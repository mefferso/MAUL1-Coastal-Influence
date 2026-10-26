# Phase 6 archived source missingness and QC audit

Research-only, read-only audit of committed normalized monthly source rows.

- NWCL1 observed water rows with exact MLLW prediction timestamp: 944,998
- Those timestamp pairs with acceptable stored CO-OPS QC: 933,172
- CO-OPS water rows rejected by nonzero flags: 11,826
- USGS negative numeric missing markers retained in normalized archives: 0
- HADS exact 9,999,999-ft markers retained in normalized archives: 315
- HADS sentinel-contaminated numeric rows (>=1,000,000 ft): 0
- NDBC 99.0-m/s speed/gust sentinel conversions retained as normalized rows: 0

Counts by station, product variable, QC value, and finite range are in `source-missingness-qc-audit.json`.
Input file SHA-256 values are included for reproducibility.

This audit does not recalculate or replace historical features, frozen model artifacts, authentic issues, verification revisions, or published skill.

Limitations: the previous NDBC parser discarded rows with `WDIR=999` before writing normalized archives, so those lost speed/gust values cannot be reconstructed without archived provider bodies. Historical normalized records also lack source receipt times.
