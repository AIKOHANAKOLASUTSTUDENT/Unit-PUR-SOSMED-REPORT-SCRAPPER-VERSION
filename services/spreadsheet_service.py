import time

import gspread
from gspread.exceptions import APIError, WorksheetNotFound
from google.oauth2.service_account import Credentials

from config.settings import (
    DEFAULT_WORKSHEET,
    FIXED_SHEET_HEADERS,
    GOOGLE_CREDENTIAL_PATH,
    GOOGLE_SHEET_ID,
)
from utils.logger import get_logger

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
RETRY_COUNT = 3
RETRY_DELAY_SECONDS = 5
INITIAL_WORKSHEET_ROWS = 1000
ROW_EXPANSION_SIZE = 500


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
        self.spreadsheet = self.client.open_by_key(sheet_id)
        self._worksheet_cache = {
            worksheet.title: worksheet for worksheet in self.spreadsheet.worksheets()
        }

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

    def _get_or_create_worksheet(self, title: str):
        if title in self._worksheet_cache:
            return self._worksheet_cache[title]

        try:
            worksheet = self.spreadsheet.worksheet(title)
        except WorksheetNotFound:
            self.logger.info("Worksheet %s not found, creating a new worksheet", title)
            worksheet = self.spreadsheet.add_worksheet(
                title=title,
                rows=INITIAL_WORKSHEET_ROWS,
                cols=len(FIXED_SHEET_HEADERS),
            )

        self._worksheet_cache[title] = worksheet
        return worksheet

    def _load_worksheet_values(self, worksheet):
        try:
            return worksheet.get_all_values()
        except Exception as err:
            self.logger.warning(
                "Could not load values from worksheet %s: %s",
                worksheet.title,
                err,
            )
            return []

    def _ensure_headers(self, worksheet, values: list):
        current_header = values[0] if values else []

        if current_header != FIXED_SHEET_HEADERS:
            self.logger.info("Writing header row to worksheet %s", worksheet.title)
            last_column = chr(ord("A") + len(FIXED_SHEET_HEADERS) - 1)
            worksheet.update(f"A1:{last_column}1", [FIXED_SHEET_HEADERS], value_input_option="USER_ENTERED")

    def _load_existing_rows(self, values: list) -> set:
        if len(values) <= 1:
            return set()

        existing = set()
        for row in values[1:]:
            existing.add(tuple(str(cell).strip() for cell in row))
        return existing

    def _expand_worksheet_rows(self, worksheet, extra_rows: int = ROW_EXPANSION_SIZE) -> None:
        try:
            self.logger.info(
                "Expanding worksheet %s by %d rows", worksheet.title, extra_rows
            )
            worksheet.add_rows(extra_rows)
        except Exception as err:
            self.logger.error(
                "Failed to expand worksheet %s by %d rows: %s",
                worksheet.title,
                extra_rows,
                err,
            )
            raise

    def append_rows(self, rows: list, worksheet_title: str | None = None) -> None:
        if not rows:
            self.logger.warning("No rows provided to append")
            return

        target_title = worksheet_title or DEFAULT_WORKSHEET
        worksheet = self._get_or_create_worksheet(target_title)
        values = self._load_worksheet_values(worksheet)
        self._ensure_headers(worksheet, values)

        existing_rows = self._load_existing_rows(values)
        filtered_rows = []
        for row in rows:
            row_key = tuple(str(cell).strip() for cell in row)
            if row_key in existing_rows:
                self.logger.info("Skipping duplicate row for worksheet %s: %s", worksheet.title, row_key)
                continue
            filtered_rows.append(row)
            existing_rows.add(row_key)

        if not filtered_rows:
            self.logger.info("No new rows to append for worksheet %s", worksheet.title)
            return

        for attempt in range(1, RETRY_COUNT + 1):
            try:
                worksheet.append_rows(filtered_rows, value_input_option="USER_ENTERED")
                self.logger.info(
                    "upload success: %d rows appended to worksheet %s",
                    len(filtered_rows),
                    worksheet.title,
                )
                return
            except APIError as err:
                self.logger.error(
                    "Upload attempt %d failed for worksheet %s: %s",
                    attempt,
                    worksheet.title,
                    err,
                )
                if attempt == RETRY_COUNT:
                    self.logger.error("upload failure after %d attempts", RETRY_COUNT)
                    raise
                self._expand_worksheet_rows(worksheet)
                time.sleep(RETRY_DELAY_SECONDS)
            except Exception as err:
                self.logger.error(
                    "Upload attempt %d failed for worksheet %s: %s",
                    attempt,
                    worksheet.title,
                    err,
                )
                if attempt == RETRY_COUNT:
                    self.logger.error("upload failure after %d attempts", RETRY_COUNT)
                    raise
                self._expand_worksheet_rows(worksheet)
                time.sleep(RETRY_DELAY_SECONDS)
