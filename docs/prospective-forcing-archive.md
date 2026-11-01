# Prospective coastal forcing observation archive — Phase A

**Research / Shadow Evaluation / Not Operational**

This is a research archive separate from published Phase 6 forecast and verification records. The collector is scheduled hourly through free GitHub Actions, with an additional manual dispatch. The Oct 25–31, 2026 audit found 69 workflow runs: 29 schedule runs (all completed successfully), 2 dispatches (both successful), and 38 pull-request runs (17 successful, 12 failed, 9 cancelled). There were no skipped workflow-run conclusions. Across 144 nominal hourly slots in the inspected schedule window, only 29 schedule run records appeared; 115 slots had no corresponding run record. All 29 scheduled runs started at their run creation timestamp and completed successfully in roughly 20–60 seconds; the records do not include an intended scheduled-for time, so the evidence cannot distinguish dropped triggers from late creation or assign a GitHub platform cause. This archive records actual retrievals only and does not establish uninterrupted operation. No forecast or advisory is generated.

## Scope and priority

1. **NWCL1 (NOAA CO-OPS 8761927):** raw wind vectors (east/north components in knots), water level and *same-datum* astronomical prediction. Preserve raw source response and provider status separately.
2. **MDLL1:** native water-level changes, source/sensor metadata and receipt timestamps.
3. **DENL1:** native discharge and stage, distinguished from coastal forcing.
4. **MAUL1:** native parameter `00065` for stage-change analysis; direct `63160` NAVD88 only when actually reported. Never infer a historical conversion.
5. **KNEW ASOS (shadow wind context):** free current METAR through NOAA AWC. It is an airport land station, not a lake wind observation; station-specific sensor height is not verified. Wind is stored in knots with direction-from and vector components. Standard ASOS/METAR wind is a two-minute average. It is retained as shadow context only.
6. **MCHL1-USGS (shadow water level):** USGS 073802302 Pass Manchac native stage, separate from HADS MCHL1. Historical/near-current coverage is promising but feed duplication is documented and must be resolved before treating it as an independent predictor. Ground elevation metadata in NAVD88 is not the gage-height datum.
7. **Local rain and tributary context (shadow):** USGS `00045` at 301828090363100, 07379960, 07378810 and 07378746; `00065` at the three tributary sites. Preserve reported precipitation accumulation without inferring a rate or accumulation interval. Treat `00065` as native stage, never discharge. Bayou Manchac can be affected by downstream controls/backwater. These optional feeds are captured by the same hourly collector.
8. **MRMS:** a limited basin-aggregation prototype is isolated from scheduled collection. The current GRIB metadata did not validate variable, units or accumulation semantics, so it produces no receipts.
9. **SHBL1 (Shell Beach):** not onboarded; no current, reliable, freely accessible observation feed has been verified for this integration. It can be reconsidered only after an identified operator/source and live timestamp are confirmed.
10. **Other speculative open-water stations:** not pursued in this integration. No currently reporting, free, authorized independent over-water wind feed has been verified.

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

USGS OGC `continuous` responses are requested over explicit `time` intervals and all advertised `next` pages are retained as received. `00060` is discharge, `00065` is station-native gage height, and `63160` is NAVD88 elevation only when that exact direct parameter is returned. The collector does not derive discharge from stage or convert a native gage datum. It preserves provider units, quality qualifiers, approval information, the server HTTP `Date` header, and available source modification metadata. An HTTP `Date` is not a publication timestamp.

Raw response bytes are SHA-256 addressed under `raw/`; receipt lines are append-only in UTC-day files. Exact repeated station-variable-valid-time-value/QC/status/datum/series observations are skipped. A changed reported value, approval status, provider modification, or QC state is retained as a new receipt. `acquisition_mode` marks newly acquired current observations `prospective` and older readings discovered in range queries `delayed_recovery`; both retain actual `retrieved_at`, and this label does not claim provider first-publication time. Health reports link each request URL and raw response digest/path. Critical feed failure or empty responses cause the collection command to exit unsuccessfully after writing health. GitHub Actions persists that report and the raw/receipt evidence before marking the run failed.

## Automated operation and limits

`.github/workflows/forcing-archive.yml` schedules hourly at minute 43, separate from Phase 6. It commits only `research/prospective-forcing-archive/`; archive-only pushes are ignored by the Pages workflow. NOAA observed products query `begin_date`/`end_date` windows no longer than 31 days, bootstrapping from the earliest existing receipt and then overlapping the latest successful valid time by one hour. USGS OGC `continuous` queries use a `time` interval and follow pagination links, including for DENL1, MDLL1, MAUL1 `00065` and direct `63160`, plus optional tributary/rain series. These range queries capture provider observations between collector invocations; they do not assert that those observations were received or known at an earlier issue time. Predictions remain a separate current request. GitHub Actions is free for public repositories subject to service availability, usage limits, and scheduled-run delays. The archive completeness report runs in the Actions summary and is not committed as a generated blob. The tested publisher helper retries fetch/rebase/push and safely aborts on conflicts. Receipt deduplication scans the append-only JSONL receipt files, so per-run work grows linearly with archive size; measured local archive size is 3.5 MiB of which raw bytes are 0.84 MiB and receipts 1.0 MiB, while recent repository growth includes much larger existing data/model artifacts. Git history is not WORM storage.

