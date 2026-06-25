"""
Configuration module for Instagram Engagement Scraper.
Loads environment variables from .env file and exposes them as module-level constants.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Required settings
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
if not GOOGLE_SHEET_ID:
    raise ValueError("GOOGLE_SHEET_ID is required in .env file")

# Optional credential settings
GOOGLE_CREDENTIAL_PATH = os.getenv("GOOGLE_CREDENTIAL_PATH", "credentials/service_account.json")
GOOGLE_CREDENTIAL_PATH_B64 = os.getenv("GOOGLE_CREDENTIAL_PATH_B64", "")

# Worksheet and timezone settings
GOOGLE_WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "Engagement Report")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")

# Scraper strategy
SCRAPER_STRATEGY = os.getenv("SCRAPER_STRATEGY", "instaloader")
if SCRAPER_STRATEGY not in ["instaloader", "playwright"]:
    raise ValueError(f"SCRAPER_STRATEGY must be 'instaloader' or 'playwright', got '{SCRAPER_STRATEGY}'")

# Instagram credentials (required for instaloader strategy)
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")

if SCRAPER_STRATEGY == "instaloader" and (not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD):
    import warnings
    warnings.warn(
        "INSTAGRAM_USERNAME or INSTAGRAM_PASSWORD not set. "
        "Instaloader will only access public accounts and may be rate-limited."
    )

# Tuning settings
REQUEST_DELAY_SECONDS = int(os.getenv("REQUEST_DELAY_SECONDS", "3"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
CAPTION_PREVIEW_LENGTH = int(os.getenv("CAPTION_PREVIEW_LENGTH", "100"))

# Validate settings at import time
if not os.path.exists(os.path.dirname(GOOGLE_CREDENTIAL_PATH)) and not GOOGLE_CREDENTIAL_PATH_B64:
    import warnings
    warnings.warn(
        f"Credentials directory '{os.path.dirname(GOOGLE_CREDENTIAL_PATH)}' does not exist. "
        "Ensure you have set GOOGLE_CREDENTIAL_PATH or GOOGLE_CREDENTIAL_PATH_B64."
    )
