# Sources and provenance

All analyzed observations come from the repository's archived Phase 3A hourly data. Exact monthly file SHA-256 values, case windows and the analysis settings are recorded in `diagnostics.json`.

## Repository sources

- `site/data/history/hourly/*.json.gz`: committed Phase 3A hourly valid-time observations and aggregates. The run reads the event months only, not raw provider feeds.
- `site/data/history/phase3b/response-events.csv`: Phase 3B catalog outcome labels and native MAUL1 event dates; onsets/peaks/recoveries are response definitions, not independent meteorological forcing times.
- `site/data/history/phase3b/control-windows.csv`: fixed July 2021 low-variation control candidate.
- `docs/phase5a-methodology.md`, `docs/phase5b-methodology.md`, `docs/phase7-data-quality.md`: model issue-time/data quality restrictions and archived-data caveats.
- `docs/spatial-forcing-feasibility.md`: merged PR #58 source inventory, station exposure, availability and gauge identity limitations.
- `research/directional-wind-memory/report.md`, `sources.md`, and `event_periods.py`: merged PR #59 wind-source correction, WeatherFlow recovery status, official storm chronology and separate June 2024 transition/Beryl intervals.
- `scripts/build.py`, `scripts/history.py`, `scripts/analyze.py`: archived wind component construction and hourly aggregation definitions.

## Station identity and measurement limitations

- **NWCL1:** NOAA CO-OPS 8761927, New Canal. The archive contains water, prediction, scalar hourly mean wind, direction, and vector components. Shoreline/structure exposure and an over-water sensor height history are not available in the archive. CO-OPS/NDBC NWCL1 rows may be re-reports of the same station; they are not combined as spatial replicates.
- **MDLL1:** USGS 301200090072400 station identity (Crossover 4) in the project's current five-station network. Its gage height is used only as a within-station native anomaly/change. Historical Mid-Lake/Causeway sensors are separate sources; no splice is made.
- **MAUL1:** USGS 07380215 stage (parameter 00065) in feet, native gage-height reference. Direct NAVD88 parameter 63160 is excluded.
- **DENL1:** USGS 07378500 discharge in cfs, native discharge reference. It does not represent all rainfall or tributary forcing.
- **MCHL1:** excluded from this diagnostic. The sensor/datum/duplicate-stream questions documented in PRs #58 and #59 remain unresolved.

The monthly archive's `coverage` field counts the source observations aggregated into each hourly row. Source cadence differs historically, so expected sub-hourly counts are estimated per month/station-variable from the mode of positive, nonmissing archived counts. An hourly bin below 80% of that modal count is marked unusable. Many rows do not retain provider QC flags or original receipt time. No statistical clipping is applied to finite stage/discharge values.

## Event chronology

Event and phase boundaries are fixed in `event_windows.json`. Alberto and Beryl named-storm chronology comes from the NHC/WPC records cited in merged PR #59's `sources.md`; those dates do not set local wind-onset dates. MAUL1 response onset, peak and recovery periods come from Phase 3B's response catalog. The June 27–July 1, 2024 pulse is explicitly unattributed and is not assigned to Beryl. The August 2016 event is left-censored in Phase 3B and has no verified forcing label here.

## Prospective archive adapter

`prospective-observation.schema.json` and `normalize_prospective_observation` specify a future timestamped archive interface. The required received time must be an actual collection timestamp; it is not backfilled from valid time. This package does not connect to or modify the live collector.
