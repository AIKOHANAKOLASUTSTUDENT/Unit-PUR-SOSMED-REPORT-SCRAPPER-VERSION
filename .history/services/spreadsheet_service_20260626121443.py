"""
Google Sheets integration for Instagram Engagement Scraper.
Handles authentication, header management, and row appending.
"""

import base64
import json
import tempfile
from typing import Dict, List, Set, Optional
import gspread
from google.oauth2.service_account import Credentials

from config.settings import (
    GOOGLE_SHEET_ID,
    GOOGLE_CREDENTIAL_PATH,
    GOOGLE_CREDENTIAL_PATH_B64,
    GOOGLE_WORKSHEET_NAME,
)
from utils.logger import get_logger


SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]


class SpreadsheetService:
    """
    Service for interacting with Google Sheets.
    Handles authentication, sheet operations, and data appending.
    """

    def __init__(self):
        """
        Initialize Google Sheets service.
        Authorizes using either file path or base64-encoded credentials.
        """
        self.logger = get_logger()
        self.sheet_id = self._normalize_sheet_id(GOOGLE_SHEET_ID)
        self.worksheet_name = GOOGLE_WORKSHEET_NAME
        
        # Get credentials
        credentials = self._get_credentials()
        
        # Authorize and open spreadsheet
        try:
            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open_by_key(self.sheet_id)
            self.worksheet = None
            self.logger.info(f"SpreadsheetService initialized for sheet: {self.sheet_id}")
        except Exception as e:
            error_message = f"Failed to open Google Sheet '{self.sheet_id}': {e}"
            self.logger.error(error_message)
            raise RuntimeError(error_message) from e
    
    def _normalize_sheet_id(self, raw_id: str) -> str:
        """
        Extract sheet ID from various formats.
        Handles both full URLs and plain IDs.
        """
        raw_id = raw_id.strip()
        
        # Extract from URL if needed
        if "/d/" in raw_id:
            parts = raw_id.split("/d/", 1)[1]
            parts = parts.split("/", 1)[0]
            raw_id = parts
        
        # Remove query parameters
        if "?" in raw_id:
            raw_id = raw_id.split("?", 1)[0]
        
        if not raw_id:
            raise ValueError("Could not extract sheet ID from GOOGLE_SHEET_ID")
        
        return raw_id
    
    def _get_credentials(self) -> Credentials:
        """
        Get Google credentials from file or base64 string.
        """
        if GOOGLE_CREDENTIAL_PATH_B64:
            # Decode base64 and create temp file
            try:
                decoded = base64.b64decode(GOOGLE_CREDENTIAL_PATH_B64)
                cred_dict = json.loads(decoded)
                credentials = Credentials.from_service_account_info(cred_dict, scopes=SCOPES)
                return credentials
            except Exception as e:
                raise ValueError(f"Failed to decode base64 credentials: {e}")
        
        elif GOOGLE_CREDENTIAL_PATH:
            # Load from file
            try:
                credentials = Credentials.from_service_account_file(
                    GOOGLE_CREDENTIAL_PATH,
                    scopes=SCOPES
                )
                return credentials
            except FileNotFoundError:
                raise ValueError(f"Credential file not found: {GOOGLE_CREDENTIAL_PATH}")
            except Exception as e:
                raise ValueError(f"Failed to load credentials from file: {e}")
        
        else:
            raise ValueError("No credentials provided (GOOGLE_CREDENTIAL_PATH or GOOGLE_CREDENTIAL_PATH_B64)")
    
    def ensure_header(self) -> None:
        """
        Ensure header row exists in worksheet.
        Creates worksheet if needed and writes headers.
        """
        # Get or create worksheet
        try:
            self.worksheet = self.spreadsheet.worksheet(self.worksheet_name)
            self.logger.info(f"Opened worksheet: {self.worksheet_name}")
        except gspread.WorksheetNotFound:
            self.logger.info(f"Worksheet '{self.worksheet_name}' not found. Creating...")
            self.worksheet = self.spreadsheet.add_worksheet(
                title=self.worksheet_name,
                rows=1000,
                cols=14
            )
            self.logger.info(f"Created worksheet: {self.worksheet_name}")
        
        # Check if header exists
        try:
            first_row = self.worksheet.row_values(1)
        except:
            first_row = []
        
        headers = [
            "No", "Bulan", "Tanggal yang post date", "Judul Konten", "Content Type", "Username", "Link IG",
            "Reach", "Views", "Likes", "Comment", "Share", "Repost", "Save", "Collab Status",
            "Jumlah followers akun cbp.rupiah saat di scrapping"
        ]
        
        if not first_row or first_row != headers:
            self.logger.info("Writing header row...")
            self.worksheet.append_row(headers, value_input_option="USER_ENTERED")
            self.logger.info("Header row written")
    
    def get_existing_urls(self) -> Set[str]:
        """
        Read existing URLs from spreadsheet to avoid duplicates.
        
        Returns:
            Set of URLs already in the spreadsheet
        """
        if not self.worksheet:
            raise ValueError("Worksheet not initialized. Call ensure_header() first.")
        
        try:
            # Get header row and determine the Link IG column index
            header_values = self.worksheet.row_values(1)
            try:
                url_column_index = header_values.index("Link IG") + 1
            except ValueError:
                url_column_index = 1
            values = self.worksheet.col_values(url_column_index)
            # Skip header (first value)
            existing_urls = set(url for url in values[1:] if url.strip())
            self.logger.info(f"Found {len(existing_urls)} existing URLs in sheet")
            return existing_urls
        except Exception as e:
            self.logger.warning(f"Failed to get existing URLs: {e}")
            return set()
    
    def append_rows(self, records: List[Dict]) -> int:
        """
        Append records to spreadsheet, skipping duplicates.
        
        Args:
            records: List of cleaned record dicts
        
        Returns:
            Number of rows actually appended
        """
        if not self.worksheet:
            raise ValueError("Worksheet not initialized. Call ensure_header() first.")
        
        if not records:
            self.logger.warning("No records to append")
            return 0
        
        # Get existing URLs
        existing_urls = self.get_existing_urls()
        
        # Build rows to append
        rows_to_append = []
        duplicates_skipped = 0
        next_no = len(existing_urls) + 1

        for record in records:
            url = record.get("url", "")

            # Skip if URL already exists
            if url in existing_urls:
                duplicates_skipped += 1
                continue

            # Build row in order matching header columns
            post_date = record.get("post_date", "")
            bulan = ""
            if post_date and post_date != "N/A":
                try:
                    month_value = post_date.split(" ")[0].split("-")[1]
                    bulan = {
                        "01": "Januari",
                        "02": "Februari",
                        "03": "Maret",
                        "04": "April",
                        "05": "Mei",
                        "06": "Juni",
                        "07": "Juli",
                        "08": "Agustus",
                        "09": "September",
                        "10": "Oktober",
                        "11": "November",
                        "12": "Desember",
                    }.get(month_value, "")
                except Exception:
                    bulan = ""

            row = [
                next_no,
                bulan,
                post_date,
                record.get("caption", ""),
                record.get("content_type", ""),
                record.get("username", ""),
                record.get("url", ""),
                record.get("reach", ""),
                record.get("views", ""),
                record.get("likes", ""),
                record.get("comments", ""),
                record.get("shares", ""),
                record.get("reposts", ""),
                record.get("saves", ""),
                record.get("collab_status", "belum collab"),
                record.get("followers", ""),
            ]
            rows_to_append.append(row)
            existing_urls.add(url)  # Mark as seen
            next_no += 1
            try:
                self.worksheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
                self.logger.info(f"Appended {len(rows_to_append)} new rows to sheet")
            except Exception as e:
                self.logger.error(f"Failed to append rows: {e}")
                raise
        
        if duplicates_skipped > 0:
            self.logger.info(f"Skipped {duplicates_skipped} duplicate URLs")
        
        return len(rows_to_append)

