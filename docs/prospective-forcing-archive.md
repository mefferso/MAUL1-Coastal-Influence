# Prospective coastal forcing observation archive — Phase A

**Research / Shadow Evaluation / Not Operational**

This is a research archive separate from published Phase 6 forecast and verification records. The collector runs hourly through free GitHub Actions, with an additional manual dispatch. It records actual retrievals only; this does not establish uninterrupted operation until scheduled runs, stored payloads, and health reports have accumulated and been inspected. No forecast or advisory is generated.

## Scope and priority

1. **NWCL1 (NOAA CO-OPS 8761927):** raw wind vectors (east/north components in knots), water level and *same-datum* astronomical prediction. Preserve raw source response and provider status separately.
2. **MDLL1:** native water-level changes, source/sensor metadata and receipt timestamps.
3. **DENL1:** native discharge and stage, distinguished from coastal forcing.
4. **MAUL1:** native parameter `00065` for stage-change analysis; direct `63160` NAVD88 only when actually reported. Never infer a historical conversion.
5. **Independent Mid-Lake wind station:** add only after verifying a currently accessible raw data endpoint, sensor identity, height, averaging cadence, and historical continuity. WeatherFlow Mid-Lake 2024 records have not been recovered.
6. **PR #58 candidate stations:** add only after checking genuine current reporting, source ownership, datum, duplicate feeds, historical gaps, and API reliability.

Do not use FREL1 as a current observation source without evidence. MCHL1 remains shadow-only.

## Receipt schema (`forcing-1`)

Each newline in a dated JSONL batch is an independent **provider receipt**, not a model-ready hourly aggregate. Required fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Exactly `forcing-1` |
| `station_id`, `source`, `raw_id` | Station, upstream provider/feed identity, and original observation key |
| `variable`, `unit`, `datum` | Typed measurement; use `not_applicable` for wind/discharge, `unspecified` for uncertain water datum |
| `valid_time` | Actual observation/forecast valid time, UTC ISO8601 |
| `retrieved_at` | Actual provider retrieval time, UTC ISO8601 — never reconstructed from valid time |
| `value` | Finite numeric reading, or null if missing/rejected |
| `status`, `qc_flags` | Provisional/observed/predicted/missing/rejected and explicit QC annotations |

NOAA wind records include speed and direction as well as east/north vector components. CO-OPS direction is the direction the wind is from; the code uses `u=-speed*sin(direction)` and `v=-speed*cos(direction)`. CO-OPS observed water levels and predictions explicitly request MLLW. Predictions are `record_type=prediction`, `status=predicted`; future valid times are permitted only in that class. They are never treated as observations.

USGS OGC latest-continuous responses are preserved as received. `00060` is discharge, `00065` is station-native gage height, and `63160` is NAVD88 elevation only when that exact direct parameter is returned. The collector does not derive discharge from stage or convert a native gage datum. It preserves provider units, quality qualifiers, approval information, the server HTTP `Date` header, and available source modification metadata. An HTTP `Date` is not a publication timestamp.

Raw response bytes are SHA-256 addressed under `raw/`; receipt lines are append-only in UTC-day files. Exact repeated station-variable-valid-time-value-QC observations are skipped. A changed reported value or QC state is retained as a new receipt with its own actual `retrieved_at`. Every run writes a `health/` JSON report with per-feed status, response code, attempts, record counts, valid-time coverage, and QC flag counts. Critical feed failure or empty responses cause the collection command to exit unsuccessfully after writing health. GitHub Actions persists that report and the raw/receipt evidence before marking the run failed.

## Automated operation and limits

`.github/workflows/forcing-archive.yml` schedules hourly at minute 43, separate from Phase 6. It commits only `research/prospective-forcing-archive/`; its schedule does not consume forecast archives or rewrite issue times. GitHub Actions is free for public repositories subject to GitHub service availability, usage limits, and scheduled-run delays. Its default repository branch storage is persistent Git storage, not a guaranteed database or immutable/WORM store: Git history preserves committed prior bytes, while repository administrators can still rewrite history. Runs are serialized only by scheduler cadence, and concurrent workflow pushes may need retry/reconciliation if GitHub rejects a push.

