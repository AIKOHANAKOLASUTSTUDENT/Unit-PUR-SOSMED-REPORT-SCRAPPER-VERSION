"""
Record processor for Instagram engagement data.
Transforms raw scraped data into cleaned, normalized records.
"""

from datetime import datetime
import pytz
from typing import Dict, Any

from .normalizer import (
    normalize_count,
    normalize_date,
    normalize_caption,
    normalize_url,
)
from config.settings import TIMEZONE, CAPTION_PREVIEW_LENGTH


def process_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a raw scraper record into a cleaned record.
    
    Args:
        raw: Raw dict from scraper with keys:
             url, content_type, post_date, likes_raw, comments_raw, 
             views_raw, reposts_raw, saves_raw, shares_raw, caption_raw
    
    Returns:
        Cleaned dict with normalized values and ingestion timestamp
    """
    # Normalize engagement metrics
    cleaned = {
        "url": normalize_url(raw.get("url", "")),
        "content_type": raw.get("content_type", "Unknown"),
        "post_date": normalize_date(raw.get("post_date_raw"), TIMEZONE),
        "likes": normalize_count(raw.get("likes_raw")),
        "comments": normalize_count(raw.get("comments_raw")),
        "views": normalize_count(raw.get("views_raw")),
        "reposts": normalize_count(raw.get("reposts_raw", "N/A")),
        "saves": normalize_count(raw.get("saves_raw", "N/A")),
        "shares": normalize_count(raw.get("shares_raw", "N/A")),
        "caption": normalize_caption(raw.get("caption_raw"), CAPTION_PREVIEW_LENGTH),
    }
    
    # Add ingestion timestamp in target timezone
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    cleaned["ingestion_timestamp"] = now.strftime("%Y-%m-%d %H:%M:%S")
    
    return cleaned

