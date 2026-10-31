# Forcing archive recovery and completeness design

**Status:** Research / Shadow Evaluation / Not Operational

## Intent

Recover provider-observed values that fell between sparse collector runs, and make source coverage and actual observation-to-retrieval latency visible. Keep observation valid times, acquisition times, source metadata, datum rules, QC, and revisions intact. Do not amend earlier receipts or any archived Phase 6 forecasts.

## Goals and constraints

- Replace current-only acquisition for NOAA CO-OPS NWCL1 wind and MLLW water level, and USGS continuous readings at DENL1, MDLL1, and MAUL1 (00065 and direct 63160), with provider time-range queries that can return intermediate values.
- Apply the same range recovery to optional tributary and precipitation feeds while retaining each provider’s own accumulation semantics and QC.
- Store the exact response bytes content-addressed. Record SHA-256, request URL, HTTP/server metadata, actual local `retrieved_at`, provider `valid_time`, QC, and revisions. Tag records acquired from missing historical intervals as delayed recovery.
- Evaluate feature availability at archived issue times using only receipts whose actual retrieval time is no later than the issue time.
- Keep direct datum constraints: NWCL1 levels and predictions remain MLLW; MAUL1 63160 remains a distinct directly reported NAVD88 series; never convert 00065 into 63160.
- Keep all work in shadow evaluation. Do not modify model artifacts, forecast issuance, verification, or immutable prior receipts.
- Preserve bounded requests, pagination, deduplication, append-only receipts, safe main publication, and useful archive-growth and Actions summaries.
- Do not enable MRMS collection. Its NOAA operational product table identifies `MultiSensor_QPE_01H_Pass2` as local GRIB2 parameter 209/6/37, a 60-minute accumulation in mm with two-hour latency, but the captured prototype payload decoded as unknown units/parameter and `instant`. Keep it withheld until message sections, interval timestamps, and basin aggregation are verified against the definition.

## Approaches considered

1. **Bounded recovery in the existing collector (selected).** Query the last known observation through the current time using NOAA begin/end dates and the USGS `continuous` OGC collection. Use the earliest receipt on first recovery, then an overlapping watermark to capture new points and revisions. This repairs missed intervals at the next collector run and avoids a second scheduled workflow. It returns more data per existing source request and requires explicit response limits and pagination.
2. **Separate daily recovery workflow.** Keep the hourly collector small and run a second scheduled process. This separates the larger responses but adds a schedule vulnerable to the same missing-trigger problem, another publisher, and more race/resource paths.
3. **Manual or external hosted recovery.** This would avoid recurring archive requests but would not automatically repair a future Actions gap and would add operational dependencies.

## Chosen behavior

Use the existing archive workflow and its source list. NOAA date ranges are capped to the documented 31-day limit and split into smaller requests where needed. USGS history uses `collections/continuous/items` with the provider time interval filter, follows pagination links, and preserves the raw page responses. Use a one-hour overlap for revision discovery; deduplicate identical receipts while retaining changed value, approval status, QC, or provider modification metadata as a separate receipt. The first run recovers only the period already represented by the prospective archive, not the station’s full period of record.

Each record keeps source valid time and the actual acquisition time. The newest readings inside a source’s declared freshness window are marked prospective; older values returned by a recovery window are marked delayed recovery. This classification does not claim when the provider first published a value. Availability audits use `retrieved_at <= issue_time` and `valid_time <= issue_time`; late-acquired values are never counted as available at an earlier forecast issue.

## Completeness and operations

Add a deterministic report for unique valid timestamps, cadence, gaps, retrieval latency, repeated values, revisions, recovery class, and observation availability at Phase 6 issue times. Run it in the Actions summary without committing generated reports or triggering a site build. Add a fixture test with a six-hour interval between collector invocations. Keep the main archive publisher on the tested rebase helper and exclude archive-only pushes from the Pages workflow. Measure current archive growth and report post-change fixture counts separately from live production coverage.

## MRMS disposition

Document NOAA’s GRIB2 product-table identity, unit, accumulation period, and latency beside the captured decoder discrepancy. Document the NLDI basin source as upstream NHDPlusV2 catchments associated with each gage COMID, including geometry hashes and derived overlap/difference steps. Leave the source out of scheduled acquisition and keep the existing optional smoke nonblocking until product metadata and timestamps pass scientific checks.