### Automated health and scientific-readiness reports

`.github/workflows/archive-monitoring.yml` writes a daily archive-health report and a weekly scientific-readiness report beneath [`research/prospective-forcing-archive/monitoring/`](../research/prospective-forcing-archive/monitoring/). Each report is available as JSON and Markdown and is also written to the Actions job summary. The monitor reads the Actions workflow-run API using the workflow token's `actions: read` permission; it compares scheduled run records with nominal hourly slots but cannot map a run to an exact intended slot because GitHub run records do not expose a scheduled-for timestamp. The monitor does not change receipt files.

Cadence checks use NOAA CO-OPS six-minute observations for NWCL1 wind and water levels, hourly routine METAR reports for KNEW, and a **provisional 15-minute criterion** for USGS continuous series until station-specific sample-interval metadata is archived. USGS and local rainfall/tributary criteria are labeled provisional where that metadata is not available. A predictor window requires paired, finite observations at 80% or more of expected timestamps, no gap greater than three expected intervals, and a latest observation within that same three-interval freshness limit; an overall feature is called sufficient only when at least 80% of authentic issue windows pass. These are provisional research criteria. Values count as available at an authentic Phase 6 issue only if both `valid_time` and actual `retrieved_at` are no later than the issue time. Large gaps are not interpolated.

Weekly context summaries assess NWCL1 MLLW residuals only at exact observation/prediction valid-time matches, plus MDLL1 stage, DENL1 discharge/stage, MAUL1 native stage and direct NAVD88 values, KNEW wind, MCHL1 stage, and available rainfall/tributary series. The monitor does not convert datums or calculate absolute gradients between stations. Forecast target counts deduplicate model/revision rows by issuance and target. MAUL1 significant rises are grouped across overlapping windows using native USGS `00065` only, and count only when the episode includes a matured Phase 6 prospective verification target. Three distinct grouped episodes is a provisional candidate-for-review criterion, not a statistically justified sample-size threshold; event independence still needs scientific review, and the count does not establish model validation. The weekly report identifies remaining blockers and a next action while preserving Research / Shadow Evaluation / Not Operational status.

The monitoring workflow has no push trigger, publishes only changed dated report files, uses the existing rebase-safe publisher, and does not trigger Pages because the Pages workflow ignores the full prospective archive path. A monitoring API failure is shown as insufficient schedule evidence, not as proof that no collection ran.

The current-main Oct 25–31 baseline held 985 receipt rows across 24 source-variable series. NWCL1 wind and MLLW level each had 31 unique observed times (median gap 5h24m, maximum gap 7h30m); USGS current-only series had 30–31 unique times with maximum gaps of 7h15m–8h. NOAA median observed-to-retrieval latency was about 7.8 minutes; USGS medians were about 28–42 minutes. All 31 health reports reported zero critical failures, but successful current requests returned only the latest provider observation and did not fill intermediate intervals. The six-hour outage fixture begins with one archived valid time and ends with seven (the six intermediate hourly readings retained), moving fixture timestamp coverage from 1/7 to 7/7; the six newly acquired rows carry the injected post-outage retrieval time. This is a regression fixture, not live production recovery. A live before/after coverage claim remains pending the next provider-backed collector run. At inspection the local working tree measured 278.13 MiB, Git pack 243.38 MiB, and the growth utility found 19.72 MiB of new unique data blobs over the prior seven days; its history-based linear planning projection is +515.66 MiB in six months and +1.00 GiB in a year, including historical-backfill activity. The prospective archive itself was about 3.5 MiB. These are repository planning measures, not an attribution of that growth to this collector.

The live smoke command retrieves NOAA AWC KNEW METAR, NOAA CO-OPS wind, observed water level and MLLW tide predictions, and every configured USGS core/shadow series, including MCHL1 and the local rain/tributary candidates. It prints actual response code, collector receipt time, provider HTTP `Date`, valid-time age and source category. KNEW is assessed against a two-hour freshness window. Optional-source errors and empty results are reported but do not stop core checks; required NWCL1/DENL1/MDLL1/MAUL1 failures do fail the smoke. Fixture tests are not proof of provider availability. On the coastal expansion hosted run at 2026-10-25 15:29 UTC, KNEW returned 8 reports (newest `obsTime` 14:53Z; age 36 minutes), MCHL1-USGS returned `00065` at 14:45Z, and the four core station families passed. The combined hosted run on 2026-10-25 verified NWCL1 CO-OPS wind, observed water level and tide predictions (HTTP 200); KNEW returned 8 reports with newest valid time 15:53Z; DENL1 `00060`/`00065`, MDLL1 `00065`, and MAUL1 `00065`/`63160` returned current USGS records (newest 15:15Z or 16:00Z); MCHL1-USGS `00065` returned at 15:45Z; local rain `00045` at site 301828090363100 and at Dawson Creek, Bayou Fountain and Bayou Manchac, plus tributary native stages `00065` at the three creeks, each returned at 16:00Z. The MRMS endpoint was reachable (HTTP 200) but its downloaded GRIB decoded with unknown precipitation units/field and `stepType=instant`; it yielded zero receipts and the optional smoke step failed as expected. Keep MRMS disabled from scheduled collection. These are point-in-time checks, not continuity evidence. Missing series are never synthesized.

