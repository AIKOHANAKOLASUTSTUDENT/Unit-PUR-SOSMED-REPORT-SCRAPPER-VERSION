import re
from datetime import datetime

from config.settings import MONTH_NAMES

CURRENCY_PATTERN = re.compile(r"([0-9\.\,\-]+)\s*M", re.IGNORECASE)
PERCENTAGE_PATTERN = re.compile(r"[-+]?[0-9]+(?:\.[0-9]+)?")
DATE_PATTERN = re.compile(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})")


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

    match = DATE_PATTERN.search(raw_date.strip())
    if not match:
        raise ValueError(f"Unable to parse tanggal pengambilan: {raw_date}")

    day = int(match.group(1))
    month_name = match.group(2).strip().lower()
    year = int(match.group(3))
    month = MONTH_NAMES.get(month_name)
    if not month:
        raise ValueError(f"Unknown month name in tanggal pengambilan: {month_name}")

    return datetime(year=year, month=month, day=day).strftime("%Y-%m-%d")
