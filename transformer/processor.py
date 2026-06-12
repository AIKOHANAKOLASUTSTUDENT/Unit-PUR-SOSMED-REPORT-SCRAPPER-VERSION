from typing import Dict, List

import pandas as pd

from .normalizer import parse_currency_m, parse_percentage
from .validator import validate_record


def build_record(region_name: str, nama_file: str, tanggal_pengambilan: str, raw_row: List[str]) -> Dict[str, object]:
    if len(raw_row) < 5:
        raise ValueError("Raw row does not contain enough cells")

    akun = raw_row[1].strip() if len(raw_row) > 1 and raw_row[1].strip() else raw_row[0].strip()
    anggaran = parse_currency_m(raw_row[2])
    realisasi = parse_currency_m(raw_row[3])
    presentase = parse_percentage(raw_row[4])

    record = {
        "nama_file": nama_file,
        "akun": akun,
        "anggaran_M": anggaran,
        "realisasi_M": realisasi,
        "presentase": presentase,
        "tanggal_pengambilan": tanggal_pengambilan,
        "kab_kota": region_name,
    }

    validate_record(record)
    return record


def deduplicate_records(records: List[Dict[str, object]]) -> List[Dict[str, object]]:
    if not records:
        return []

    df = pd.DataFrame(records)
    if df.empty:
        return []

    df = df.drop_duplicates(
        subset=["nama_file", "kab_kota", "anggaran_M", "realisasi_M", "presentase", "tanggal_pengambilan"]
    )
    return df.to_dict(orient="records")
