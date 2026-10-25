# Source provenance

## Local repository inputs

- `scripts/phase5a.py`, `scripts/phase5b.py`, frozen `site/data/prospective/model-artifacts.json`: model feature definitions and frozen Phase 6 artifact.
- `site/data/history/hourly/*.json.gz`: retrospective hourly archive; schema v3A.1. NWCL1 wind components are stored in knots; MAUL1 gage height remains native. This archive contains no original receipt timestamps or complete sensor/QC metadata.
- `research/rise-failure-audit/analysis.json`, `event-diagnostics.csv`, `false-alert-clusters.csv`: reused historical significant-rise evaluation diagnostics. Not an independent validation sample.
- `site/data/history/phase3b/control-windows.csv`: eligible nonresponse control candidate status and coverage. These are descriptive controls, not guaranteed matched independent events.
- `scripts/build.py`, `scripts/history.py`, `scripts/analyze.py`: event and archive construction rules.

## Public scientific context

- NOAA PSL, North American Regional Reanalysis data: <https://psl.noaa.gov/data/gridded/data.narr.html>. Dataset description lists ~32-km, 3-hourly fields from 1979 onward, including mean sea-level pressure and 10-m winds. It is regional context, not an in-lake observation. No NARR field values were downloaded in this session.
- NOAA/NHC Alberto Tropical Cyclone Report: <https://www.nhc.noaa.gov/data/tcr/AL012024_Alberto.pdf>.
- NOAA/WPC Alberto rainfall/event page: <https://www.wpc.ncep.noaa.gov/tropical/rain/alberto2024.html>.
- NOAA/WPC Beryl rainfall/event page: <https://www.wpc.ncep.noaa.gov/tropical/rain/beryl2024.html>.
- Tempest API documentation: <https://apidocs.tempestwx.com/reference/quick-start> and remote data access policy <https://apidocs.tempestwx.com/reference/remote-data-access-policy>. Access conditions apply; public observation access and raw historical retrieval may require subscription/service access. This analysis did not retrieve historical XPTN observations.

The Alberto presentation URL supplied in chat returned a 404 from connected Google Drive/Slides access. Its contents therefore are not a source used in this package.
