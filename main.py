import argparse
from datetime import datetime

from config.settings import FIXED_REGIONS, SUMMARY_WORKSHEET
from services.spreadsheet_service import SpreadsheetService
from scraper.apbd_scraper import APBDScraper
from transformer.processor import deduplicate_records
from utils.logger import get_logger

logger = get_logger()


def _validate_region_groups(grouped_records: dict) -> None:
    if not grouped_records:
        return

    region_signatures = {}
    for region_name, rows in grouped_records.items():
        if not rows:
            logger.warning("No rows found for region %s", region_name)
            continue

        row_set = {tuple(row[:-1]) for row in rows}
        if len(row_set) == 1 and len(rows) > 1:
            logger.warning(
                "Region %s has %d identical rows; this may indicate a scraping or selection issue",
                region_name,
                len(rows),
            )

        region_signatures[region_name] = tuple(sorted(row_set))

    signatures = {}
    for region_name, signature in region_signatures.items():
        signatures.setdefault(signature, []).append(region_name)

    for regions in signatures.values():
        if len(regions) > 1:
            logger.warning(
                "Regions share identical row sets: %s. Verify that region selection is working correctly.",
                ", ".join(regions),
            )


def _group_records(records: list[dict]) -> dict:
    grouped_records = {}
    ingestion_timestamp = datetime.utcnow().replace(microsecond=0).isoformat()
    for record in records:
        region_name = record["kab_kota"]
        grouped_records.setdefault(region_name, []).append(
            [
                record["nama_file"],
                record["akun"],
                record["anggaran_M"],
                record["realisasi_M"],
                record["presentase"],
                record["tanggal_pengambilan"],
                record["kab_kota"],
                ingestion_timestamp,
            ]
        )
    return grouped_records


def _is_excluded_region(region_name: str) -> bool:
    return region_name.strip().lower() == "semua pemda"


def _upload_grouped_records(grouped_records: dict) -> None:
    if not grouped_records:
        logger.warning("No grouped records to upload")
        return

    service = SpreadsheetService()
    _validate_region_groups(grouped_records)

    total_rows = 0
    all_rows = []
    for region_name, rows in grouped_records.items():
        if _is_excluded_region(region_name):
            logger.info("Skipping excluded region %s", region_name)
            continue

        service.append_rows(rows, worksheet_title=region_name)
        total_rows += len(rows)
        all_rows.extend(rows)
        logger.info("uploaded %d rows to worksheet %s", len(rows), region_name)

    if all_rows:
        service.append_rows(all_rows, worksheet_title=SUMMARY_WORKSHEET)
        logger.info(
            "uploaded %d rows to worksheet %s",
            len(all_rows),
            SUMMARY_WORKSHEET,
        )

    logger.info("scraping success")
    logger.info("total rows uploaded %d", total_rows)


def _parse_year_month(value: str) -> tuple[int, int]:
    try:
        year_str, month_str = value.strip().split("-")
        year = int(year_str)
        month = int(month_str)
    except Exception as err:
        raise ValueError("Invalid date format, expected YYYY-MM") from err

    if month < 1 or month > 12:
        raise ValueError("Month must be between 1 and 12")
    return year, month


def _resolve_regions(region_arg: str | None) -> list[dict] | None:
    if not region_arg:
        return None

    requested = {part.strip().lower() for part in region_arg.split(",") if part.strip()}
    selected = [
        region
        for region in FIXED_REGIONS
        if region["name"].strip().lower() in requested or region["value"] in requested
    ]

    if not selected:
        raise ValueError(
            "No matching regions found. Provide valid region names or values from FIXED_REGIONS."
        )

    return selected


def run_scrape_and_upload():
    try:
        logger.info("scraping start")
        scraper = APBDScraper()
        scraped_records = scraper.scrape_all_regions()
        records = deduplicate_records(scraped_records)

        if not records:
            logger.warning("No records were produced after scraping")
            return

        grouped_records = _group_records(records)
        _upload_grouped_records(grouped_records)
        logger.info("total records %d", len(records))
    except Exception as err:
        logger.exception("scraping failure: %s", err)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="DJPK APBD scraper")
    parser.add_argument(
        "--history-start",
        help="One-time historical scrape start period in YYYY-MM format",
        default=None,
    )
    parser.add_argument(
        "--history-end",
        help="One-time historical scrape end period in YYYY-MM format (defaults to current month)",
        default=None,
    )
    parser.add_argument(
        "--regions",
        help="Comma-separated region names or values to scrape (default is all fixed regions)",
        default=None,
    )
    args = parser.parse_args()

    if args.history_start:
        start_year, start_month = _parse_year_month(args.history_start)
        end_year, end_month = (
            _parse_year_month(args.history_end)
            if args.history_end
            else (None, None)
        )
        regions = _resolve_regions(args.regions)

        try:
            logger.info(
                "Starting one-time historical scrape from %s to %s",
                args.history_start,
                args.history_end or "current month",
            )
            scraper = APBDScraper()
            scraped_records = scraper.scrape_regions_for_periods(
                start_year,
                start_month,
                end_year,
                end_month,
                regions=regions,
            )
            records = deduplicate_records(scraped_records)
            if not records:
                logger.warning("No records were produced after historical scraping")
                return

            grouped_records = _group_records(records)
            _upload_grouped_records(grouped_records)
            logger.info("total records %d", len(records))
        except Exception as err:
            logger.exception("historical scraping failure: %s", err)
            raise
    else:
        run_scrape_and_upload()


if __name__ == "__main__":
    main()
