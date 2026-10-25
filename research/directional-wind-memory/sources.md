# Source provenance

## Local repository inputs

- `scripts/phase5a.py`, `scripts/phase5b.py`, frozen `site/data/prospective/model-artifacts.json`: model feature definitions and frozen Phase 6 artifact.
- `site/data/history/hourly/*.json.gz`: retrospective hourly archive; schema v3A.1. NWCL1 wind components are stored in knots; MAUL1 gage height remains native. This archive contains no original receipt timestamps or complete sensor/QC metadata.
- `research/rise-failure-audit/analysis.json`, `event-diagnostics.csv`, `false-alert-clusters.csv`: reused historical significant-rise evaluation diagnostics. Not an independent validation sample.
- `site/data/history/phase3b/control-windows.csv`: eligible nonresponse control candidate status and coverage. These are descriptive controls, not guaranteed matched independent events.
- `scripts/build.py`, `scripts/history.py`, `scripts/analyze.py`: event and archive construction rules.

## Public scientific context

- NOAA PSL, North American Regional Reanalysis data: <https://psl.noaa.gov/data/gridded/data.narr.html>. Dataset description lists ~32-km, 3-hourly fields from 1979 onward, including mean sea-level pressure and 10-m winds. It is regional context, not an in-lake observation. No NARR field values were downloaded in this session.
- User-provided `Alberto effects.pptx` (21 slides; inspected as text and rendered images; SHA-256 `0341076c81337d4c669fbb4f5db35d21da3d925733bcc736b74c7ccaf20db5ba`). The deck has static screenshot charts rather than embedded numeric chart series.
- NOAA/NHC Alberto Tropical Cyclone Report: <https://www.nhc.noaa.gov/data/tcr/AL012024_Alberto.pdf>; NHC documents formation 2024-06-19 12 UTC and reported landfall near Tampico 2024-06-20 around 09 UTC.
- NOAA/WPC Alberto overview: <https://www.wpc.ncep.noaa.gov/tropical/rain/alberto2024.html>; documents the preceding mid-June disturbed-weather low and named storm period.
- NOAA/NHC Sally Tropical Cyclone Report: <https://www.nhc.noaa.gov/data/tcr/AL192020_Sally.pdf>; identifies historical WeatherFlow XPTN at 30.20N, 90.12W and reports 12.5 m / 1-minute wind for the Sally event. This does not certify the 2024 sensor configuration.
- NOAA/NHC Beryl Tropical Cyclone Report: <https://www.nhc.noaa.gov/data/tcr/AL022024_Beryl.pdf>; documents Beryl chronology and Texas landfall at 08:40 UTC July 8.
- NOAA/NWS Houston-Galveston Beryl summary: <https://www.weather.gov/hgx/beryl2024>; documents June 28 formation and Texas impacts.
- WindAlert/SailFlow Mid-Lake Causeway spot 36469: <https://windalert.com/spot/36469>. Current platform title is “MDLL1 - Mid-Lake Pontchartrain on Causeway”. The deck-to-spot crosswalk is likely but not certified by WeatherFlow station metadata.
- WeatherFlow/Tempest remote data access policy: <https://apidocs.tempestwx.com/reference/remote-data-access-policy> and API observation endpoint: <https://apidocs.tempestwx.com/reference/get_observations-stn-station-id>. Third-party station observations require authorized access.
- WeatherFlow support, Wind Archives & Statistics: <https://help.tempest.earth/hc/en-us/articles/4418099105819-Wind-Archives-Statistics>. The page states raw historical downloads are available via professional-services pricing/API access packages; archive graphs and metadata are described separately.
- NOAA CO-OPS data page for New Canal (station 8761927): <https://tidesandcurrents.noaa.gov/stationhome.html?id=8761927>. The deck’s slides 16 and 20 show CO-OPS New Canal charts for 2024-06-12–06-27 and 2024-07-01–07-10, respectively. The reproducible archive metrics in this package use station-consistent MLLW residuals, not deck MHHW absolute values.
- Tempest API documentation: <https://apidocs.tempestwx.com/reference/quick-start> and remote data access policy <https://apidocs.tempestwx.com/reference/remote-data-access-policy>. Access conditions apply; public observation access and raw historical retrieval may require subscription/service access. This analysis did not retrieve historical XPTN observations.

The initial Drive URL could not be accessed. The later attached PPTX was available and is the source used for the deck audit. The original WeatherFlow raw series remains unavailable; no numerical data are inferred from chart pixels.
