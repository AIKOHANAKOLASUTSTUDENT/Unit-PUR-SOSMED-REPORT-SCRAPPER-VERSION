import unittest
from unittest.mock import patch

from scraper.apbd_scraper import APBDScraper


class APBDScraperTests(unittest.TestCase):
    def test_iterate_periods_includes_full_range(self):
        periods = APBDScraper._iterate_periods(2025, 9, 2025, 12)
        self.assertEqual(
            periods,
            [(2025, 9), (2025, 10), (2025, 11), (2025, 12)],
        )

    def test_get_nama_file_formats_period(self):
        self.assertEqual(APBDScraper.get_nama_file(2025, 9), "2025_09csv")
        self.assertEqual(APBDScraper.get_nama_file(2026, 12), "2026_12csv")

    @patch("scraper.apbd_scraper.time.sleep", return_value=None)
    @patch.object(APBDScraper, "_build_region_record")
    @patch.object(APBDScraper, "_extract_tanggal_pengambilan")
    @patch.object(APBDScraper, "_extract_summary_rows")
    @patch.object(APBDScraper, "_fetch_region_html")
    def test_scrape_regions_for_periods_builds_expected_records(
        self,
        mock_fetch_html,
        mock_extract_rows,
        mock_extract_date,
        mock_build_record,
        mock_sleep,
    ):
        mock_fetch_html.return_value = "<html></html>"
        mock_extract_rows.return_value = [["", "Pendapatan Daerah", "1,00 M", "1,00 M", "100"]]
        mock_extract_date.return_value = ("2025-09-01", True)
        mock_build_record.return_value = {
            "nama_file": "2025_09csv",
            "akun": "Pendapatan Daerah",
            "anggaran_M": 1.0,
            "realisasi_M": 1.0,
            "presentase": 100.0,
            "tanggal_pengambilan": "2025-09-01",
            "kab_kota": "Tomohon",
        }

        scraper = APBDScraper()
        regions = [{"name": "Tomohon", "value": "08"}]
        records = scraper.scrape_regions_for_periods(2025, 9, 2025, 9, regions=regions)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["nama_file"], "2025_09csv")
        mock_build_record.assert_called_once_with(
            ["", "Pendapatan Daerah", "1,00 M", "1,00 M", "100"],
            "Tomohon",
            "2025-09-01",
            "2025_09csv",
        )

    def test_extract_tanggal_pengambilan_falls_back_to_period_start(self):
        scraper = APBDScraper()
        html = "<html><body><p>No matching date text here</p></body></html>"

        fallback_date, extracted = scraper._extract_tanggal_pengambilan(html, 2025, 9)

        self.assertEqual(fallback_date, "2025-09-01")
        self.assertFalse(extracted)

    def test_extract_tanggal_pengambilan_from_page_text(self):
        scraper = APBDScraper()
        html = (
            "<html><body>"
            "<p>Data diterima SIKD per 31 Desember 2025</p>"
            "</body></html>"
        )

        extracted_date, extracted = scraper._extract_tanggal_pengambilan(html, 2025, 12)

        self.assertEqual(extracted_date, "2025-12-31")
        self.assertTrue(extracted)

    @patch("scraper.apbd_scraper.time.sleep", return_value=None)
    @patch.object(APBDScraper, "_extract_summary_rows")
    @patch.object(APBDScraper, "_fetch_region_html")
    def test_scrape_regions_uses_shared_date_for_subregions(
        self,
        mock_fetch_html,
        mock_extract_rows,
        mock_sleep,
    ):
        html_with_date = "<html><body><p>Data diterima SIKD per 01 September 2025</p></body></html>"
        html_without_date = "<html><body><p>No date visible here</p></body></html>"

        # First region returns an explicit date, second region does not.
        mock_fetch_html.side_effect = [html_with_date, html_without_date]
        mock_extract_rows.return_value = [["", "Pendapatan Daerah", "1,00 M", "1,00 M", "100"]]

        scraper = APBDScraper()
        regions = [
            {"name": "Semua Pemda", "value": "--"},
            {"name": "Tomohon", "value": "08"},
        ]

        records = scraper.scrape_regions_for_periods(2025, 9, 2025, 9, regions=regions)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["tanggal_pengambilan"], "2025-09-01")
        self.assertEqual(records[1]["tanggal_pengambilan"], "2025-09-01")


if __name__ == "__main__":
    unittest.main()
