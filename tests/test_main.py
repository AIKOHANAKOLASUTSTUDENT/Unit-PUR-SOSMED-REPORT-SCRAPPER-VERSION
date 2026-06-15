import unittest
from unittest.mock import MagicMock, patch

from config.settings import SUMMARY_WORKSHEET
from main import _upload_grouped_records


class MainUploadTests(unittest.TestCase):
    @patch("main.SpreadsheetService")
    def test_upload_grouped_records_skips_semua_pemda(self, mock_service_cls):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        semua_rows = [
            [
                "2025_09csv",
                "Pendapatan Daerah",
                1.0,
                1.0,
                100.0,
                "2025-09-01",
                "Semua Pemda",
                "2025-09-01",
            ]
        ]
        tomohon_rows = [
            [
                "2025_09csv",
                "Pendapatan Daerah",
                1.0,
                1.0,
                100.0,
                "2025-09-01",
                "Tomohon",
                "2025-09-01",
            ]
        ]
        grouped_records = {
            "Semua Pemda": semua_rows,
            "Tomohon": tomohon_rows,
        }

        _upload_grouped_records(grouped_records)

        mock_service.append_rows.assert_any_call(tomohon_rows, worksheet_title="Tomohon")
        mock_service.append_rows.assert_any_call(tomohon_rows, worksheet_title=SUMMARY_WORKSHEET)
        self.assertEqual(mock_service.append_rows.call_count, 2)

        excluded_calls = [
            call for call in mock_service.append_rows.call_args_list
            if call.kwargs.get("worksheet_title") == "Semua Pemda"
        ]
        self.assertEqual(excluded_calls, [])


if __name__ == "__main__":
    unittest.main()
