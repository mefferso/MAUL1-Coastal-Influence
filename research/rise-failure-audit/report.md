# MAUL1 Significant-Rise Failure Audit

**Research / Shadow Evaluation / Not Operational. Retrospective diagnostics only.**

## Main finding

The published event and false-alert counts reproduce from the Phase 5B holdout rows using the existing Phase 6 outcome-target grouping and the Model Lab's issue-time episode rule. The 109 qualifying groups are separated only by qualifying target-time gaps; they are not proven independent physical hydrologic events. The event match is a threshold forecast on a qualifying valid-target row, not onset detection.

The apparent contrast is a difference in scoring objective and event rarity. Phase 5B ridge penalties were selected on calibration forward-fold MAE for continuous target stage change; no significant-rise classification or event-recall objective was used. Its all-case holdout MAE was 0.0626 vs 0.1742 ft persistence at 6h, 0.1219 vs 0.2415 ft at 12h, and 0.1902 vs 0.2403 ft at 24h. Yet only 5.7% of paired 24h target windows meet the +0.50-ft rise definition. At those target windows, the threshold forecast had 202 hits, 1,657 misses and 305 false positives: probability of detection 10.9%, false-alarm ratio 60.2%, CSI 9.3%. These overlapping row-level rates are not independent-event rates.

Phase 5B coastal + tidal: **28 detected / 81 missed** qualifying target groups; **305 false-positive target windows** in **48 false-alert issue-time clusters** (78 alert clusters total). The false-alert count describes rolling 24-hour forecast opportunities clustered when issue times are <=24 h apart; it is not a count of independent storms.

Among the 81 groups not credited as detected, 79 never reached +0.50 ft on any qualifying target window; two did cross the threshold on a later qualifying target row but only after the group's first qualifying target, so they fail the existing Phase 6 lead rule. This is lateness relative to the verification target, not a claim about physical onset. Among the 79 subthreshold cases, 57 had a maximum predicted rise below 0.40 ft and 22 peaked between 0.40 and 0.50 ft. The lowest 57 had a median observed qualifying target rise of 0.640 ft versus a median maximum prediction of 0.233 ft. This is evidence of missed rise magnitude on the scored windows; it does not identify a forcing cause. Predictor conditions below are issue-time valid-bin co-occurrences, not causal explanations. An unavailable signal can mean missing archived data or feature construction support; source receipt time and sensor QC histories are generally absent.

## Definitions and reproduction audit

| Check | Recomputed | Existing report | Result |
|---|---:|---:|---|
| Phase 6 qualifying groups | 109 | 109 | match |
| Detected | 28 | 28 | match |
| Missed | 81 | 81 | match |
| False alert clusters | 48 | 48 | match |
| False-positive target windows | 305 | 305 | match |

Phase 6 groups outcome-defined 24-hour MAUL1 native-stage changes >=0.50 ft when qualifying valid target times are at most 24 hours apart. Detection is an issued >=0.50-ft forecast for one of the qualifying targets before the group's first target. It does not establish physical onset. False alert clusters are built separately by sorting qualifying forecasts by issue time and joining adjacent issues no more than 24 hours apart; a cluster is false when none of its own linked valid targets meets the 0.50-ft outcome threshold.

### Independence audit

The separate Phase 3B response catalog contains 189 larger response windows (145 observed-response, 34 recovery-right-censored, 10 left-censored). 21 Phase 6 groups have no temporal overlap with a Phase 3B response window; 88 overlap one. 21 Phase 3B windows overlap multiple Phase 6 groups. This timing crosswalk shows the 109 are not demonstrably independent physical events; it is not an event identity match, because Phase 3B applies a different >=1-ft response definition and its windows can be censored by gaps/datum transitions.

## Missed-event patterns

