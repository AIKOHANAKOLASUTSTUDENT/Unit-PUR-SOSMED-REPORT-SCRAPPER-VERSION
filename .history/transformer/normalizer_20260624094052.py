"""
Normalization functions for Instagram engagement metrics.
Converts raw scraped data into standardized formats.
"""

import re
from datetime import datetime
import pytz
from typing import Union, Optional


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
        ]
        
        parsed_date = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(value.strip(), fmt)
                break
            except ValueError:
                continue
        
        if parsed_date is None:
            return "N/A"
        
        # If source string has no timezone information, parse as UTC for ISO timestamps
        if fmt == "%Y-%m-%dT%H:%M:%S" and parsed_date.tzinfo is None:
            parsed_date = pytz.utc.localize(parsed_date)

        # Convert to target timezone
        tz = pytz.timezone(timezone)
        if parsed_date.tzinfo is None:
            parsed_date = tz.localize(parsed_date)
        else:
            parsed_date = parsed_date.astimezone(tz)
        
        return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "N/A"


def normalize_caption(text: Optional[str], max_length: int = 100) -> str:
    """
    Normalize caption text.
    
    Args:
        text: Raw caption text or None
        max_length: Maximum length before truncation
    
    Returns:
        Cleaned caption text, truncated if needed, or empty string if None
    """
    if text is None:
        return ""
    
    # Strip whitespace and replace newlines with space
    text = " ".join(text.strip().split())
    
    # Truncate if too long
    if len(text) > max_length:
        return text[:max_length] + "..."
    
    return text


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
