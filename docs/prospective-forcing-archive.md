# Prospective coastal forcing observation archive — Phase A

**Research / Shadow Evaluation / Not Operational**

This is a research archive separate from published Phase 6 forecast and verification records. The collector runs hourly through free GitHub Actions, with an additional manual dispatch. It records actual retrievals only; this does not establish uninterrupted operation until scheduled runs, stored payloads, and health reports have accumulated and been inspected. No forecast or advisory is generated.

## Scope and priority

1. **NWCL1 (NOAA CO-OPS 8761927):** raw wind vectors (east/north components in knots), water level and *same-datum* astronomical prediction. Preserve raw source response and provider status separately.
2. **MDLL1:** native water-level changes, source/sensor metadata and receipt timestamps.
3. **DENL1:** native discharge and stage, distinguished from coastal forcing.
4. **MAUL1:** native parameter `00065` for stage-change analysis; direct `63160` NAVD88 only when actually reported. Never infer a historical conversion.
5. **KNEW ASOS (shadow wind context):** free current METAR through NOAA AWC. It is an airport land station, not a lake wind observation; station-specific sensor height is not verified. Wind is stored in knots with direction-from and vector components. Standard ASOS/METAR wind is a two-minute average. It is retained as shadow context only.
6. **MCHL1-USGS (shadow water level):** USGS 073802302 Pass Manchac native stage, separate from HADS MCHL1. Historical/near-current coverage is promising but feed duplication is documented and must be resolved before treating it as an independent predictor. Ground elevation metadata in NAVD88 is not the gage-height datum.
7. **Independent Mid-Lake wind station:** no currently reporting, free, authorized over-water feed has been verified. WeatherFlow Mid-Lake 2024 records have not been recovered; third-party access to another owner's Tempest station is restricted by its access policy.
8. **PR #58 candidate stations:** do not ingest display-only or stale observations. Current telemetry, provider identity, sensor lineage, datum and duplicate status must be verified first.

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

`.github/workflows/forcing-archive.yml` schedules hourly at minute 43, separate from Phase 6. It commits only `research/prospective-forcing-archive/`; its schedule does not consume forecast archives or rewrite issue times. NOAA observed products request `latest` hourly and its larger `recent` window at least daily. A failed recovery-window request is retried on later runs until one succeeds; repeated rows are deduplicated by station, variable, valid time, value and QC state. This limits repeated large raw responses while allowing recovery of missed runs and delayed updates within the provider window. Tide predictions use the current product response. USGS latest-continuous supplies the latest values at each run, so a prolonged USGS outage can leave an unrecoverable gap unless a later source backfill is explicitly designed. GitHub Actions is free for public repositories subject to GitHub service availability, usage limits, and scheduled-run delays. Its default repository branch storage is persistent Git storage, not a guaranteed database or immutable/WORM store: Git history preserves committed prior bytes, while repository administrators can still rewrite history. Runs are serialized, with retry/rebase on push conflicts.

The live smoke command retrieves and parses current NOAA AWC KNEW METAR, NOAA CO-OPS wind, observed water level and MLLW tide predictions, and USGS core/shadow series. It prints actual response code, collector receipt time, provider HTTP `Date`, valid-time age and source category. KNEW must report within two hours during smoke verification. MCHL1-USGS is optional and any empty/unavailable response remains explicit. Fixture tests are not proof of provider availability. On 2026-10-25, the hosted PR #60 smoke check verified NWCL1, DENL1, MDLL1 and MAUL1 endpoints (HTTP 200); the expansion branch's own hosted workflow must verify KNEW and MCHL1 before completion claims are made. Missing series are never synthesized.

Source endpoints and parameter contracts:

