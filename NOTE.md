# NOTE

## What I understand now
- The current scraper pipeline writes all scraped rows into a single worksheet.
- `main.py` collects records from every region and `services/spreadsheet_service.py` appends them to `DEFAULT_WORKSHEET`.
- The existing upload logic does not separate data by region into its own sheet.
- The desired future format is:
  - each region gets its own worksheet/tab
  - each worksheet follows the example spreadsheet layout
  - updates should preserve the region-specific structure and formatting

## What needs to change next
1. Review the exact spreadsheet example layout.
   - sheet/tab names for each region
   - column headers and column order
   - whether data should append or replace existing rows
   - whether each worksheet needs a header row and timestamp columns
2. Update `SpreadsheetService` so it can:
   - open one spreadsheet by `GOOGLE_SHEET_ID`
   - select or create a worksheet for each region
   - optionally write headers if the worksheet is new
3. Update `main.py` so that records are grouped by `kab_kota` and written to the matching region worksheet instead of a single worksheet.
4. Preserve the current validation and deduplication behavior before upload.
5. Implement the exact fixed worksheet format for every region.
   - column headers must be: `Source.name`, `Akun`, `Anggaran.M`, `Realisasi.M`, `Presentase`, `Tanggal`, `Kab/Kota`
   - rows must include the fixed category names below in the same order for all regions
   - row labels are patents and do not change across provinces

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
