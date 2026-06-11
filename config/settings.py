import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

TARGET_URL = "https://djpk.kemenkeu.go.id/portal/data/apbd"
PROVINCE_CODE = "18"
DEFAULT_WORKSHEET = os.getenv("GOOGLE_WORKSHEET_NAME", "Sheet1")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIAL_PATH = os.getenv("GOOGLE_CREDENTIAL_PATH")
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").strip().lower() in ("1", "true", "yes")
DEFAULT_USER_AGENT = os.getenv(
    "PLAYWRIGHT_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)
PLAYWRIGHT_ARGS = os.getenv("PLAYWRIGHT_ARGS", "--disable-blink-features=AutomationControlled").split()

FIXED_REGIONS = [
    {"name": "Semua Pemda", "value": "--"},
    {"name": "Provinsi Sulawesi Utara", "value": "00"},
    {"name": "Kab.Bolaang Mongondow", "value": "01"},
    {"name": "Kab.Minahasa", "value": "02"},
    {"name": "Kab.Sangihe", "value": "03"},
    {"name": "Kota Bitung", "value": "04"},
    {"name": "Kota Manado", "value": "05"},
    {"name": "Kab.Kepulauan Talaud", "value": "06"},
    {"name": "Minahasa Selatan", "value": "07"},
    {"name": "Tomohon", "value": "08"},
    {"name": "Minahasa Utara", "value": "09"},
    {"name": "Kab.Kep.Siau Tagulandang Biaro", "value": "10"},
    {"name": "Kota Kotamobagu", "value": "11"},
    {"name": "Kab.Bolaang Mongondow Utara", "value": "12"},
    {"name": "Kab.Minahasa Tenggara", "value": "13"},
    {"name": "Kab.Bolaang Mongondow Timur", "value": "14"},
    {"name": "Kab.Bolaang Mongondow Selatan", "value": "15"},
]

MONTH_NAMES = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}
