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
from utils.logger import get_logger


def process_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a raw scraper record into a cleaned record.

    Args:
        raw: Raw dict from scraper with keys:
             url, content_type, post_date_raw, likes_raw, comments_raw,
             views_raw, reposts_raw, saves_raw, shares_raw, caption_raw

    Returns:
        Cleaned dict with normalized values and ingestion timestamp
    """
    logger = get_logger()
    cleaned: Dict[str, Any] = {
        "url": "",
        "content_type": "Post",
        "post_date": "N/A",
        "likes": "N/A",
        "comments": "N/A",
        "views": "N/A",
        "reach": "N/A",
        "reposts": "N/A",
        "saves": "N/A",
        "shares": "N/A",
        "followers": "N/A",
        "caption": "",
        "ingestion_timestamp": "",
    }

    try:
        url = raw.get("url", "") if isinstance(raw, dict) else ""
        content_type = raw.get("content_type") if isinstance(raw, dict) else None
        if not content_type or content_type == "N/A":
            content_type = "Post"

        cleaned["url"] = normalize_url(url)
        cleaned["content_type"] = content_type
        cleaned["post_date"] = normalize_date(raw.get("post_date_raw") if isinstance(raw, dict) else None, TIMEZONE)
        cleaned["likes"] = normalize_count(raw.get("likes_raw") if isinstance(raw, dict) else None)
        cleaned["comments"] = normalize_count(raw.get("comments_raw") if isinstance(raw, dict) else None)
        cleaned["views"] = normalize_count(raw.get("views_raw") if isinstance(raw, dict) else None)
        cleaned["reach"] = normalize_count(raw.get("reach_raw") if isinstance(raw, dict) else None)
        cleaned["reposts"] = normalize_count(raw.get("reposts_raw") if isinstance(raw, dict) else None)
        cleaned["saves"] = normalize_count(raw.get("saves_raw") if isinstance(raw, dict) else None)
        cleaned["shares"] = normalize_count(raw.get("shares_raw") if isinstance(raw, dict) else None)
        cleaned["followers"] = normalize_count(raw.get("followers_raw") if isinstance(raw, dict) else None)
        cleaned["caption"] = normalize_caption(raw.get("caption_raw") if isinstance(raw, dict) else None, CAPTION_PREVIEW_LENGTH)
    except Exception as exc:
        logger.warning("Failed to process raw record: %s", exc)

    try:
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        cleaned["ingestion_timestamp"] = now.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as exc:
        logger.warning("Failed to generate ingestion timestamp: %s", exc)
        cleaned["ingestion_timestamp"] = "N/A"

    return cleaned

