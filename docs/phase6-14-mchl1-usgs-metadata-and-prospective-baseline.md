# MCHL1 / USGS 073802302 metadata and early prospective baseline (2026-10-23)

**Research-only status: keep MCHL1 shadow-only.** This note captures authoritative metadata and an early, non-independent-in-time forecast verification snapshot. It makes no changes to model coefficients, QC gates, or archives.

## Source identity and datum: what is actually known

- NWS HADS lists **MCHL1**, DCP **CE678A12**, as **PASS MANCHAC NEAR HWY 51**, operator code **CEMVN1**, HG variable, nominal 15-minute observation interval, at 30°17′00″ N, 90°23′46″ W. See https://hads.ncep.noaa.gov/hsas/LIX_dcps.shtml . HADS does **not**, on that page, certify datum or sensor identity relative to USGS.
- USGS station **073802302**, **Pass Manchac nr. Lake Maurepas, LA**, lists 30°17′00.84″ N, 90°23′52.22″ W and **datum of gage −0.18 ft NAVD88**, based on USGS site inventory/monitoring location metadata. See https://waterdata.usgs.gov/nwis/inventory/?agency_cd=USGS&site_no=073802302 and https://waterdata.usgs.gov/monitoring-location/USGS-073802302 . This is metadata for the **USGS site only**; do not apply −0.18 ft to MCHL1.
- The published HADS and USGS coordinates differ by roughly six arcseconds longitude. This is consistent with nearby facilities but **does not establish common instrumentation**. HADS describes CEMVN1 and USGS lists maintenance by the Louisiana Water Science Center, in cooperation with Pontchartrain Levee District. Provider/operator labels may reflect data relay or separate responsibilities; confirmation from the actual operators is required.
- PR #37's September 1–5, 2026, exact-UTC overlap experiment reported 365 exact timestamp matches and 0.000 ft differences at matched times, including available 6/24/72-hour deltas. These are *reported probe results*; consult archived workflow artifact `mchl1-usgs-overlap` on run 39850169916 before asserting independently reproduced numeric agreement. Matching data could be one shared upstream measurement stream, not two independent gauges.

**Open gates:** instrument/DCP mapping, original sensor and telemetry identity, MCHL1 physical reference datum, gauge-zero changes and survey history, SHEF quality flags, USGS qualification/revision semantics, record continuity, and reporting latency. USACE 85420/85420LA are not proxies.

## Genuine prospective scorecard snapshot

Source: committed `site/data/prospective/performance.json` at commit `a8da6c9291324ad88585cd8ce00339af50c37b14`, read October 23, 2026.

| Horizon | Verified forecasts per model | Persistence MAE (ft) | MAUL1-only MAE (ft) | Phase 5A coastal MAE (ft) | Phase 5B coastal-tidal MAE (ft) | Phase 5B full MAE (ft) |
|---|---:|---:|---:|---:|---:|---:|
| 6h | 12 | 0.0275 | 0.0600 | 0.0669 | 0.0747 | 0.0753 |
| 12h | 8 | 0.0438 | 0.0507 | 0.0879 | 0.0738 | 0.0899 |

As of this snapshot there are **zero independent events** and **zero rapid-rise cases** at both 6h and 12h. No 24h cases are yet scored. These forecasts overlap and cannot be counted as independent meteorological events. All learned candidates underperform simple persistence in this small quiet-period sample; **do not infer future extreme-event skill or overall model rankings**. Maintain authentic issuance-time cutoffs and report missing input and verified denominators.

## Next experiments (not authorized activation)

1. Obtain primary documentation from CEMVN1/USACE and USGS establishing station instrumentation, site surveys, datum, zero changes, timestamp and QC semantics.
2. Extend the overlap probe read-only to separated pre-2026 periods and current periods, with per-period paired and unpaired counts, coverage, exact-time value/delta differences, offsets, qualifiers, and provenance. Historical changes in stream identity are possible.
3. Audit actual historical training feature-missing rates and fitted dependence for all three MCHL1 predictors **per model and horizon**; the existence of coefficients or median imputation is not evidence of useful training support.
4. Extend the prospective scorecard with verified 24h sample sizes, explicit issue clustering, rise-stratified verification and missing-data accounting. Revisit performance only after independent coastal, river and mixed episodes.

**Never equate MAUL1 parameter 00065 with 4.0 ft NAVD88.** Use direct 63160 where certified. Keep forecasts authentic/immutable and models frozen.
