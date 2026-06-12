import unittest
from unittest.mock import MagicMock, patch

from gspread.exceptions import APIError

from services.spreadsheet_service import SpreadsheetService


class SpreadsheetServiceTests(unittest.TestCase):
    @patch("services.spreadsheet_service.GOOGLE_CREDENTIAL_PATH", "dummy-path")
    @patch("services.spreadsheet_service.GOOGLE_SHEET_ID", "dummy-id")
    @patch("services.spreadsheet_service.Credentials.from_service_account_file")
    @patch("services.spreadsheet_service.gspread.authorize")
    def test_append_rows_success(self, mock_authorize, mock_credentials):
        mock_client = MagicMock()
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = []
        mock_worksheet.get_all_values.return_value = []
        mock_sheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_sheet
        mock_authorize.return_value = mock_client

        service = SpreadsheetService()
        service.append_rows([["2026_06.csv", 1.0, 1.0, 100.0, "2026-06-07", "Kota Manado"]])

        mock_worksheet.append_rows.assert_called_once()

    @patch("services.spreadsheet_service.time.sleep", return_value=None)
    @patch("services.spreadsheet_service.GOOGLE_CREDENTIAL_PATH", "dummy-path")
    @patch("services.spreadsheet_service.GOOGLE_SHEET_ID", "dummy-id")
    @patch("services.spreadsheet_service.Credentials.from_service_account_file")
    @patch("services.spreadsheet_service.gspread.authorize")
    def test_append_rows_retries_on_api_error(self, mock_authorize, mock_credentials, mock_sleep):
        mock_client = MagicMock()
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = []
        mock_worksheet.get_all_values.return_value = []
        mock_worksheet.append_rows.side_effect = [Exception("first"), None]
        mock_sheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_sheet
        mock_authorize.return_value = mock_client

        service = SpreadsheetService()
        service.append_rows([["2026_06.csv", 1.0, 1.0, 100.0, "2026-06-07", "Kota Manado"]])

        self.assertEqual(mock_worksheet.append_rows.call_count, 2)

    @patch("services.spreadsheet_service.time.sleep", return_value=None)
    @patch("services.spreadsheet_service.GOOGLE_CREDENTIAL_PATH", "dummy-path")
    @patch("services.spreadsheet_service.GOOGLE_SHEET_ID", "dummy-id")
    @patch("services.spreadsheet_service.Credentials.from_service_account_file")
    @patch("services.spreadsheet_service.gspread.authorize")
    def test_append_rows_adds_rows_when_worksheet_is_full(self, mock_authorize, mock_credentials, mock_sleep):
        mock_client = MagicMock()
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = []
        mock_worksheet.get_all_values.return_value = []
        mock_worksheet.append_rows.side_effect = [Exception("full"), None]
        mock_sheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_sheet
        mock_authorize.return_value = mock_client

        service = SpreadsheetService()
        service.append_rows([["2026_06.csv", 1.0, 1.0, 100.0, "2026-06-07", "Kota Manado"]])

        mock_worksheet.add_rows.assert_called_once()
        self.assertEqual(mock_worksheet.append_rows.call_count, 2)

    @patch("services.spreadsheet_service.GOOGLE_CREDENTIAL_PATH", "dummy-path")
    @patch("services.spreadsheet_service.GOOGLE_SHEET_ID", "dummy-id")
    @patch("services.spreadsheet_service.Credentials.from_service_account_file")
    @patch("services.spreadsheet_service.gspread.authorize")
    def test_append_rows_no_rows(self, mock_authorize, mock_credentials):
        mock_client = MagicMock()
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_sheet
        mock_authorize.return_value = mock_client

        service = SpreadsheetService()
        service.append_rows([])

        mock_worksheet.append_rows.assert_not_called()

    @patch("services.spreadsheet_service.GOOGLE_CREDENTIAL_PATH", "dummy-path")
    @patch("services.spreadsheet_service.GOOGLE_SHEET_ID", "dummy-id")
    @patch("services.spreadsheet_service.Credentials.from_service_account_file")
    @patch("services.spreadsheet_service.gspread.authorize")
    def test_append_rows_skips_existing_duplicate_rows(self, mock_authorize, mock_credentials):
        mock_client = MagicMock()
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = []
        mock_worksheet.get_all_values.return_value = [
            ["Source.name", "Akun", "Anggaran.M", "Realisasi.M", "Presentase", "Tanggal", "Kab/Kota"],
            ["2026_06csv", "Pendapatan Daerah", "1.0", "1.0", "100.0", "2026-06-07", "Kota Manado"],
        ]
        mock_sheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_sheet
        mock_authorize.return_value = mock_client

        service = SpreadsheetService()
        service.append_rows([
            ["2026_06csv", "Pendapatan Daerah", "1.0", "1.0", "100.0", "2026-06-07", "Kota Manado"],
            ["2026_07csv", "Pendapatan Daerah", "2.0", "2.0", "100.0", "2026-07-01", "Kota Manado"],
        ])

        mock_worksheet.append_rows.assert_called_once()
        appended_rows = mock_worksheet.append_rows.call_args[0][0]
        self.assertEqual(len(appended_rows), 1)
        self.assertEqual(appended_rows[0][0], "2026_07csv")


if __name__ == "__main__":
    unittest.main()
