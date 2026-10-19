# MAUL1 Phase 3A — Historical Data Expansion and Validation

## Goal

Expand the current event-window archive into a reproducible, resumable 2016–2026 historical archive while preserving the Phase 2A/2B event datasets, datum safeguards, and research-only interpretation.

## Archive layout and acquisition

The existing `site/data/<event>.json.gz`, hourly event products, `analysis.json`, and `verification.json` remain immutable compatibility artifacts. New continuous data use deterministic monthly partitions:

```
site/data/history/
  manifest.json
  coverage.json
  wind-comparison.json
  discovery.json
  raw/<station>/<YYYY-MM>.json.gz
  hourly/<YYYY-MM>.json.gz
```

Each raw partition contains canonical observations plus source metadata and a half-open UTC interval `[month_start, next_month_start)`. Station-month records retain original timestamps, units, native datums, quality flags, source identifiers, request URL, retrieval status, row count, and errors. Existing observations are skipped when the deterministic partition already exists; `--refresh` is the only way to replace a partition. A failed or forbidden source produces a manifest status and does not create fabricated rows.

Source adapters use monthly requests: USGS NWIS IV for DENL1, MDLL1, and MAUL1; NOAA CO-OPS for NWCL1 water, prediction, and meteorology; HADS for MCHL1; NDBC historical NWCL1 attempts as a separate source; and USACE 85420/85420LA requests only where their documented response can be parsed. MCHL1, USACE-85420, and USACE-85420LA are never merged. USGS 00065 and 63160 remain separate; no historical gage-height-to-NAVD88 conversion is performed.

## Derived hourly archive and quality

Hourly partitions are derived only from observations inside each UTC hour. Empty hours remain present as missing records. Water levels use hourly medians, discharge and wind components use means, and wind directions are derived from component means rather than averaged angles. Trailing changes and vector statistics use exact available hourly predecessors, minimum coverage, and no future observations. Partition boundaries include the required antecedent context but emit only timestamps belonging to the target month.

Automated quality checks report duplicate timestamps, unit/datum changes, suspicious jumps, gaps, incomplete source responses, observation quality flags, and event-boundary truncation. Coverage reports include station/variable by year and month, expected versus observed counts, missing fractions, major outages, and retrieval status.

## Wind comparison

CO-OPS NWCL1 is primary. NDBC data, when reachable and station identity is confirmed, is normalized into a separate source series. Overlapping timestamps are compared after unit normalization, with circular direction differences and speed/gust disagreement summaries. The comparison never averages sources or backfills CO-OPS values automatically. HTTP 403, unavailable station identity, or no overlap is reported explicitly.

## Historical discovery

Discovery runs over the continuous hourly archive, using MAUL1-independent positive-rise episodes and independently detected DENL1, NWCL1 residual, MDLL1, and wind episodes. It emits descriptive candidates for river, coastal, compound, river-only nonresponse, coastal-only nonresponse, and quiet-control periods. Overlapping candidates are merged or linked by explicit episode groups; Sally/Beta remains dependent. NCEI/NWS/NHC context is optional metadata and never supplies event labels or causal classification.

The discovery artifact records episode IDs, source intervals, peak/onset metrics, station coverage, datum status, matching windows, nonresponse status, and uncertainty. It contains no forecast probabilities, causal claims, or automatic forcing classification.

## Workflows and delivery

`history.yml` accepts `start_month`, `end_month`, `refresh`, and `run_discovery` inputs. It processes one month at a time, skips existing successful partitions, reports failures, commits only changed history artifacts, and can be rerun for incomplete ranges. The validation workflow checks partition JSON, coverage consistency, source separation, deterministic regeneration, Python tests, JavaScript checks, and site smoke tests before Pages deployment.

The final report must distinguish completed months from failed/unavailable months and state actual station-variable coverage, wind comparison results, discovery counts, major gaps, unresolved datums, reference-event revisions, and remaining limitations. Complete coverage is never claimed solely because a workflow finished.
