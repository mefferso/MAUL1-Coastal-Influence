# Coastal wind and hydrologic response diagnostics

**Status:** Historical research / shadow diagnostics / not operational.

This package builds reusable wind and water-response descriptors from the committed Phase 3A hourly archive and evaluates five fixed cases: Alberto 2024, the separated Beryl 2024 chronology, May 2021, the August 2016 high-water response, and a Phase 3B quiet-low-variation control candidate from July 2021.

It does not fetch live data, modify the Agent 1 collector, change dashboards, or fit/retrain forecasting models. It does not use the prospective forecast archive. The historical archive has valid-time hourly labels but no original receipt timestamps, so the diagnostics cannot assert that any value was available at a past forecast issuance time.

## Reproduce

From the repository root:

```bash
python -m unittest discover -s research/coastal-response-diagnostics/tests -v
python research/coastal-response-diagnostics/run_diagnostics.py
```

To write outputs elsewhere:

```bash
python research/coastal-response-diagnostics/run_diagnostics.py --output-dir /tmp/coastal-response-run
```

The script reads the six event-period monthly source files it needs and records their SHA-256 hashes in `diagnostics.json`. Outputs are:

- `diagnostics.json`: event and phase summaries, coverage, observed timing offsets, and predeclared lag profiles.
- `phase_summary.csv` and `lag_profiles.csv`: flattened tables for independent inspection.
- `figures/*.svg`: event timelines showing wind speed/direction, 24/72-hour directional stress proxies, within-station lake anomalies, MAUL1 native-stage tendencies, and DENL1 discharge tendencies.

Feature definitions, QC, averaging limitations and event rules are in [methods.md](methods.md). The interpretation and shortlist for future challenger research are in [findings.md](findings.md). The prospective archive interface is specified in [prospective-observation.schema.json](prospective-observation.schema.json).
