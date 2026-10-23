# MAUL1 Coastal Influence Research v1.0

**Status: research application for shadow evaluation. Not an operational forecast, warning system, flood probability, or certified coastal attribution product.**

## Purpose and intended users

This static application brings the MAUL1 observation archive, frozen Phase 5 forecast models, genuine Phase 6 prospective issuances, and Phase 7–8 historical research into one forecaster-facing view. It is intended for research review by NWS New Orleans/Baton Rouge (LIX) meteorologists and collaborators. A user can inspect a current archived observation snapshot, compare native-stage 6/12/24-hour forecast guidance against persistence, review whether observations are stale or absent, and open the supporting methods and archives.

The website updates when a successful GitHub Actions data commit is deployed. It is not a continuously connected gauge display. Each displayed valid time and age describes the archived issue; the dashboard recalculates its age in the browser and labels stale observations. Successful model output and a technically working dashboard are not evidence of predictive skill.

## Five-station observation network

| Station | Research role and source | Displayed reference and limitations |
|---|---|---|
| DENL1 | Upstream Amite River discharge, USGS 07378500 | Discharge in cfs is distinct from stage. The issue snapshot may include current discharge plus frozen-model change features; upstream flow alone cannot rule out local tributary rainfall or establish a MAUL1 cause. |
| NWCL1 | Lake Pontchartrain water, prediction, and wind; NOAA CO-OPS 8761927 | Water and astronomical prediction must share valid time and MLLW datum before a residual is computed. Wind is meteorological FROM in source products. A wind feature by itself is not a complete coastal evidence screen. |
| MDLL1 | Independent lake-side gage, USGS 301200090072400 | Native gage height and same-station changes only. It is not silently equated with NWCL1 MLLW. |
| MCHL1 | Pass Manchac context; HADS DCP CE678A12 / IEM historical archive | Source QC, sensor identity, absolute vertical datum, and current delivery remain unverified. It is shadow-only and excluded from frozen model inference. Use relative changes only with an explicit unverified label. |
| MAUL1 | Target at Amite River at Highway 22, USGS 07380215 | Parameter 00065 is native gage height. Parameter 63160 is direct NAVD88 elevation when separately present and verified. They remain separate series. |

The dashboard shows provider, source valid time, retrieval time, reported QC, reference, and freshness when available. A missing value remains missing. It does not interpolate chart gaps or silently substitute a station.

## Datum safeguards

The local 4.0 ft threshold is in NAVD88. **Never compare it to MAUL1 native parameter 00065.** Phase 6 queries MAUL1 parameters 00065 and 63160. The v1.0 issue snapshot now carries 63160 as a separate availability record when an eligible observation is returned; it never enters model features. The dashboard compares against the 4.0 ft line only when that separate record is eligible, is from USGS NWIS, identifies parameter code 63160 and elevation, has datum NAVD88 and feet units, and is still fresh. Older issue records without that separate record keep the line withheld. No cross-parameter conversion is applied.

NWCL1 water and prediction can be subtracted only at matching valid times on MLLW. MDLL1 and MCHL1 gage heights are not cross-station elevations. Forecasts retain their native MAUL1 stage reference and must not be converted for presentation without an independent datum verification.

## Sources, provenance, and freshness

Historical archives retain source identifiers, units, datums, source and valid times, retrieval status, source responses and hashes where acquired. Some historical archives are hourly aggregates and do not preserve original observation receipt times or all raw provider QC metadata. A valid-time backtest using those files cannot prove that a predictor had arrived by a historical issue time.

Phase 6 records actual issue time separately from the nominal scheduled slot and model feature anchor. It captures source snapshots before issue time with source, parameter, datum, units, QC, valid time, retrieval time, provenance URL and response hash. Only completed hourly bins enter frozen model features; no interpolation or carry-forward is used. Input age and model-feature availability are separate checks. Failed, stale or missing required target data produce explicit abstention/diagnostic states rather than fabricated forecasts.

The compact `latest.json` feeds the page, while its matching authentic issue file in the immutable history archive provides the raw observation and feature details, including the separately captured 63160 field when present. The dashboard hydrates that full record by issuance ID. If hydration fails, it displays the compact archive state or a retrieval error; it does not fall back to historical plots as current conditions.

## Application sections

### Current conditions and observational context

The dashboard shows the latest archived authentic issue, target observation age and value, recent target change, and the five station/source cards. DENL1, NWCL1, MDLL1 and MAUL1 inputs show provider/QC metadata when captured. MCHL1 is marked unverified and shadow-only. Wind-vector magnitude and model-anchor changes are described as derived issue context, not independent observations or classifications.

