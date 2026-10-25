# Directional wind forcing and hydrologic memory

**Research / Shadow Evaluation / Not Operational.** This package is isolated from the forecast pipeline, Phase 6 records, verification archives, and dashboard.

## Reproduction

From the repository root:

```sh
python research/directional-wind-memory/analyze_wind_memory.py
python research/directional-wind-memory/event_periods.py
python -m unittest discover -s research/directional-wind-memory -v
```

The script reads only committed `site/data/history/hourly/*.json.gz` records and the rise-failure audit/control tables, and writes a JSON cohort summary and SVG figure. It does not fit a model. Windows, event definitions, 80% coverage, thresholds, issue-time cutoff, and directional conventions are fixed in the script.

## Contents

- `report.md`: findings, feature audit, case and failure analysis, interpretations, data limitations, and recommendations.
- `analyze_wind_memory.py`: reproducible issue-time descriptor calculations.
- `event_periods.py`: fixed Alberto/transition/Beryl chronology and same-station historical context diagnostics.
- `test_analyze_wind_memory.py`: cutoff, missingness/run, and low coverage tests.
- `test_event_periods.py`: event-window separation and same-station change tests.
- `presentation_claims.json`: structured transcription of the presentation's annotated event claims and visible metadata.
- `test_presentation_claims.py`: arithmetic checks for the stated wind/duration and delay claims.
- `wind_memory_summary.json`: generated episode descriptor cohort summaries.
- `event_period_diagnostics.json`: generated fixed-window metrics and source/datum notes.
- `wind_memory_groups.svg`: cohort median and IQR figure.
- `sources.md`: repository and public source provenance.

## Interpretation boundary

Wind vector observations come from NWCL1 only. The archive lacks wind-height/exposure history, provider QC qualifiers, and receipt timestamps. Thus the `U|V|` statistic is explicitly a directional stress **proxy**, not stress in physical units; a retrospective valid timestamp does not prove it was available to an operational forecast. The existing holdout is reused and is not independent validation. No forecast-skill claim is made.