| Mechanism label (descriptive) | Groups | Median max observed target rise | Median max Phase 5B predicted change | Median peak underforecast gap | NWCL1 residual present | DENL1 discharge present | MDLL1 24h change present |
|---|---:|---:|---:|---:|---:|---:|---:|
| large_subthreshold_forecast_not_causal | 57 | 0.640 ft | 0.233 ft | 0.396 ft | 100.0% | 100.0% | 100.0% |
| near_threshold_underforecast_not_causal | 22 | 0.682 ft | 0.473 ft | 0.234 ft | 100.0% | 100.0% | 100.0% |
| target_alert_matched | 28 | 0.802 ft | 0.653 ft | 0.113 ft | 100.0% | 100.0% | 100.0% |
| threshold_target_after_first_qualifying_target_not_physical_onset | 2 | 1.165 ft | 0.858 ft | 0.307 ft | 100.0% | 100.0% | 100.0% |

The event-level CSV has one row per all 109 groups, including individual maxima, issue-window context, target-window counts, categories, and predictor missingness in both the event issue window and the preceding 72 valid-time hours. ‘Near-threshold’ is an arithmetic bin (maximum forecast change >=0.40 and <0.50 ft), not a confidence bound. `phase4_category` flags are existing descriptive support screens and do not attribute cause.

### Issue-time signal co-occurrence

| Group status | Groups | Any NWCL1 residual >=0.50 ft | Any NWCL1 wind >=5 kn | Any Phase 4 river-supported hour | Any Phase 4 coastal-supported hour | Median NWCL1 residual | Median wind speed |
|---|---:|---:|---:|---:|---:|---:|---:|
| phase6 detected | 28 | 18 | 28 | 1 | 9 | 0.281 ft | 9.307 kn |
| phase6 not detected | 81 | 43 | 68 | 4 | 3 | 0.320 ft | 4.615 kn |

Within the 81 not-detected groups, issue-window NWCL1 residual reached 0.50 ft in 43 groups and wind speed reached 5 knots in 68; only three had any Phase 4 coastal-supported category hour. These screens co-occur with misses and do not identify causes. In particular, an elevated residual or wind vector alone did not reliably translate into the model's target-window threshold crossing.
Across event groups, median-of-group-median issue features (not row-independent estimates) were MAUL1 Δ6h 0.023 ft and Δ24h 0.115 ft for not-detected groups versus 0.110 and 0.102 ft for detected groups. Median DENL1 log-discharge change over 24h was -0.046 versus -0.045; MDLL1 24h native-stage change was 0.095 versus 0.094 ft. MDLL1 changes are within-station context only, not a cross-site stage comparison. The predictor coverage and receipt-time caveats above apply to these summaries.

## False-alert patterns

The 48 false clusters and 30 clusters containing at least one true target window are compared at the cluster level. False clusters had median max forecast change 0.591 ft; hit-containing clusters had 0.696 ft. Their median issue-time NWCL1 residuals were 0.559 ft (false) and 0.557 ft (hit-containing); median vector wind speeds were 15.778 and 16.173 kn. These similar coastal markers do not separate false from hit-containing episodes in this sample. 10 of the false clusters preceded the first qualifying target of a separate Phase 6 group by at most 72 hours; this is a diagnostic temporal relation, not onset lead or an event match. Episodes overlap and are serially dependent, so no independent-sample inference is claimed.

## Data coverage, freshness, and datum limits

The analysis has 32,406 completed 24-hour holdout forecast/observation rows from 2023-01-07T00:00:00Z through targets ending 2026-10-20T12:00:00Z. Another 776 24-hour holdout rows have no archived actual and are omitted. Every event score uses the Phase 5B row's own archived actual native gage height; this audit does not rescore against newer observations. The join uses issue UTC, target UTC, and horizon, with Phase 5A feature fields matched by issue time. MAUL1 is USGS 07380215 00065, feet, native gage height. The historical rows have no USGS approval/provisional qualifier, so quality state cannot be reclassified. NWCL1 residuals remain MLLW-referenced and are not numerically combined with MAUL1 native stage. No 4.0-ft NAVD88 threshold is used.

