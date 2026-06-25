"""
Configuration module for Instagram Engagement Scraper.
Loads environment variables from .env file and exposes them as module-level constants.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _get_env(key: str, default: str = "") -> str:
    value = os.getenv(key, default)
    return value.strip() if isinstance(value, str) else default

# Google Sheets settings
GOOGLE_SHEET_ID = _get_env("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIAL_PATH = _get_env("GOOGLE_CREDENTIAL_PATH") or "credentials/service_account.json"
GOOGLE_CREDENTIAL_PATH_B64 = _get_env("GOOGLE_CREDENTIAL_PATH_B64")
GOOGLE_WORKSHEET_NAME = _get_env("GOOGLE_WORKSHEET_NAME") or "Engagement Report"

# Timezone and scraping settings
TIMEZONE = _get_env("TIMEZONE") or "Asia/Jakarta"
SCRAPER_STRATEGY = _get_env("SCRAPER_STRATEGY") or "instaloader"
SCRAPER_STRATEGY = SCRAPER_STRATEGY.lower()
if SCRAPER_STRATEGY not in ["instaloader", "playwright"]:
    SCRAPER_STRATEGY = "instaloader"

INSTAGRAM_USERNAME = _get_env("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = _get_env("INSTAGRAM_PASSWORD")

REQUEST_DELAY_SECONDS = int(_get_env("REQUEST_DELAY_SECONDS", "3"))
MAX_RETRIES = int(_get_env("MAX_RETRIES", "3"))
CAPTION_PREVIEW_LENGTH = int(_get_env("CAPTION_PREVIEW_LENGTH", "100"))

if SCRAPER_STRATEGY == "instaloader" and (not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD):
    import warnings
    warnings.warn(
        "INSTAGRAM_USERNAME or INSTAGRAM_PASSWORD not set. "
        "Instaloader will only access public content and may be rate-limited."
    )

if not GOOGLE_SHEET_ID:
    import warnings
    warnings.warn(
        "GOOGLE_SHEET_ID is not set. Google Sheets upload will fail until configured."
    )

if not os.path.exists(os.path.dirname(GOOGLE_CREDENTIAL_PATH)) and not GOOGLE_CREDENTIAL_PATH_B64:
    import warnings
    warnings.warn(
        f"Credentials directory '{os.path.dirname(GOOGLE_CREDENTIAL_PATH)}' does not exist. "
        "Ensure you have set GOOGLE_CREDENTIAL_PATH or GOOGLE_CREDENTIAL_PATH_B64."
    )
