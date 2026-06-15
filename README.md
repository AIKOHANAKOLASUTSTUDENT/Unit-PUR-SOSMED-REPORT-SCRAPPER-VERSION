# DJPK APBD Scraper

## Project Purpose
This repository contains a Python scraper for the DJPK APBD portal (`https://djpk.kemenkeu.go.id/portal/data/apbd`). It collects APBD summary data for fixed Sulawesi Utara regions and uploads the extracted results to a Google Sheets worksheet.

## Current Status
- The main entry point is `main.py`.
- Scraping is handled by `scraper/apbd_scraper.py` using requests and BeautifulSoup.
- Data is normalized and validated in `transformer/`.
- Google Sheets upload is performed by `services.spreadsheet_service.py`.
- The service now writes each region to its own worksheet/tab using the region name.
- The service also writes a combined summary sheet named `APBD Kab_kota` by default, containing all rows from every region.
- Each appended row also includes an `Ingestion.Timestamp` value.
- Percentage values may exceed 100 and are now accepted.
- Logging is written to `logs/scraper.log`.
- Environment configuration is loaded from `.env` via `config/settings.py`.

## Important Notes
- The `.env` file must define `GOOGLE_SHEET_ID`, and either `GOOGLE_CREDENTIAL_PATH` or `GOOGLE_CREDENTIAL_PATH_B64`.
- The project prefers `GOOGLE_WORKSHEET_NAME`, with fallback to `GOOGLE_SHEET_NAME`.
- The spreadsheet service accepts either a raw sheet ID or a full Google Sheets URL.
- The service account JSON file must have access to the spreadsheet.

## Project Structure
- `config/settings.py` - project settings and environment variable loading.
- `main.py` - orchestrates scraping, deduplication, and upload.
- `scraper/apbd_scraper.py` - navigates DJPK portal, selects region/date, and extracts table data.
- `transformer/` - normalizes currency, percentage, and dates; validates records.
- `services/spreadsheet_service.py` - authorizes Google Sheets access and appends rows.
- `utils/logger.py` - configures file and console logging.
- `scheduler/` - scheduler scaffolding for periodic runs.
- `tests/` - unit tests for data transformation and service logic.

## How to Run
1. Activate the Python virtual environment.
2. Install dependencies from `requirements.txt` if needed.
3. Confirm `.env` contains correct values:
   - `GOOGLE_SHEET_ID`
   - `GOOGLE_CREDENTIAL_PATH`
   - `GOOGLE_WORKSHEET_NAME`
   - `TIMEZONE`
4. Run:
   ```bash
   python main.py
   ```

## Logs
- Runtime logs are written to `logs/scraper.log`.
- Check this file first when debugging scraping or upload failures.

## Recent Changes
- Added exclusion for the `Semua Pemda` region so it is not uploaded as a separate worksheet or included in the combined summary sheet.
- Reduced Google Sheets read usage by reusing worksheet values during append operations.
- Added regression tests for the region exclusion behavior and existing scraper/date parsing logic.

## Known Current Issue
- If the spreadsheet upload fails, verify:
  - `GOOGLE_WORKSHEET_NAME` is set in `.env`
  - the service account has permission for the spreadsheet
  - `GOOGLE_SHEET_ID` is valid and not a malformed URL string

## Testing
- Run the test suite in `tests/` after any code changes.

## Recommended Next Step
- Confirm `credentials/scrapingdjpk-15ac9bdf40fe.json` is valid and authorized.
- Verify `.env` uses `GOOGLE_WORKSHEET_NAME` if set, or allow `GOOGLE_SHEET_NAME` as a fallback.
