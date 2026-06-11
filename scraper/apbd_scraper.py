import re
from datetime import datetime, timedelta
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from playwright.sync_api import Playwright, sync_playwright, TimeoutError as PlaywrightTimeoutError

from config.settings import (
    DEFAULT_USER_AGENT,
    FIXED_REGIONS,
    PLAYWRIGHT_ARGS,
    PLAYWRIGHT_HEADLESS,
    PROVINCE_CODE,
    TARGET_URL,
)
from transformer.processor import build_record
from transformer.normalizer import parse_tanggal_pengambilan
from utils.logger import get_logger


class APBDScraper:
    def __init__(self) -> None:
        self.logger = get_logger()
        self.periode, self.tahun = self._compute_reporting_period()
        self.nama_file = f"{self.tahun}_{self.periode:02d}.csv"

    def _compute_reporting_period(self) -> (int, int):
        now = datetime.now()
        if now.day == 1:
            previous = now - timedelta(days=1)
            return previous.month, previous.year
        return now.month, now.year

    def _set_select_value(self, page: Any, selector: str, value: str) -> None:
        page.wait_for_selector(selector, timeout=60000)
        try:
            page.select_option(selector, value)
            page.evaluate(
                "({ selector, value }) => { const element = document.querySelector(selector); if (!element) return; if (window.$) { $(selector).val(value).trigger('change'); } else { element.dispatchEvent(new Event('change', { bubbles: true })); } }",
                {"selector": selector, "value": value},
            )
            page.wait_for_timeout(500)
            return
        except Exception as err:
            self.logger.warning("select_option failed for %s=%s, falling back to JS event dispatch: %s", selector, value, err)

        page.evaluate(
            "({ selector, value }) => { const element = document.querySelector(selector); if (!element) return; if (window.$) { $(selector).val(value).trigger('change'); } else { element.value = value; element.dispatchEvent(new Event('change', { bubbles: true })); } }",
            {"selector": selector, "value": value},
        )
        page.wait_for_timeout(500)

    def _wait_for_pemda_options(self, page: Any) -> None:
        page.wait_for_function(
            "() => { const select = document.querySelector('#sel_pemda'); return select && select.querySelectorAll('option').length > 1; }",
            timeout=45000,
        )

    def _submit_query(self, page: Any) -> None:
        button = page.query_selector('button[type="submit"]')
        if not button:
            raise RuntimeError("Submit button was not found on the page")
        button.click()
        page.wait_for_selector('table.table.tab-primary.table-striped', timeout=30000)
        page.wait_for_timeout(500)

    def _extract_first_summary_row(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table.table.tab-primary.table-striped")
        if not table:
            raise ValueError("APBD summary table not found")

        rows = [
            [cell.text.strip() for cell in row.select("td")]
            for row in table.select("tbody tr")
            if row.get_text(strip=True)
        ]
        if not rows or len(rows[0]) < 5:
            raise ValueError("Could not extract the expected row content from APBD table")
        return rows[0]

    def _extract_tanggal_pengambilan(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        paragraphs = " ".join(p.get_text(separator=" ").strip() for p in soup.select("p"))
        match = re.search(r"data diterima SIKD per\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", paragraphs, flags=re.IGNORECASE)
        if match:
            return parse_tanggal_pengambilan(match.group(1))
        return datetime.now().strftime("%Y-%m-%d")

    def _build_region_record(self, raw_row: List[str], region_name: str, tanggal: str) -> Dict[str, Any]:
        try:
            return build_record(region_name, self.nama_file, tanggal, raw_row)
        except Exception as exc:
            self.logger.error("validation failure for region %s: %s", region_name, exc, exc_info=True)
            raise

    def scrape_all_regions(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=PLAYWRIGHT_HEADLESS, args=PLAYWRIGHT_ARGS)
            page = browser.new_page(user_agent=DEFAULT_USER_AGENT, viewport={"width": 1280, "height": 800})
            page.add_init_script("() => { Object.defineProperty(navigator, 'webdriver', {get: () => false}); }")
            page.goto(TARGET_URL, timeout=60000)
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_selector("#sel_periode", timeout=60000)
            page.wait_for_selector("#sel_tahun", timeout=60000)
            page.wait_for_selector("#sel_provinsi", timeout=60000)
            page.wait_for_selector("#sel_pemda", timeout=60000)

            self._set_select_value(page, "#sel_periode", str(self.periode))
            self._set_select_value(page, "#sel_tahun", str(self.tahun))
            self._set_select_value(page, "#sel_provinsi", PROVINCE_CODE)
            self._wait_for_pemda_options(page)

            for region in FIXED_REGIONS:
                region_name = region["name"]
                region_value = region["value"]
                self.logger.info("Scraping region: %s", region_name)
                try:
                    self._set_select_value(page, "#sel_pemda", region_value)
                    self._submit_query(page)
                    html = page.content()
                    raw_row = self._extract_first_summary_row(html)
                    tanggal_pengambilan = self._extract_tanggal_pengambilan(html)
                    record = self._build_region_record(raw_row, region_name, tanggal_pengambilan)
                    records.append(record)
                except PlaywrightTimeoutError as terr:
                    self.logger.error("Timeout while scraping region %s: %s", region_name, terr)
                except Exception as err:
                    self.logger.error("Failed to scrape region %s: %s", region_name, err)

            browser.close()

        return records
