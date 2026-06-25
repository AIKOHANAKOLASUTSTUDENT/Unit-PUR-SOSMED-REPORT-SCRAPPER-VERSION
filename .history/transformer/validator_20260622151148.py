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
    
    # Check URL presence and format
    url = record.get("url")
    if not url:
        reason = "Missing URL"
        logger.warning(reason)
        return False, reason
    
    if not url.startswith("https://www.instagram.com/"):
        reason = f"Invalid URL format: {url}"
        logger.warning(reason)
        return False, reason
    
    # Check content_type
    content_type = record.get("content_type", "Unknown")
    valid_types = ["Post", "Reel", "Carousel", "Unknown"]
    if content_type not in valid_types:
        reason = f"Invalid content_type: {content_type}"
        logger.warning(reason)
        return False, reason
    
    # Check post_date
    post_date = record.get("post_date")
    if not post_date:
        reason = "Missing post_date"
        logger.warning(reason)
        return False, reason
    
    if post_date == "N/A":
        reason = "post_date is N/A (unparseable)"
        logger.warning(reason)
        return False, reason
    
    # Check likes (must be int or "N/A", not None or empty string)
    likes = record.get("likes")
    if likes is None or likes == "":
        reason = "Invalid likes value"
        logger.warning(reason)
        return False, reason
    
    if not isinstance(likes, int) and likes != "N/A":
        reason = f"likes must be int or 'N/A', got {type(likes)}: {likes}"
        logger.warning(reason)
        return False, reason
    
    # Check ingestion_timestamp
    ingestion_timestamp = record.get("ingestion_timestamp")
    if not ingestion_timestamp:
        reason = "Missing ingestion_timestamp"
        logger.warning(reason)
        return False, reason
    
    return True, ""

