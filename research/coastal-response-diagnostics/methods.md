# Methods and scientific safeguards

## Inputs and provenance

The inputs are the existing Phase 3A hourly valid-time archive, the Phase 3B MAUL1 response-event catalog, and its control-window catalog. The package reads only six monthly files around the predeclared cases: 2016-08, 2021-04, 2021-05, 2021-07, 2024-06 and 2024-07 (2024-06 and 2024-07 are each reused by the Alberto and Beryl cases). Exact byte hashes are in `diagnostics.json`. Phase 3A's full archive spans January 2016–October 2026; the event subsets are selected for process diagnostics, not model training.

The current five-station context and its limits follow the merged [expanded coastal-network investigation](../../docs/spatial-forcing-feasibility.md). The observed limitations of NWCL1 and the corrected Alberto/Beryl chronology follow merged [PR #59 research](../directional-wind-memory/report.md). Phase 3A/5A methodology and source definitions are in `../../docs/phase5a-methodology.md`; the response/control catalogs are `../../site/data/history/phase3b/response-events.csv` and `control-windows.csv`.

The NWCL1 wind series is NOAA CO-OPS station 8761927 at New Canal. It is a shoreline/structure observation, not an open-water lake-wide wind measurement. The Phase 3A archive stores hourly scalar mean wind speed and hourly vector means/direction reconstructed from its sub-hourly input. NWCL1 and the same-site CO-OPS/NDBC duplicate re-report are not independent stations. No mid-lake WeatherFlow/XPTN series or LKPL1 open-water record is present in these input archives. The original Alberto WeatherFlow record remains unrecovered, as documented by PR #59.

Input validity follows explicit archive fields and a month-specific within-hour source-coverage rule: for each month and station-variable, the modal positive, nonmissing archived `coverage` count is treated as the normal sub-hourly count; a row below 80% of that count is unusable. This accommodates historical changes in source cadence, such as 30-minute MAUL1/DENL1 archive periods, rather than applying one modern count across all years. No provider QC code is preserved in many Phase 3A hourly rows. The adapter also rejects nonfinite values, explicit missing flags, flagged-bad/rejected quality values, negative wind speed, and direction outside [0, 360]. It does not discard large finite stage or discharge values by statistical thresholds. The Phase 7 data-quality audit cautions that statistical jumps need provider-level review.

## Wind feature engine

For direction `θ` in meteorological degrees-from-north, hourly flow-to components are `u = −speed × sin(θ)` eastward and `v = −speed × cos(θ)` northward. When the archive supplies hourly vector means, their magnitude is preserved rather than inflated to the separate scalar mean speed. For an adapter input with no vector components, components are calculated from scalar speed and direction. A magnitude inconsistency above 0.05 knots between a supplied hourly vector and scalar speed invalidates that wind hour.

The wind scalar speed and vector means have the same hourly label but different averaging statistics. The directional stress proxy is the product of hourly scalar mean speed and hourly mean U or V, in kt². Its rolling integral is the sum over observed valid hourly bins, in kt²·h. These are directional **proxies**, not physical wind stress: wind height, exposure normalization, drag coefficient, and sub-hourly covariance are unavailable. Missing bins are not filled, and coverage is reported. A rolling 3-, 6-, 12-, 24-, 48-, or 72-hour feature is present only when at least 80% of the full trailing window is valid; the window is not shortened at archive edges.

Directional persistence is resultant hourly vector magnitude divided by summed scalar speed, 0–1. Wind speed acceleration and relaxation are one-hour differences; directional reversal is a circular heading shift of at least 150° while both hourly speeds are at least 5 knots. Within-sector duration is reported as both total qualifying hourly bins and longest contiguous run; missing bins break runs. The default non-overlapping 8-point compass sectors define easterly as 67.5°–<112.5° and southeasterly as 112.5°–<157.5° **from** direction. Descriptive speed thresholds are 5, 10 and 15 knots. These are exploratory bins, not thresholds or warnings.

No fetch-aligned axis is called favorable. NWCL1 siting and the complete lake-wide wind field are not sufficient to validate the relevant channel/fetch projection. Cardinal U/V are retained for a future geometry-reviewed analysis.

## Water-level and river response

- **NWCL1:** water minus astronomical prediction is formed only at exact matching UTC hourly bins with both values in feet and datum `MLLW`. Residual tendencies use exact endpoints. The predictions are retrospective valid-time data; receipt/advance availability is unknown.
- **MDLL1:** USGS 301200090072400 native gage-height changes and anomalies relative to its own preceding 72-hour median. No absolute MDLL1 value is subtracted from NWCL1 or MAUL1.
- **MAUL1:** only USGS stage/parameter 00065 in its native gage-height reference is read. `elevation`/parameter 63160 NAVD88 is not read or equated with 00065. Stage changes require exact endpoints, feet, and matching gage-height metadata.
- **DENL1:** USGS 07378500 native discharge changes in cfs are context. They do not measure all tributary/local rainfall forcing.
- **MCHL1:** excluded from these quantitative calculations; it remains shadow-only under the earlier sensor/datum and duplicate-stream cautions.

Stage and discharge endpoint phase summaries require at least 80% valid hourly coverage within the phase and compatible unit/datum metadata across every selected observation. Sparse phases report valid counts and endpoints but suppress the phase change. Per-station maximum times are selected within the event catalog response interval (or fixed control window), not the wider antecedent/forcing chart. Differences between peak times are only observed time offsets, not physical propagation estimates or usable forecast lead.

## Predeclared cases and event windows

All event windows are half-open UTC and fixed in `event_windows.json`; no window/threshold/lag was selected to maximize a correlation. Phase3B response onsets, peaks and recoveries are outcome-defined retrospective labels, not verified weather-forcing onset.

- **Alberto (2024):** June 15 pre-named disturbed-weather context, June 19 12Z–June 20 09Z named-storm formation-to-landfall chronology, post-landfall recession, and a separately labeled June 27–July 1 transition. The catalog MAUL1 rise begins June 10, before the selected pre-named window and before NHC named-storm formation. The local water rise therefore cannot be described as a response beginning after the named storm.
- **Beryl (2024):** the June 27–July 1 transition remains unattributed and excluded from Beryl local-forcing attribution; Beryl remote Caribbean/Yucatan (July 1–5), Gulf approach/landfall (July 5–9), and post-landfall recovery (through catalog recovery) are separate. The MAUL1 catalog event begins June 28, before the Gulf-approach window, and is not labeled Beryl-caused.
- **May 2021:** Phase3B response onset/peak/recovery define the response interval; no local wind-forcing onset is asserted from the synoptic chart.
- **August 2016:** response catalog marks onset left-censored/uncertain; sparse pre-onset MAUL1 stage coverage prevents an antecedent endpoint-change estimate. Wind/discharge are context only; the case is not assigned a specific forcing source by this archive.
- **Control:** Phase3B `control-candidate-00289` (July 9–16, 2021), status eligible-control candidate and category quiet-low-variation. This outcome-defined control is a fixed contrast, not a matched independent event or counterfactual.

## Lag profile

For each designated source phase, the trailing 24-hour eastward/northward stress proxies at `t` are paired with an exact same-station 6-hour change beginning at `t + lag`, at fixed lags 0, 6, 12, 24, 36, 48 and 72 hours. The targets are NWCL1 residual, MDLL1 native stage, MAUL1 native 00065 stage, and DENL1 discharge. Pairs are spaced every six hours to avoid overlap among the target six-hour intervals, but the wind histories overlap and serial dependence remains. Pearson correlations are descriptive and shown only for at least six pairs; no p-values, confidence intervals, best-lag selection, causal claim, or predictive-skill claim is made. For the August 2016 left-censored case, event chronology does not establish a physical wind forcing start.

## Prospective adapter contract

The Python `normalize_prospective_observation` function and `prospective-observation.schema.json` define a future collector adapter boundary. It requires source identity, station/variable, valid time, actual received time, value, unit, datum and QC status; receipt latency is derived without inventing a historical receipt time. It is a schema/interface only and does not import or modify Agent 1's live collector.
