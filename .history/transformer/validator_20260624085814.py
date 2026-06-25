"""
Validator for Instagram engagement records.
Validates cleaned records before uploading to Google Sheets.
"""

from typing import Tuple
from utils.logger import get_logger


def validate_record(record: dict) -> Tuple[bool, str]:
    """
    Validate a cleaned engagement record.

    Args:
        record: Cleaned dict with engagement metrics

    Returns:
        Tuple of (is_valid, reason) - reason is empty string if valid
    """
    logger = get_logger()

    if not isinstance(record, dict):
        reason = "Record is None or not a dict"
        logger.warning(reason)
        return False, reason

    url = record.get("url")
    if not url or not isinstance(url, str) or not url.startswith("https://www.instagram.com/"):
        reason = f"Invalid or missing URL: {url}"
        logger.warning(reason)
        return False, reason

    content_type = record.get("content_type")
    if not content_type or content_type == "N/A":
        record["content_type"] = "Post"
        content_type = "Post"

    valid_types = ["Post", "Reel", "Carousel", "Unknown"]
    if content_type not in valid_types:
        reason = f"Invalid content_type: {content_type}"
        logger.warning(f"{reason} | URL: {url}")
        return False, reason

    post_date = record.get("post_date")
    if post_date is None:
        reason = "post_date missing"
        logger.warning(f"{reason} | URL: {url}")
        return False, reason

    if post_date == "N/A":
        return True, ""

    likes_missing = "likes" not in record
    if likes_missing:
        reason = "likes missing"
        logger.warning(f"{reason} | URL: {url}")
        return False, reason

    ingestion_timestamp = record.get("ingestion_timestamp")
    if ingestion_timestamp is None:
        reason = "ingestion_timestamp missing"
        logger.warning(f"{reason} | URL: {url}")
        return False, reason

    return True, ""