Coastal-supporting, river-supporting, simultaneous, and indeterminate labels refer to physical evidence questions, not verified causal truth. The Phase 6 issue record is not a complete rolling Phase 4 screen evaluation. When a time-matched NWCL1 residual or a shared adequately covered evidence window is missing, the dashboard says the screen is incomplete and leaves the current assessment indeterminate. It does not turn an upstream discharge trend or a lake-level change into a coastal/river cause.

### Prospective forecast guidance

The existing Phase 6 panel displays authentic archived forecasts at 6, 12 and 24 hours, forecast valid time, persistence, the frozen Phase 5A/5B candidates, stage changes, historical 80% intervals when available, input imputation counts, availability and model artifact hash. Values remain in native MAUL1 gage-height reference. Persistence has no calibrated interval. The displayed intervals are frozen historical error intervals, not flood probabilities or newly calibrated uncertainty bounds.

Simulation runs are isolated and are not presented as authentic issuances. Actual issue time and model feature anchor are distinct. Forecast files are create-only, and a later verification revision does not rewrite the original forecast.

### Authentic prospective verification

Verification uses only authentic archived issues made before their forecast valid times and subsequent MAUL1 observations captured after those times. It reports MAE, RMSE, bias, persistence skill, rise hits/misses/false alarms, interval coverage, target observation delay, input-age strata, maturity/completeness, and outcome-group counts where available. Due-but-unverified targets remain unverified rather than being assigned a cause. Individual hourly forecast rows overlap and are not independent events; event metrics are withheld until at least five independent groups qualify under the fixed outcome rule.

At the main snapshot used for this v1.0 review (latest authentic issuance 2026-10-23 13:27 UTC), the performance archive held 125 verification records/revisions across model/horizon combinations. Each 6-hour model had 13 verified forecast/observation pairs and each 12-hour model had 12; no 24-hour model metrics had matured. There were zero qualifying independent event groups, so event detection/lead performance was insufficient. The 6-hour persistence MAE was 0.035 ft; Phase 5A MAUL1-only MAE was 0.057 ft (skill −0.63 vs persistence), and Phase 5A coastal MAE was 0.064 ft (skill −0.83). At 12 hours, persistence MAE was 0.056 ft; Phase 5A MAUL1-only MAE was 0.040 ft (skill +0.29), while Phase 5A coastal MAE was 0.120 ft (skill −1.12). These very small early samples are dominated by quiet conditions and do not establish general forecast skill. The 24-hour guidance remains unverified. The live performance file is the source of truth as records accumulate; historical hindcasts are never folded into these numbers.

## Historical research findings

Historical hindcast results and prospective forecasts are displayed in separate sections and datasets. Hindcasts are not genuine past prospective issues.

### Phase 7 data quality and cleaned-data experiment

An audit covered 4,137,183 rows in 130 archived monthly hourly files. MCHL1 contained 21 invalid stage values: two exact HADS `9999999` sentinels and 19 near-five-million-foot hourly means contaminated when a sentinel was averaged with valid reports. Another 206 derived MCHL1 changes contained sentinel arithmetic. The Phase 7 cleaner masks only these documented sentinel-contaminated values (and non-finite values) in a separate research copy; raw archives and frozen models remain unchanged. The derived Phase 4 archive also flags 594 adjacent MCHL1 stage jumps, which are repeated pairwise flags rather than 594 unique bad observations.

A cleaned Phase 5A replay left persistence, MAUL1-only and river-only holdout results unchanged; MCHL1-bearing coastal/full experiments changed. This is a sensitivity result on an already inspected historical holdout, not independent prospective validation. Frozen MCHL1-bearing models had less than 0.32% usable MCHL1 support during training. Data-quality correction does not establish sensor independence, gauge-zero stability, datum equivalence or a defensible basis to activate MCHL1 in forecasts. MCHL1 remains forecast-ineligible.

### Phase 8 retrospective precursor timing

Phase 8 examined 189 response events (179 with known onset; 10 uncertain) and 63 selected nonresponse controls. The strict coastal composite was uniquely credited before onset for 3/179 known-onset events, with median lead 70 hours and none within 24 hours. The river composite was credited in 14/179 (median 54 hours). NWCL1 wind screens were credited in 53/179 (median 40 hours; 14 within six hours) and appeared in 38/63 selected controls. Only two events showed the complete residual → lake → MCHL1 context → MAUL1 screen ordering.

