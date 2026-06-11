import time

import gspread
from gspread.exceptions import APIError, WorksheetNotFound
from google.oauth2.service_account import Credentials

from config.settings import DEFAULT_WORKSHEET, GOOGLE_CREDENTIAL_PATH, GOOGLE_SHEET_ID
from utils.logger import get_logger

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
RETRY_COUNT = 3
RETRY_DELAY_SECONDS = 5


class SpreadsheetService:
    def __init__(self) -> None:
        self.logger = get_logger()
        if not GOOGLE_SHEET_ID:
            raise ValueError("GOOGLE_SHEET_ID is not configured")
        if not GOOGLE_CREDENTIAL_PATH:
            raise ValueError("GOOGLE_CREDENTIAL_PATH is not configured")

        sheet_id = self._normalize_sheet_id(GOOGLE_SHEET_ID)
        credentials = Credentials.from_service_account_file(GOOGLE_CREDENTIAL_PATH, scopes=SCOPES)
        self.client = gspread.authorize(credentials)

        try:
            self.spreadsheet = self.client.open_by_key(sheet_id)
            self.worksheet = self.spreadsheet.worksheet(DEFAULT_WORKSHEET)
        except WorksheetNotFound as err:
            self.logger.error("Worksheet %s not found", DEFAULT_WORKSHEET)
            raise

    def _normalize_sheet_id(self, raw_sheet_id: str) -> str:
        raw_sheet_id = raw_sheet_id.strip()
        if "/d/" in raw_sheet_id:
            parts = raw_sheet_id.split("/d/", 1)[1]
            parts = parts.split("/", 1)[0]
            raw_sheet_id = parts
        if "?" in raw_sheet_id:
            raw_sheet_id = raw_sheet_id.split("?", 1)[0]
        if not raw_sheet_id:
            raise ValueError("GOOGLE_SHEET_ID was provided but could not be parsed")
        return raw_sheet_id

    def append_rows(self, rows: list) -> None:
        if not rows:
            self.logger.warning("No rows provided to append")
            return

        for attempt in range(1, RETRY_COUNT + 1):
            try:
                self.worksheet.append_rows(rows, value_input_option="USER_ENTERED")
                self.logger.info("upload success: %d rows appended", len(rows))
                return
            except APIError as err:
                self.logger.error("Upload attempt %d failed: %s", attempt, err)
                if attempt == RETRY_COUNT:
                    self.logger.error("upload failure after %d attempts", RETRY_COUNT)
                    raise
                time.sleep(RETRY_DELAY_SECONDS)
            except Exception as err:
                self.logger.error("Upload attempt %d failed: %s", attempt, err)
                if attempt == RETRY_COUNT:
                    self.logger.error("upload failure after %d attempts", RETRY_COUNT)
                    raise
                time.sleep(RETRY_DELAY_SECONDS)