Source endpoints and parameter contracts:

| Archive alias | Provider station | Current endpoint and parameter | Interpretation |
| --- | --- | --- | --- |
| NWCL1 | NOAA CO-OPS `8761927` | [CO-OPS Data API](https://api.tidesandcurrents.noaa.gov/api/prod/datagetter), products `wind`, `water_level`, `predictions` | Wind `s` and `d` fields; water level and predictions explicitly request `datum=MLLW`. The hosted smoke job checks each response by parsing source records. |
| DENL1 | USGS `USGS-07378500` | [Water Data OGC API continuous collection](https://api.waterdata.usgs.gov/ogcapi/v0/collections/continuous/items), separate parameter requests `00060` and `00065` with OGC `time` intervals | Discharge and native gage height are distinct series; provider discharge unit is retained in `provider_unit` and normalized to cfs without numerical conversion. |
| MDLL1 | USGS `USGS-301200090072400` | Same continuous collection; parameter `00065` with `time` interval | Native gage height only. No conversion to another station datum. |
| MAUL1 | USGS `USGS-07380215` | Same continuous collection; `00065` and direct `63160` queried separately with `time` intervals | `00065` stays native gage height. `63160` is kept only when the exact direct series is returned and labeled NAVD88; an empty response is recorded as empty. |
| KNEW (shadow) | NOAA AWC METAR `KNEW`, provider-reported coordinates 30.0494, -90.0290, elevation 1 m (live response 2026-10-25) | [Aviation Weather Center Data API](https://aviationweather.gov/data/api/), `metar?ids=KNEW&format=json&hours=2` | Airport land wind context; knots, true-north direction-from and derived meteorological vector. Standard ASOS/METAR wind uses a two-minute average. `obsTime` is valid time; our retrieval time and HTTP `Date` are separate. `reportTime` is retained as provider report time, not asserted publication time. Sensor mounting height remains unverified. |
| MCHL1-USGS (shadow) | USGS `USGS-073802302` | Same OGC API; `00065` | Pass Manchac native gage height. Ground-altitude NAVD88 metadata is not stage datum. USGS/HADS MCHL1 have matching overlapping values in prior research; this is a separate source feed, not an independent physical replicate. |
| USGS local precipitation | USGS `USGS-301828090363100`, `USGS-07379960`, `USGS-07378810`, `USGS-07378746` | Same OGC API; parameter `00045` | Point accumulated precipitation; preserve provider unit, valid time, QC and interval only when supplied. Do not infer interval/rate. Optional shadow feeds. |
| USGS tributary context | USGS `USGS-07379960`, `USGS-07378810`, `USGS-07378746` | Same OGC API; parameter `00065` | Native site gage height in feet; no rating-based discharge conversion or cross-station datum subtraction. Optional shadow feeds. |

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

- The collector queries bounded NOAA date ranges and USGS OGC continuous timestamp ranges to recover observations from missed collection intervals; it retains actual retrieval time and never asserts historical receipt time or provider first availability.
- The archive is research-only and must remain disjoint from Phase 6 model inputs until prospective receipt coverage and QC have been reviewed.
- For production-grade durability beyond free GitHub storage, a later decision would need a separate public immutable archive. No paid or external cloud storage is configured here.
- Before model experimentation, inspect scheduled health reports for missing runs, latency, source metadata and datum lineage, and compare only observations actually received by each issuance time.
- Wind vector conventions, sensor metadata, NOAA MLLW datum availability, and USGS OGC field names must be verified against successful live source payloads before treating records as physically validated.

Provider references: [NOAA CO-OPS Data API](https://api.tidesandcurrents.noaa.gov/api/dev), [CO-OPS web services limits](https://tidesandcurrents.noaa.gov/web_services_info.html), [USGS OGC API](https://api.waterdata.usgs.gov/ogcapi/v0/?f=html), and the [USGS continuous collection](https://api.waterdata.usgs.gov/ogcapi/v0/collections/continuous/items). The NOAA range requests use the documented `begin_date` and `end_date` query parameters; USGS history requests use the advertised RFC3339 `time` interval and pagination links.

Never modify frozen Phase 6 forecast artifacts or genuine issuance/verification logs. No operational thresholds or advisory recommendations.