These are retrospective valid-time precursor screens. They are not authentic forecasts, not receipt-time lead, not independent causal determinations, and not 40 hours of actionable warning. The selected controls do not provide an unbiased false-alarm rate. Data coverage, missing rainfall/local tributary observations, onset uncertainty and unverified MCHL1 context limit interpretation. The existing Phase 4 evidence classes (56 Coastal-supported, 7 Compound-supported, 85 Indeterminate, 41 River-supported across the catalog) are rule-based observational categories, not causal truth.

## Models and historical compatibility

Phase 5 frozen estimators forecast MAUL1 native-stage change at 6, 12 and 24 hours. The dashboard reads the frozen artifact and model hash; it does not retrain, refit, or select new weights. Model families include persistence, MAUL1-only, coastal, coastal+tide and full multivariable candidates. Phase 5B tidal predictors are historical/astronomical features as documented in the model methodology and do not establish that a tidal forcing caused a rise. MCHL1 is not promoted to a predictor.

Historical feature availability and Phase 6 per-issue availability are different questions. Phase 7/Phase 6.15 documented sparse MCHL1 training support and contamination. Phase 6 reports missing/imputed predictors per issuance. Activating a newly available source can create a training/inference mismatch even if the dashboard can display it; v1.0 makes no such activation.

## Verification methodology and uncertainty

For each genuine prospective issue, verification waits until the forecast valid time and subsequent observation capture. It preserves forecast and verification files separately and retains later corrections as numbered revisions. The target is the first available MAUL1 observation within the documented verification tolerance. Errors are observed minus forecast in native-stage units. Persistence is anchored to the same issue observation. Rise thresholds are evaluated against target change, and overlapping forecast outcomes are summarized at independent outcome-defined event level only when the minimum group count is reached.

Metrics are descriptive of the captured cases. Small samples, short observation windows, provisional providers, delayed observations, sparse event diversity and autocorrelation limit precision and generalization. The static dashboard's age is a page-view age from valid time; it does not estimate future provider delivery latency. Do not infer zero hazard from a missing or quiet station.

## What v1.0 can and cannot tell a forecaster

**It can:** show the latest archived authentic observation snapshot and its age; distinguish native versus documented references; show authentic archived forecast guidance and frozen model provenance; compare each forecast model with persistence; expose predictor gaps/imputation and verification sample size; and provide traceable historical methods and limitations.

**It cannot:** issue an operational warning; establish a flood probability; equate native 00065 to NAVD88; guarantee the static page is current; establish that Phase 8 precursors were available in real time; certify MCHL1; attribute a MAUL1 rise to coast versus river; prove predictive skill from software functioning; or replace NWS procedures and forecaster judgment.

## Maintenance and troubleshooting

- **Pages appears stale:** inspect the latest successful `Validate and deploy` run, deployment URL and Pages artifact. A failed source retrieval may leave the previous committed dashboard data in place; check the new run artifact and workflow log before interpreting values.
- **No forecast row or an abstention:** inspect `Phase 6 prospective verification` run logs and its `phase6-cycle-*` artifact. Check source availability, latest completed hourly bins, issue eligibility, target age, and feature diagnostics.
- **Verification pending:** confirm the forecast valid time has passed and later MAUL1 observations have been captured. A matured but absent target stays due-unverified; do not fill it manually.
- **Reproduce research:** run `python -m pip install -r requirements-phase5a.txt`, `python -m unittest discover -s tests -v`, `python scripts/phase7_data.py --help`, and `python scripts/phase8_lead_analysis.py --root . --output work/phase8`. Follow Phase 7/8 workflow and methodology docs for exact inputs and hashes.
- **Check the page:** run `node --check site/research-dashboard.js`, `node --check site/phase6.js`, `node tests/research-dashboard-smoke.cjs`, `node tests/site-smoke.cjs`, and `node tests/phase6-site-smoke.cjs`.
- Do not edit or delete historical forecast records, alter frozen model artifacts, change the five-station network, or turn simulations into authentic issues while troubleshooting.

## Highest-value future research

1. Accumulate genuinely prospective events and independent event groups across all three horizons; evaluate receipt-time delays, missed rises and persistence skill as samples mature.
2. Establish independent MCHL1 instrument identity, sensor history, datum/gauge-zero stability, QC meaning and current delivery through authoritative HADS/USACE records before any model use.
3. Capture a matched, continuous evidence archive including local tributary/rainfall observations and fully paired NWCL1 water/prediction/wind, with receipt timestamps; preregister event/control analyses before scoring coastal-versus-river discrimination.

## Release boundary

Research v1.0 consolidates a forecaster-readable shadow research interface and the existing immutable datasets. It is not operational certification. Any future operational proposal needs adequate independent prospective evidence, verified datum handling, reliable observation delivery, validated event and false-alarm performance, NWS review and appropriate authorization.