The live smoke command retrieves and parses current NOAA wind, NOAA water level, MLLW tide predictions, and the requested USGS series, then prints real HTTP status, collector receipt time, and provider HTTP `Date`. Fixture tests are not proof of provider availability. Interactive-shell requests were blocked by the outbound proxy (403 CONNECT), but the hosted PR Actions smoke check succeeded on 2026-10-25: NOAA returned parseable wind, MLLW water-level and prediction records; USGS returned parseable DENL1 `00060`/`00065`, MDLL1 `00065`, and MAUL1 `00065`/`63160` records (HTTP 200). This verifies current endpoint reachability and parser compatibility for that run, not continuous uptime or scheduled persistence. Missing `63160` is still represented as empty if a later response lacks it; no value is synthesized.

Source endpoints and parameter contracts:

| Archive alias | Provider station | Current endpoint and parameter | Interpretation |
| --- | --- | --- | --- |
| NWCL1 | NOAA CO-OPS `8761927` | [CO-OPS Data API](https://api.tidesandcurrents.noaa.gov/api/prod/datagetter), products `wind`, `water_level`, `predictions` | Wind `s` and `d` fields; water level and predictions explicitly request `datum=MLLW`. The hosted smoke job checks each response by parsing source records. |
| DENL1 | USGS `USGS-07378500` | [Water Data OGC API latest-continuous](https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items), separate parameter requests `00060` and `00065` | Discharge and native gage height are distinct series; current response reports discharge in `ft^3/s`, retained in `provider_unit` and normalized to cfs without numerical conversion. |
| MDLL1 | USGS `USGS-301200090072400` | Same OGC API; parameter `00065` | Native gage height only. No conversion to another station datum. |
| MAUL1 | USGS `USGS-07380215` | Same OGC API; `00065` and `63160` queried separately | `00065` stays native gage height. `63160` is kept only when the exact direct series is returned and labeled NAVD88; an empty response is recorded as empty. |

USGS `approval_status`, `qualifier`, `time_series_id`, `unit_of_measure`, `last_modified`, feature geometry and the original feature payload are retained as QC/provenance. In observed DENL1 responses the OGC `unit_of_measure` literal is `ft^3/s`; the collector preserves that literal alongside normalized `cfs`. `last_modified` is a provider field, not assumed to be first-publication time. Per-source `newest_valid_age_seconds` is the observed valid-time age at our actual retrieval and is not a measurement of provider release latency.

Provider times (`valid_time`), collector times (`retrieved_at`), HTTP server `Date`, and any source-provided modification field are stored as different fields. None of these reconstructs when an observation first became publicly available. Backfilled historical source records must not be merged into the prospective receipt archive.

**Important:** a `retrieved_at` timestamp proves only when *our collector saw the value*, not when it first became available. A provider publication timestamp, if reported, is additional evidence; don't fabricate it. For historical datasets without real receipts, use an explicitly different historical archive namespace and never populate `retrieved_at` with guessed dates.

## Validation

```bash
python -m unittest tests.test_forcing_archive -v
python scripts/validate_forcing_archive.py path/to/actual-observations.jsonl
```

No fictitious observation records are committed. Validation rejects missing provenance, improper units, unzoned dates, duplicate receipt keys within a batch, invalid values, and receipt times before valid times. Source-specific collector code must additionally enforce provider-specific QC and sensor/datum lineage; this validator does not certify physical validity.

## Data contract and operations review

- The collector only queries current NOAA products and USGS latest-continuous data; it does not backfill source observations or assert historical receipt time.
- The archive is research-only and must remain disjoint from Phase 6 model inputs until prospective receipt coverage and QC have been reviewed.
- For production-grade durability beyond free GitHub storage, a later decision would need a separate public immutable archive. No paid or external cloud storage is configured here.
- Before model experimentation, inspect scheduled health reports for missing runs, latency, source metadata and datum lineage, and compare only observations actually received by each issuance time.
- Wind vector conventions, sensor metadata, NOAA MLLW datum availability, and USGS OGC field names must be verified against successful live source payloads before treating records as physically validated.

Never modify frozen Phase 6 forecast artifacts or genuine issuance/verification logs. No operational thresholds or advisory recommendations.

