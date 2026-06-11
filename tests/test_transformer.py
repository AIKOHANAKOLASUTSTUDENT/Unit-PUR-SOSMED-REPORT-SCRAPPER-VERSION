import unittest

from transformer.normalizer import parse_currency_m, parse_percentage, parse_tanggal_pengambilan
from transformer.processor import build_record, deduplicate_records


class TransformerTests(unittest.TestCase):
    def test_parse_currency_m(self):
        self.assertEqual(parse_currency_m("1.188.016,96 M"), 1188016.96)
        self.assertEqual(parse_currency_m("0,00 M"), 0.0)

    def test_parse_percentage(self):
        self.assertEqual(parse_percentage("30.43"), 30.43)
        self.assertEqual(parse_percentage("0"), 0.0)

    def test_parse_tanggal_pengambilan(self):
        self.assertEqual(parse_tanggal_pengambilan("07 Juni 2026"), "2026-06-07")

    def test_build_record(self):
        raw_row = ["", "Pendapatan Daerah", "1.188.016,96 M", "361.501,22 M", "30.43"]
        record = build_record("Kota Manado", "2026_06.csv", "2026-06-07", raw_row)

        self.assertEqual(record["nama_file"], "2026_06.csv")
        self.assertEqual(record["kab_kota"], "Kota Manado")
        self.assertEqual(record["anggaran_M"], 1188016.96)
        self.assertEqual(record["realisasi_M"], 361501.22)
        self.assertEqual(record["presentase"], 30.43)
        self.assertEqual(record["tanggal_pengambilan"], "2026-06-07")

    def test_deduplicate_records(self):
        records = [
            {"nama_file": "2026_06.csv", "anggaran_M": 1.0, "realisasi_M": 1.0, "presentase": 100.0, "tanggal_pengambilan": "2026-06-07", "kab_kota": "Kota Manado"},
            {"nama_file": "2026_06.csv", "anggaran_M": 1.0, "realisasi_M": 1.0, "presentase": 100.0, "tanggal_pengambilan": "2026-06-07", "kab_kota": "Kota Manado"},
        ]
        deduplicated = deduplicate_records(records)
        self.assertEqual(len(deduplicated), 1)


if __name__ == "__main__":
    unittest.main()