Feature missingness is listed per event in the CSV/JSON. An empty archive feature is unknown, not evidence that the physical forcing was absent. The historical archive mostly preserves observation valid time but not original receipt time, so even apparently pre-event feature rows do not prove they would have been available at a real issuance. MCHL1 stays unverified/shadow-only; its fields are counted as availability only and are not used for causal classification. Retrospective-valid-time NOAA astronomical predictions are not treated as issue-time evidence. No observation is interpolated or filled.

### Local precipitation and tributary data leads (not used in results)

USGS publishes precipitation parameter 00045 at the local MAUL1-area atmospheric site [301828090363100](https://waterdata.usgs.gov/monitoring-location/USGS-301828090363100), with a currently listed period beginning 2021-08-19. USGS warns that precipitation observations are temporary and may only be available for 120 days; a stable complete historical series therefore must be checked by actual retrieval and captured prospectively before modeling. [Bayou Fountain at Bluebonnet (07378810)](https://waterdata.usgs.gov/monitoring-location/USGS-07378810/) has a listed continuous gage-height record from 2007-10-01, and is a plausible local urban-tributary context series, but it is not a rainfall measurement or a validated discharge proxy. Candidate nearby series include [Bayou Manchac at Alligator Bayou (07378746)](https://waterdata.usgs.gov/monitoring-location/USGS-07378746/) and [Dawson Creek at Bluebonnet (07379960)](https://waterdata.usgs.gov/monitoring-location/USGS-07379960/). NOAA's [MRMS archive](https://www.nssl.noaa.gov/projects/mrms/MRMS_data.php) offers a gridded precipitation lead; it needs watershed aggregation and version, continuity, and quality checks. These sources were identified, not downloaded or joined; no result or existing archive contains them as predictors.

## Representative timelines

`representative-timelines.json` contains a few algorithmically selected, compact timelines: largest observed miss, closest subthreshold miss, a high-missingness miss, and representative false alert episodes. The timeline fields preserve issue time and valid time separately. These are illustrative outcomes selected from the same archive, not an independent sample.

## Prioritized hypotheses for challenger research

1. **Target-window scoring may understate useful earlier anticipation.** The current event rule only credits forecasts whose valid targets themselves qualify; test episode-level time-to-target diagnostics without relabeling target time as physical onset.
2. **A single 24-hour outcome may obscure trajectory shape.** Separate slow-rising, rapid-rising, and multi-peak response patterns using observed-only labels, keeping split/gap uncertainty explicit.
3. **The two-station coastal/river feature set may miss local runoff.** Check the local precipitation and tributary candidates above, first validating stable historical coverage, drainage relevance, units, datum, QC, and receipt times.
4. **Coastal predictor support may be intermittent or weak relative to the threshold.** Compare covariate coverage and magnitude on event windows versus alert episodes, with event-blocked uncertainty and no use of outcome labels as predictors.
5. **False alert episodes may indicate response heterogeneity rather than one overactive predictor.** Compare false clusters by river/coastal configuration and duration before any coefficient or threshold work.

These are hypotheses for an independently predeclared study, not model changes. No model was trained or tuned in this diagnostic package.

## Reproduction

From repository root run `python research/rise-failure-audit/audit.py`. This regenerates the event CSV, false-cluster CSV, compact JSON, representative timelines, and this report. The exact Phase 6 event grouping implementation is imported from `scripts/phase6_metrics.py`; source SHA-256 fingerprints are stored in `analysis.json`.

## Outputs

- `analysis.json`: reproducible summary, count checks, metadata, and provenance.
- `event-diagnostics.csv`: one compact row per all 109 Phase 6 groups.
- `false-alert-clusters.csv`: one row per threshold forecast episode, including all 48 false clusters.
- `representative-timelines.json`: small issue/valid-time examples.
- `report.md`: scientific narrative and limitations.
