# NOTE

## Status
- Big update executed: every region now uploads to its own worksheet with fixed headers and an ingestion timestamp.
- Added historical scraping support and CLI flags for `--history-start`, `--history-end`, and `--regions`.
- Duplicate prevention is now applied by exact row match, and worksheet expansion is handled automatically.

## What I understand now
- The current scraper pipeline collects rows for each region, normalizes and validates them, then groups them by `kab_kota`.
- `main.py` now writes grouped rows into region-specific worksheets instead of a single default sheet.
- `services.spreadsheet_service.py` now ensures headers, appends rows safely, expands the worksheet when full, and skips exact duplicate rows.
- A new `Ingestion.Timestamp` column is included on each appended row.
- The desired future format remains:
  - each region gets its own worksheet/tab
  - each worksheet follows the example spreadsheet layout
  - updates should preserve the region-specific structure and formatting

## What needs to change next
1. Review the exact spreadsheet example layout.
   - sheet/tab names for each region
   - column headers and column order
   - whether data should append or replace existing rows
   - whether each worksheet should include `Ingestion.Timestamp`
2. Confirm the exact row category order for each region and whether all fixed categories should be present, including duplicates like `Belanja Pegawai` and `Belanja Modal`.
3. Verify that our region worksheet names match the expected tab names exactly.
4. Review deduplication strategy for special cases where new rows may match existing rows exactly but should still be retained.
5. Keep the current validation and normalization behavior in place.

## Change summary
- `scraper/apbd_scraper.py`: added direct GET scraping, historical period support, shared `tanggal_pengambilan` fallback, and robust row extraction.
- `main.py`: added region grouping, per-region worksheet upload, ingestion timestamp, and history CLI parsing.
- `services/spreadsheet_service.py`: improved header handling, duplicate row skipping, and worksheet row expansion.
- `config/settings.py`: added fixed sheet headers and category list.
- Tests: added/updated spreadsheet, transformer, and scraper tests to cover exact duplicates, timestamp behavior, and date parsing.

## Exact Required Sheet Format
- Column headers:
  1. Source.name
  2. Akun
  3. Anggaran.M
  4. Realisasi.M
  5. Presentase
  6. Tanggal
  7. Kab/Kota

- Fixed row categories (same for every region):
  1. Pendapatan Daerah
  2. PAD
  3. Pajak Daerah
  4. Retribusi Daerah
  5. Hasil Pengelolaan Kekayaan Daerah yang Dipisahkan
  6. Lain-Lain PAD yang Sah
  7. TKDD
  8. Pendapatan Transfer Pemerintah Pusat
  9. Pendapatan Lainnya
  10. Pendapatan Hibah
  11. Belanja Daerah
  12. Belanja Pegawai
  13. Belanja Pegawai
  14. Belanja Barang dan Jasa
  15. Belanja Barang dan Jasa
  16. Belanja Modal
  17. Belanja Modal
  18. Belanja Lainnya
  19. Belanja Bagi Hasil
  20. Belanja Bantuan Keuangan
  21. Belanja Bunga
  22. Belanja Subsidi
  23. Belanja Hibah
  24. Belanja Bantuan Sosial
  25. Belanja Tidak Terduga
  26. Pembiayaan Daerah
  27. Penerimaan Pembiayaan Daerah
  28. Sisa Lebih Perhitungan Anggaran Tahun Sebelumnya
  29. Pengeluaran Pembiayaan Daerah
  30. Penyertaan Modal Daerah
  31. Pembayaran Cicilan Pokok Utang yang Jatuh Tempo
  32. Pendapatan Daerah

## Example row shape
- Sample collected row data should match the sheet columns exactly:
  - `2023_08csv`, `Pendapatan Daerah`, `1672,22`, `920,02`, `,55,02`, `,01/08/2023`, `Manado`
- `Presentase` may be greater than 100 and should not be rejected.

## Current limitation
- The code currently assumes a single worksheet and appends rows as:
  `nama_file`, `anggaran_M`, `realisasi_M`, `presentase`, `tanggal_pengambilan`, `kab_kota`
- This is not sufficient for a future design where each region has its own sheet.

## What I need from you
- the example spreadsheet or a screenshot of the sheet layout
- the exact header row and any extra columns required per region
- whether the region worksheet names should match `kab_kota` values exactly
- whether the scraper should create missing worksheets automatically

## Next update task
- implement region-specific worksheet selection and row grouping once the example format is confirmed
