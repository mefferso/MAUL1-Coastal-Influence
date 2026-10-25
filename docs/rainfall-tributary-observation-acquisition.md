# Local rainfall and tributary observation acquisition

**Research / Shadow Evaluation / Not Operational.** This work archives source observations and watershed rainfall aggregates for later analysis. It does not alter any forecast, Phase 6 record, or dashboard behavior and does not establish rainfall attribution or predictive skill.

## Implementation

The existing hourly observation archive now requests current USGS OGC latest-continuous observations for:

| Source | Parameters | Interpretation and limitations |
| --- | --- | --- |
| USGS 301828090363100 | `00045` | Point precipitation at Amite River at Maurepas. Provider units are retained and normalized only between inch/mm spellings. The API valid timestamp is retained; the collector does not infer the accumulation interval or treat the value as a rate. |
| USGS 07379960 Dawson Creek | `00045`, `00065` | Temporary point precipitation and native gage height. The page-listed 00065 record is long; no continuous 00060 discharge series was listed in the reviewed inventory. Stage is not converted to flow. |
| USGS 07378810 Bayou Fountain | `00045`, `00065` | Temporary point precipitation and native gage height. No 00060 series was listed in the reviewed inventory. |
| USGS 07378746 Bayou Manchac at Alligator Bayou | `00045`, `00065` | Temporary point precipitation and native gage height. Its position near the control structure and confluence makes stage susceptible to boundary/backwater effects; it is not assumed to measure upstream runoff. |

These additions are optional health feeds. An unavailable or empty candidate feed is recorded but does not fail the existing NOAA/USGS core archive. Raw USGS response bytes remain content-addressed, and each receipt records valid time, actual retrieval time, HTTP server date, provider station/parameter/time-series identity, provider units, qualifiers, approval status, and source modification metadata when supplied. Provider `00045` values with negative sentinels or timezone-naive timestamps are rejected; zero remains a valid dry reading. Revisions or changed QC produce new receipts. The current collector records only what the latest-continuous endpoint returns; it does not reconstruct missing periods.

### MRMS proof of concept

The isolated optional collector targets NOAA `MultiSensor_QPE_01H_Pass2` from the public MRMS endpoint and gets upstream basin polygons from USGS NLDI for MAUL1 (07380215) and DENL1 (07378500). The hosted check returned HTTP 200 for both NLDI sites. DENL1 is 99.9989% inside MAUL1; the approximately 0.038 km² mismatch is a small boundary sliver. The collector permits at most 0.1% of DENL1 outside MAUL1, clips DENL1 to MAUL1 before differencing, and records the raw overlap fraction. Larger mismatches withhold the incremental area. This tolerance is explicit and tested. For each eligible polygon it clips the grid to a small bounding box, uses cell-center inclusion and cos(latitude) area weights, reports valid-cell coverage, and writes a receipt only when coverage is at least 80%. It stores the two small NLDI geometries as immutable raw payloads and records geometry hashes. Full MRMS continental GRIB files are not committed; their SHA-256, byte count, product metadata and URL are retained with aggregate receipts.

The product contract is strictly checked as a one-hour `0–1` accumulation. Values are recorded in mm with UTC `valid_start` and `valid_end`; the interval end is the observation `valid_time`. The decoded grid must be regular latitude/longitude. Invalid or negative grid cells count as missing, never as zero. The boundary-cell method approximates partial watershed cells by their centers; the resulting coverage and method are explicit metadata. The optional Python dependencies live in `research/local-forcing-feasibility/mrms-requirements.txt` and are installed only for MRMS steps. MRMS acquisition errors write health data but do not block the existing archive persistence step.

The endpoint is current-product-only in this implementation. Historical archive availability and complete historical basin aggregates have not been established. A successful provider request would verify only that one current file and its geometry were readable at that retrieval. It would not establish uninterrupted coverage, provider first-publication time, or operational forecast usefulness. Actual valid-time-to-retrieval delay must be measured over prospective runs; the server `Date`, `Last-Modified`, and `ETag` are kept separately and are not treated as first availability.

## Source status and scientific interpretation

| Category | Status |
| --- | --- |
| Previously verified currently reporting | Existing DENL1, MDLL1, MAUL1 and NOAA CO-OPS NWCL1 endpoints were verified by the already merged archive workflow. |
| Verified currently reporting | Hosted PR live smoke on 2026-10-25 returned HTTP 200 and one parsable current observation for each added USGS parameter: site 301828090363100 `00045`; 07379960, 07378810 and 07378746 `00045` and `00065`. Each had valid time 15:00Z and was retrieved about 15:39Z. This is a point-in-time reachability check, not a continuity guarantee. |
| Historical but insufficiently complete for attribution | The three tributary gage-height series have page-listed multi-year records, but full retrieval, gap coverage, rating/control context and datums have not been established here. The temporary rainfall series are recent-window data, not reliable long-term rainfall archives. Site 301828090363100 lists a longer record, but direct historical completeness has not been audited. |
| Unresolved | NOAA MRMS historical completeness and first-publication latency remain unverified. The hosted smoke downloaded a current MRMS product body, but cfgrib reported the field unit as `unknown`; the decoder rejected the field rather than assigning a unit. A GRIB-unit metadata fallback is now tested on the updated branch, but it still requires hosted verification before any MRMS aggregate can be reported. |

Existing feasibility work reports 109 grouped outcome-defined rises (28 detected, 81 missed), but its archive contains none of these local candidate series. Therefore no candidate-to-event join, paired comparison, lead/lag statistic, rainfall/tributary contribution estimate, or incremental predictive result is available. The groups are not assumed to be independent physical events. Historical page coverage alone is not a usable issue-time record. No causal or predictive claim is made.

The new observations can test a limited question: whether local precipitation or tributary stage changes provide temporally available, physically distinct information after accounting descriptively for DENL1 discharge and the existing coastal context. MRMS basin-mean precipitation is an area estimate, not a point gauge; USGS 00045 is a point reported accumulation, not a basin mean. The incremental MRMS basin is also not a measurement of runoff volume: it is an area-average precipitation estimate for the difference polygon. Tributary 00065 stage can respond to runoff, backwater, structures, and local controls; it is not discharge. No absolute stages are compared across gages or datum systems.

## Checks and next use

Deterministic tests cover optional source registration, parameter/sensor-aware receipt deduplication, units, qualifiers, rejected precipitation sentinels, interval semantics, no inferred rate, native stage datum, MRMS accumulation interval, grid spacing and geometry, missing-cell coverage, area weighting, incremental basin arithmetic, and receipt validation. The PR workflow runs these tests plus live endpoint checks for the added USGS sources and MRMS/NLDI. Hosted smoke results are the evidence for present reachability; local shell network failures are not substituted for source status.

Before exploratory event analysis, audit actual receipt continuity and latency, retrieve date-bounded historic rows where available with gap/QC summaries, and independently confirm catchment/routing interpretations. Compare event blocks and nonresponse controls while preserving missingness and source availability. Do not train a model or call any gain independent from reused retrospective data on the basis of this archive alone.

## Sources

- [USGS Water Data OGC latest-continuous API](https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items)
- [USGS NLDI basin API documentation](https://api.water.usgs.gov/docs/nldi/basin/)
- [NOAA MRMS product guide](https://vlab.noaa.gov/web/wdtd/-/multi-sensor-qpe)
- [NOAA MRMS operational product tables](https://www.nssl.noaa.gov/projects/mrms/operational/tables.php)
- [Public MRMS product endpoint](https://mrms.ncep.noaa.gov/2D/MultiSensor_QPE_01H_Pass2/)
