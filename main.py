from services.spreadsheet_service import SpreadsheetService
from scraper.apbd_scraper import APBDScraper
from transformer.processor import deduplicate_records
from utils.logger import get_logger

logger = get_logger()


def run_scrape_and_upload():
    try:
        logger.info("scraping start")
        scraper = APBDScraper()
        scraped_records = scraper.scrape_all_regions()
        records = deduplicate_records(scraped_records)

        if not records:
            logger.warning("No records were produced after scraping")
            return

        service = SpreadsheetService()
        rows = [
            [
                record["nama_file"],
                record["anggaran_M"],
                record["realisasi_M"],
                record["presentase"],
                record["tanggal_pengambilan"],
                record["kab_kota"],
            ]
            for record in records
        ]

        service.append_rows(rows)
        logger.info("scraping success")
        logger.info("total records %d", len(records))
    except Exception as err:
        logger.exception("scraping failure: %s", err)
        raise


if __name__ == "__main__":
    run_scrape_and_upload()
