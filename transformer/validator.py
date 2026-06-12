from datetime import datetime


REQUIRED_FIELDS = [
    "nama_file",
    "akun",
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

    # NOTE: Nilai negatif diizinkan — data DJPK resmi bisa negatif untuk
    # komponen Pembiayaan Daerah (pengeluaran pembiayaan, cicilan, dsb).

    if record["presentase"] is None:
        raise ValueError("Presentase cannot be null")

    try:
        datetime.fromisoformat(record["tanggal_pengambilan"])
    except Exception as err:
        raise ValueError(f"tanggal_pengambilan is not a valid ISO date: {record['tanggal_pengambilan']}") from err
