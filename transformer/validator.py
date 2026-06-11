from datetime import datetime


REQUIRED_FIELDS = [
    "nama_file",
    "anggaran_M",
    "realisasi_M",
    "presentase",
    "tanggal_pengambilan",
    "kab_kota",
]


def validate_record(record: dict) -> None:
    if not isinstance(record, dict):
        raise ValueError("Record must be a dictionary")

    for field in REQUIRED_FIELDS:
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    if not record["kab_kota"] or not isinstance(record["kab_kota"], str):
        raise ValueError("kab_kota must be a non-empty string")

    if record["anggaran_M"] is None or record["realisasi_M"] is None:
        raise ValueError("Anggaran and realisasi values cannot be null")

    if record["anggaran_M"] < 0 or record["realisasi_M"] < 0:
        raise ValueError("Anggaran and realisasi values must be non-negative")

    if not (0 <= record["presentase"] <= 100):
        raise ValueError("Presentase must be between 0 and 100")

    try:
        datetime.fromisoformat(record["tanggal_pengambilan"])
    except Exception as err:
        raise ValueError(f"tanggal_pengambilan is not a valid ISO date: {record['tanggal_pengambilan']}") from err
