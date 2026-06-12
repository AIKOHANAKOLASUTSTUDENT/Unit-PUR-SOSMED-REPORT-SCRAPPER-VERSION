import re
from datetime import datetime

from config.settings import MONTH_NAMES

CURRENCY_PATTERN = re.compile(r"([0-9\.\,\-]+)\s*M", re.IGNORECASE)
PERCENTAGE_PATTERN = re.compile(r"[-+]?[0-9]+(?:\.[0-9]+)?")
DATE_PATTERN = re.compile(r"(\d{1,2})\s+([A-Za-z\.]+)\s+(\d{4})")
NUMERIC_DMY_PATTERN = re.compile(r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})")
ISO_DATE_PATTERN = re.compile(r"(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})")

MONTH_ALIASES = {
    "sep": "september",
    "sept": "september",
    "okt": "oktober",
    "nov": "november",
    "des": "desember",
}


def parse_currency_m(value: str) -> float:
    if not value or not isinstance(value, str):
        raise ValueError("Currency value is missing or invalid")

    match = CURRENCY_PATTERN.search(value)
    if not match:
        raise ValueError(f"Unable to parse currency value: {value}")

    text = match.group(1).replace('.', '').replace(',', '.')
    try:
        return float(text)
    except ValueError as err:
        raise ValueError(f"Unable to convert currency value to float: {value}") from err


def parse_percentage(value: str) -> float:
    if not value or not isinstance(value, str):
        raise ValueError("Percentage value is missing or invalid")

    match = PERCENTAGE_PATTERN.search(value)
    if not match:
        raise ValueError(f"Unable to parse percentage value: {value}")

    try:
        return float(match.group(0))
    except ValueError as err:
        raise ValueError(f"Unable to convert percentage to float: {value}") from err


def parse_tanggal_pengambilan(raw_date: str) -> str:
    if not raw_date or not isinstance(raw_date, str):
        raise ValueError("Tanggal pengambilan is missing or invalid")

    raw = raw_date.strip()

    # Accept ISO dates directly
    iso_match = ISO_DATE_PATTERN.fullmatch(raw)
    if iso_match:
        year = int(iso_match.group(1))
        month = int(iso_match.group(2))
        day = int(iso_match.group(3))
        return datetime(year=year, month=month, day=day).strftime("%Y-%m-%d")

    # Common numeric forms: DD/MM/YYYY or DD-MM-YYYY
    numeric_match = NUMERIC_DMY_PATTERN.fullmatch(raw)
    if numeric_match:
        day = int(numeric_match.group(1))
        month = int(numeric_match.group(2))
        year = int(numeric_match.group(3))
        return datetime(year=year, month=month, day=day).strftime("%Y-%m-%d")

    # Indonesian month names and common abbreviations
    match = DATE_PATTERN.search(raw)
    if match:
        day = int(match.group(1))
        month_name = match.group(2).strip().lower().rstrip('.')
        year = int(match.group(3))
        month_name = MONTH_ALIASES.get(month_name, month_name)
        month = MONTH_NAMES.get(month_name)
        if not month:
            raise ValueError(f"Unknown month name in tanggal pengambilan: {month_name}")

        return datetime(year=year, month=month, day=day).strftime("%Y-%m-%d")

    raise ValueError(f"Unable to parse tanggal pengambilan: {raw_date}")
