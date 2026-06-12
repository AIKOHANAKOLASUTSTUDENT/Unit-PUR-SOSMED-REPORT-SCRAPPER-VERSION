import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup

from config.settings import (
    FIXED_REGIONS,
    PROVINCE_CODE,
    TARGET_URL,
)
from transformer.processor import build_record
from transformer.normalizer import parse_tanggal_pengambilan
from utils.logger import get_logger

# Direct URL patterns discovered from browser inspection of the DJPK portal.
# The form submits via GET with query parameters — no session/CSRF required.
DATA_URL = TARGET_URL  # https://djpk.kemenkeu.go.id/portal/data/apbd

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
    "Referer": TARGET_URL,
}


class APBDScraper:
    def __init__(self) -> None:
        self.logger = get_logger()
        self.session = requests.Session()
        self.session.headers.update(_DEFAULT_HEADERS)

    @staticmethod
    def _compute_reporting_period() -> Tuple[int, int]:
        now = datetime.now()
        if now.day == 1:
            previous = now - timedelta(days=1)
            return previous.month, previous.year
        return now.month, now.year

    @staticmethod
    def _normalize_period(year: int, month: int) -> Tuple[int, int]:
        if month < 1 or month > 12:
            raise ValueError("Month must be between 1 and 12")
        return year, month

    @classmethod
    def _iterate_periods(
        cls,
        start_year: int,
        start_month: int,
        end_year: int | None = None,
        end_month: int | None = None,
    ) -> List[Tuple[int, int]]:
        start_year, start_month = cls._normalize_period(start_year, start_month)
        if end_year is None or end_month is None:
            now = datetime.now()
            end_year, end_month = now.year, now.month
        end_year, end_month = cls._normalize_period(end_year, end_month)

        if (start_year, start_month) > (end_year, end_month):
            raise ValueError("Start period must be earlier than or equal to end period")

        periods: List[Tuple[int, int]] = []
        current_year, current_month = start_year, start_month
        while (current_year, current_month) <= (end_year, end_month):
            periods.append((current_year, current_month))
            if current_month == 12:
                current_year += 1
                current_month = 1
            else:
                current_month += 1

        return periods

    @staticmethod
    def get_nama_file(year: int, month: int) -> str:
        return f"{year}_{month:02d}csv"

    def _fetch_region_html(self, region_value: str, year: int, month: int) -> str:
        """Fetch APBD page for a specific region via direct GET request."""
        params = {
            "periode": str(month),
            "tahun": str(year),
            "provinsi": PROVINCE_CODE,
            "pemda": region_value,
        }
        self.logger.debug("Fetching URL params: %s", params)
        resp = self.session.get(DATA_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _extract_summary_rows(self, html: str) -> List[List[str]]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table.table.tab-primary.table-striped")
        if not table:
            raise ValueError("APBD summary table not found in HTML response")

        # The DJPK portal generates invalid HTML with nested <tr> inside <tr>.
        # BeautifulSoup (and most parsers) flatten this into one huge row.
        # Solution: extract each <tr>...</tr> block directly from the raw table HTML
        # using regex, then parse each block individually for exactly 5 cells.
        raw_table_html = str(table)

        # Extract individual <tr> opening tags with their content up to the next <tr
        # Split by <tr (case-insensitive) boundaries
        tr_blocks = re.split(r'(?i)<tr(?:\s[^>]*)?>', raw_table_html)

        rows = []
        for block in tr_blocks:
            # Parse just this block to get <td> elements
            block_soup = BeautifulSoup("<table><tr>" + block + "</tr></table>", "html.parser")
            cells = block_soup.select("td")
            if len(cells) < 5:
                continue
            cell_texts = [c.get_text(strip=True) for c in cells[:5]]
            # Skip rows where no meaningful data exists
            if all(not v for v in cell_texts):
                continue
            # Skip rows where akun (index 1) is empty
            if not cell_texts[1]:
                continue
            rows.append(cell_texts)

        if not rows:
            raise ValueError("Could not extract summary rows from APBD table")
        return rows

    def _extract_tanggal_pengambilan(self, html: str, year: int, month: int) -> tuple[str, bool]:
        soup = BeautifulSoup(html, "html.parser")
        page_text = soup.get_text(separator=" ").strip()

        patterns = [
            r"data\s+diterima(?:\s+SIKD)?\s+per\s+(\d{1,2}\s+[A-Za-z\.]+\s+\d{4})",
            r"per\s+(\d{1,2}\s+[A-Za-z\.]+\s+\d{4})",
            r"tanggal\s+pengambilan\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z\.]+\s+\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, page_text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                raw_date = match.group(1)
                try:
                    return parse_tanggal_pengambilan(raw_date), True
                except ValueError:
                    self.logger.warning(
                        "Could not parse tanggal_pengambilan text '%s' for %04d-%02d",
                        raw_date,
                        year,
                        month,
                    )

        generic_match = re.search(
            r"(\d{1,2}\s+[A-Za-z\.]+\s+\d{4})",
            page_text,
            flags=re.IGNORECASE,
        )
        if generic_match:
            raw_date = generic_match.group(1)
            try:
                return parse_tanggal_pengambilan(raw_date), True
            except ValueError:
                self.logger.warning(
                    "Could not parse generic tanggal_pengambilan text '%s' for %04d-%02d",
                    raw_date,
                    year,
                    month,
                )

        fallback_date = f"{year}-{month:02d}-01"
        self.logger.warning(
            "Falling back to period start date for tanggal_pengambilan: %s",
            fallback_date,
        )
        return fallback_date, False

    def _build_region_record(
        self,
        raw_row: List[str],
        region_name: str,
        tanggal: str,
        nama_file: str,
    ) -> Dict[str, Any]:
        try:
            return build_record(region_name, nama_file, tanggal, raw_row)
        except Exception as exc:
            self.logger.error(
                "validation failure for region %s: %s", region_name, exc, exc_info=True
            )
            raise

    def _scrape_region_period(
        self,
        year: int,
        month: int,
        region: Dict[str, str],
        shared_tanggal_pengambilan: str | None = None,
    ) -> tuple[List[Dict[str, Any]], str, bool]:
        region_name = region["name"]
        region_value = region["value"]
        nama_file = self.get_nama_file(year, month)
        records: List[Dict[str, Any]] = []

        self.logger.info("Scraping period %04d-%02d for region %s", year, month, region_name)
        html = self._fetch_region_html(region_value, year, month)
        raw_rows = self._extract_summary_rows(html)
        tanggal_pengambilan, extracted = self._extract_tanggal_pengambilan(html, year, month)
        if not extracted and shared_tanggal_pengambilan is not None:
            self.logger.info(
                "Using shared tanggal_pengambilan %s for region %s",
                shared_tanggal_pengambilan,
                region_name,
            )
            tanggal_pengambilan = shared_tanggal_pengambilan
            extracted = True

        self.logger.info(
            "Region %s %04d-%02d: found %d rows, tanggal=%s",
            region_name,
            year,
            month,
            len(raw_rows),
            tanggal_pengambilan,
        )

        for raw_row in raw_rows:
            try:
                record = self._build_region_record(
                    raw_row, region_name, tanggal_pengambilan, nama_file
                )
                records.append(record)
            except Exception as row_err:
                self.logger.error(
                    "Skipping row for region %s: %s | raw=%s",
                    region_name,
                    row_err,
                    raw_row,
                )

        return records, tanggal_pengambilan, extracted

    def scrape_regions_for_periods(
        self,
        start_year: int,
        start_month: int,
        end_year: int | None = None,
        end_month: int | None = None,
        regions: List[Dict[str, str]] | None = None,
    ) -> List[Dict[str, Any]]:
        if regions is None:
            regions = FIXED_REGIONS

        records: List[Dict[str, Any]] = []
        periods = self._iterate_periods(start_year, start_month, end_year, end_month)

        for year, month in periods:
            self.logger.info("Starting scrape for period %04d-%02d", year, month)
            period_tanggal_pengambilan: str | None = None
            for region in regions:
                try:
                    period_records, tanggal_pengambilan, extracted = self._scrape_region_period(
                        year,
                        month,
                        region,
                        shared_tanggal_pengambilan=period_tanggal_pengambilan,
                    )
                    records.extend(period_records)
                    if extracted and period_tanggal_pengambilan is None:
                        period_tanggal_pengambilan = tanggal_pengambilan
                except requests.RequestException as req_err:
                    self.logger.error(
                        "HTTP error while scraping region %s for %04d-%02d: %s",
                        region["name"],
                        year,
                        month,
                        req_err,
                    )
                except Exception as err:
                    self.logger.error(
                        "Failed to scrape region %s for %04d-%02d: %s",
                        region["name"],
                        year,
                        month,
                        err,
                    )
                time.sleep(1)

        return records

    def scrape_all_regions(self) -> List[Dict[str, Any]]:
        period_month, period_year = self._compute_reporting_period()
        return self.scrape_regions_for_periods(period_year, period_month)
