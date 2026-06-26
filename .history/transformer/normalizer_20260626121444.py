"""
Normalization functions for Instagram engagement metrics.
Converts raw scraped data into standardized formats.
"""

import re
from datetime import datetime
import pytz
from typing import Union, Optional

from config.settings import INSTAGRAM_USERNAME
# dateutil for robust ISO timestamp parsing
from dateutil import parser as dateutil_parser


def normalize_count(value: Union[str, int, None]) -> Union[int, str]:
    """
    Normalize engagement count from various Instagram formats.
    
    Args:
        value: Raw count value - can be "1.2K", "980K", "1.5M", "2.3B", 
               plain integer string "12400", None, "", or "N/A"
    
    Returns:
        Integer count or "N/A" if unparseable
        
    Examples:
        "1.2K" -> 1200
        "980K" -> 980000
        "1.5M" -> 1500000
        "2.3B" -> 2300000000
        "12,400" -> 12400
        None -> "N/A"
    """
    if value is None or value == "" or value == "N/A":
        return "N/A"
    
    if isinstance(value, int):
        return value
    
    if not isinstance(value, str):
        return "N/A"
    
    # Strip commas
    value = value.replace(",", "")
    
    # Handle case-insensitive multipliers
    match = re.match(r"^([\d.]+)\s*([kmb]?)$", value.strip(), re.IGNORECASE)
    if not match:
        return "N/A"
    
    number_str, multiplier = match.groups()
    
    try:
        number = float(number_str)
        multiplier = multiplier.lower()
        
        if multiplier == "k":
            return int(number * 1000)
        elif multiplier == "m":
            return int(number * 1000000)
        elif multiplier == "b":
            return int(number * 1000000000)
        else:
            return int(number)
    except (ValueError, AttributeError):
        return "N/A"


def normalize_date(value: Optional[str], timezone: str = "Asia/Jakarta") -> str:
    """
    Normalize date to standard format.
    
    Args:
        value: Date string in various formats or None
        timezone: Target timezone string
    
    Returns:
        Formatted date string "YYYY-MM-DD HH:MM:SS" or "N/A" if unparseable
    """
    if not value or value == "N/A":
        return "N/A"
    
    try:
        # Try parsing various common formats
        date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S+0000",
        ]
        
        parsed_date = None
        parsed_fmt = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(value.strip(), fmt)
                parsed_fmt = fmt
                break
            except ValueError:
                continue

        # If strptime couldn't parse, try dateutil as fallback
        if parsed_date is None:
            try:
                parsed_date = dateutil_parser.parse(value)
            except Exception:
                return "N/A"

        # If the parsed datetime has no tzinfo and the format was an explicit +0000
        # treat it as UTC; otherwise assume naive datetimes are UTC as a safe default
        if getattr(parsed_date, "tzinfo", None) is None:
            parsed_date = pytz.utc.localize(parsed_date)

        # Convert to target timezone
        try:
            tz = pytz.timezone(timezone)
            parsed_date = parsed_date.astimezone(tz)
        except Exception:
            # If timezone conversion fails, still return UTC-based time
            parsed_date = parsed_date.astimezone(pytz.utc)

        return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "N/A"


def normalize_caption(text: Optional[str], max_length: int = 100) -> str:
    """
    Normalize caption text into a content title.
    
    Args:
        text: Raw caption text or None
        max_length: Maximum length before truncation
    
    Returns:
        Extracted title text, truncated if needed, or empty string if None
    """
    if text is None:
        return ""

    lines = [line.strip(' "\'') for line in re.split(r'[\r\n]+', text) if line.strip()]
    if not lines:
        return ""

    keywords = [
        "cbp", "cbprupiah", "cbp rupiah", "qris", "lomba", "edukasi",
        "story telling", "konten digital", "hari wanita", "smp", "smpn",
        "kgpm", "genbi", "komisi wanita", "sidang"
    ]

    best = None
    for line in lines:
        low = line.lower()
        if any(keyword in low for keyword in keywords):
            best = line
            break

    if best is None:
        for line in lines:
            if not re.match(r'^[@#]|^\([^)]*\)$', line):
                best = line
                break

    best = best or lines[0]
    best = re.sub(r'\s*\([^)]*\)\s*$', '', best).strip()
    best = " ".join(best.split())

    if len(best) > max_length:
        best = best[:max_length].rstrip() + "..."

    return best


def normalize_collab_status(text: Optional[str], author_username: str = "") -> str:
    """
    Determine collab status relative to the CBP account.

    Rules:
    - If the uploader is the CBP account, return "konten akun cbp"
    - If the caption mentions the CBP account, return "sudah collab"
    - Otherwise, return "belum collab"
    """
    cbp_handle = INSTAGRAM_USERNAME.strip().lower() or "cbp.rupiah_qris_peka_bi_sulut"
    author_username_clean = (author_username or "").strip().lower()

    if author_username_clean and author_username_clean == cbp_handle:
        return "konten akun cbp"

    if not text:
        return "belum collab"

    lower_text = text.lower()
    mention_variants = [
        cbp_handle,
        f"@{cbp_handle}",
        "cbp rupiah qris",
        "cbp.rupiah",
        "cbprupiah",
    ]

    if any(variant in lower_text for variant in mention_variants):
        return "sudah collab"

    return "belum collab"


def normalize_url(url: str) -> str:
    """
    Normalize Instagram URL.
    
    Args:
        url: Raw Instagram URL
    
    Returns:
        Cleaned URL
    """
    if not url:
        return url
    
    # Remove query parameters
    url = url.split("?")[0]
    
    # Ensure trailing slash
    if not url.endswith("/"):
        url += "/"
    
    return url