| Archive alias | Provider station | Current endpoint and parameter | Interpretation |
| --- | --- | --- | --- |
| NWCL1 | NOAA CO-OPS `8761927` | [CO-OPS Data API](https://api.tidesandcurrents.noaa.gov/api/prod/datagetter), products `wind`, `water_level`, `predictions` | Wind `s` and `d` fields; water level and predictions explicitly request `datum=MLLW`. The hosted smoke job checks each response by parsing source records. |
| DENL1 | USGS `USGS-07378500` | [Water Data OGC API latest-continuous](https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items), separate parameter requests `00060` and `00065` | Discharge and native gage height are distinct series; current response reports discharge in `ft^3/s`, retained in `provider_unit` and normalized to cfs without numerical conversion. |
| MDLL1 | USGS `USGS-301200090072400` | Same OGC API; parameter `00065` | Native gage height only. No conversion to another station datum. |
| MAUL1 | USGS `USGS-07380215` | Same OGC API; `00065` and `63160` queried separately | `00065` stays native gage height. `63160` is kept only when the exact direct series is returned and labeled NAVD88; an empty response is recorded as empty. |
| KNEW (shadow) | NOAA AWC METAR `KNEW` | [Aviation Weather Center Data API](https://aviationweather.gov/data/api/), `metar?ids=KNEW&format=json&hours=2` | Airport land wind context; knots, true-north direction-from and derived meteorological vector. `obsTime` is valid time; our retrieval time and HTTP `Date` are separate. `reportTime` is retained as provider report time, not asserted publication time. No station-specific anemometer height verified. |
| MCHL1-USGS (shadow) | USGS `USGS-073802302` | Same OGC API; `00065` | Pass Manchac native gage height. Ground-altitude NAVD88 metadata is not stage datum. USGS/HADS MCHL1 have matching overlapping values in prior research; this is a separate source feed, not an independent physical replicate. |

## Coastal network expansion inventory

The source triage below is for deciding what can enter prospective collection. A current display is not evidence of uninterrupted telemetry, and no datum conversion is applied to native stage.

| Candidate | Provider / status | Spatial or measurement value | Decision |
| --- | --- | --- | --- |
| NWCL1 / NDBC NWCL1 | NOAA CO-OPS 8761927; active in archive | Existing exposed station; CO-OPS and NDBC labels refer to the same site/feed family, so not an independent wind sensor | Keep current core source; do not duplicate NDBC |
| LKPL1 | NDBC historical western-lake station; anemometer reported at 13 m, 2004–2012 | Valuable over-water historical reference, but NDBC reports no data in its recent 45-day window | Historical-only; no prospective collector |
| FREL1 | CO-OPS 8762484 / NDBC; historical reports only (CO-OPS products end 2023-03-31; no recent NDBC reports through prior review) | Gulf connection exposure; presently stale | Do not collect as current |
| BCFL1 | CO-OPS 8762483 | Station activity not demonstrated | Unverified; exclude |
| WeatherFlow Mid-Lake / Tempest | Historical 2024 report not recovered; third-party station access requires authorization under provider policy | Best conceptual independent lake wind, but no free authorized endpoint demonstrated | Do not pursue archive until owner-authorized access exists |
| KNEW | NOAA AWC METAR, free; ASOS land/airport site | Independent regional wind context; no station-specific sensor height/exposure metadata verified; standard two-minute averaging | Collect as shadow; not an over-water replacement |
| WEGL1 | NWPS/USACE station 85625; prior review found last displayed observation Oct 12, 2026 | ~0.7 km from NWCL1; possible local redundancy. USACE datum lineage documented as NGVD29 before 2006-12-19 and NAVD88 (2004.65) thereafter | No collection until live telemetry and source metadata are checked; likely limited spatial gain |
| PLAL1 | NWPS candidate, no verified current observation in prior review | Lakefront Airport location could add eastern-lake water response | Exclude pending original provider, live timestamp and datum proof |
| LRLL1 | NWPS candidate near Lacombe; last located display Oct 13, 2026 | Potential north-shore response | Exclude pending live telemetry, sensor/provider and datum verification |
| RGTL1 / RFPL1 | NWPS candidates near Rigolets/US 90, ~0.7 km apart; owners/feed pairing unresolved | Potential Gulf-connection response, but apparent nearby IDs may be duplicate/co-located feeds | Exclude until paired values/source lineage and datum are verified |
| MCHL1-USGS | USGS 073802302, continuous stage series documented from May 2022; PR #58 found exact overlap with HADS MCHL1 in 852/852 paired points | Adds an alternative official source receipt for Pass Manchac; likely re-report of same physical measurement and affected by downstream backwater | Shadow archive only; not independent predictor evidence |
| Bayou Manchac at Alligator Bayou | USGS 07378746; last verified page observation in late September 2026 during prior review | Tributary connection plausible but current feed freshness not established; native stage is not discharge | Exclude pending fresh live series and hydrologic direction/lead evidence |
| NOAA CO-OPS/NDBC | NOAA public, free | APIs available, but reviewed active target candidates duplicate NWCL1 or lack current telemetry | Recheck only if candidate status changes |

The expansion smoke workflow is the first live API/parser validation for KNEW and MCHL1-USGS. The table's other stale/unverified NWPS candidates remain inventory findings rather than claimed live source checks on this branch. Source/provider status can change; health reports retain per-run response status and newest valid time so later outages and stale data remain visible.

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

