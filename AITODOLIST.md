# AI TODO LIST

## Purpose
This file is the manual task guide for the AI model. It is intentionally written so the AI can review the current project state and follow strict safety rules before making changes.

## Current Project State
- Project is a DJPK APBD scraper that uses Playwright to load the DJPK portal and extract APBD summary data.
- The workflow is:
  1. Scrape region data in `scraper/apbd_scraper.py`.
  2. Normalize and validate records in `transformer/`.
  3. Deduplicate records in `main.py`.
  4. Upload rows to Google Sheets via `services/spreadsheet_service.py`.
- Logging is captured in `logs/scraper.log`.
- The environment file `.env` is the configuration source.

## High Priority Tasks
1. Confirm `.env` uses the correct worksheet variable name:
   - `GOOGLE_WORKSHEET_NAME=APBD`
2. Verify the `GOOGLE_SHEET_ID` value is valid and the service account has access.
3. Inspect `logs/scraper.log` for the latest scraping or upload errors before editing code.
4. If scraper failures are present, check Playwright selectors and page interaction logic carefully.
5. After any code change, run the tests in `tests/`.
6. The sheet format is fixed and must use the exact headers and row category names provided by the user.
7. Collected rows must match the exact sheet column order and the sample row shape shown by the user.

## Important Warnings for the AI
- Do not change or delete important code without explicit user approval.
- Do not change generated code or code that is clearly marked as generated.
- Do not modify `.venv`, `__pycache__`, or unrelated environment files.
- Always read the current error log before continuing to correct a problem.
- Always run tests after making code changes.
- If the project contains a file or folder named `generated`, preserve it completely.
- Ask the user before refactoring large sections or changing core scraping/upload workflows.

## Restrictions
- Never remove code from `main.py`, `scraper/apbd_scraper.py`, `services/spreadsheet_service.py`, or `transformer/` unless the user explicitly requests a refactor.
- Never change the environment variable names used in `config/settings.py` unless the user confirms the change.
- Never delete or alter the sheet-value normalization behavior in `SpreadsheetService` without approval.

## How to Use This File
- Read this file at the start of each new task.
- Update the task list manually when the user assigns new priorities.
- Treat the rules above as binding guidance for all code edits.
