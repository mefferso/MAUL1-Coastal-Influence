# Phase 8 — retrospective precursor timing and propagation screens

**Status:** Reproducible retrospective research, not a forecast validation or operational warning product. Results below were produced from the archived inputs identified by SHA-256 in the generated `provenance.json` artifact. The analysis does not rewrite the historical archive, Phase 5 models, Phase 6 prospective forecasts, or the five-station network.

## Question and answer

Can the archived Lake Pontchartrain / Pass Manchac observations provide evidence before a meaningful MAUL1 rise? **Sometimes they meet the frozen observational screens before MAUL1 onset, but these results do not yet demonstrate useful operational coastal warning.** The strict Phase 4 coastal composite was uniquely credited before onset in only 3 of 179 known-onset events, and its lead was long (61–72 hours), with none within 24 hours. The lake and wind component screens appeared earlier in more events, but many also appeared in selected nonresponse windows. The six-hour wind screen preceded onset in 53 events (median retrospective lead 40 hours), including 14 within six hours; that is valid-time retrospective evidence, not a true forecast or receipt-time lead.

The results support continued research into coastal setup and wind as possible precursor context. They do **not** show that a screen gives forecasters 40 hours of actionable notice, establish coastal causation, or justify operational use.

## Data and method

- The analysis verifies 189 Phase 3B response events, 179 with usable onset times and 10 onset-uncertain, plus 63 preselected seven-day nonresponse controls.
- Each screen-present episode is assigned to at most one nearest upcoming known onset within 72 hours. Hourly rows are not treated as independent events. Event-level lead distributions count only uniquely credited pre-onset episodes.
- Phase 4's causal-quality physical evidence screens are replayed on valid time, with an expanding prior-only 90th percentile for DENL1 high discharge. Coastal, river, and component screens use completed hourly data; a six-hour condition is first credited only when the full six-hour evidence window can be evaluated.
- The event assessment window is −72 to +24 hours. This truncates longer leads; a 72-hour value is at the analysis-window boundary and is not interpreted as a known first onset.
- MCHL1 is optional shadow context only. Documented sentinel-contaminated values are excluded from MCHL1 context; they do not change the source archive. MCHL1 is not used in any operational model.
- NWCL1 astronomical residual is formed only from same-time, same-datum water level and prediction. Cross-station stage levels are not mixed across datums. MAUL1 native USGS `00065` is not compared to the 4.0 ft NAVD88 threshold.

Run from the repository root with:

```sh
python -m pip install -r requirements-phase5a.txt
python -m unittest discover -s tests -v
python scripts/phase8_lead_analysis.py --root . --output work/phase8
```

The script writes `summary.json`, `event-leads.json`, `control-alarms.json`, `propagation.json`, `case-studies.json`, and `provenance.json`. CI checks these artifacts and retains them without committing generated results. The provenance manifest includes SHA-256 hashes of source code, event/control/classification catalogs, and all hourly input files.

## Event-level screen results

Counts below use the 179 known-onset events. “Unique before” requires a positive lead and unique episode credit. The adjacent local timing columns count each event’s first local screen in its window; local pre-onset candidates can exceed uniquely credited detections because one precursor episode is never credited to two nearby events. “During” is at onset; “after” means the first local screen was after onset. `No local screen` is within the event assessment window. Lead percentiles are descriptive and event-level. They are not independent prospective validation, and nearby events may share meteorological episodes.

| Evidence screen | Unique before | Local before candidates | Median unique lead (p10–p90) | Unique before within 6 / 12 / 24 h | During | After | No local screen | Mean pre-onset unknown fraction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Coastal composite | 3/179 | 6 | 70 h (62.8–71.6) | 0 / 0 / 0 | 1 | 3 | 169 | 0.04% |
| River composite | 14/179 | 33 | 54 h (22.9–65.8) | 0 / 1 / 2 | 0 | 0 | 146 | 1.39% |
| NWCL1 residual | 46/179 | 63 | 51 h (19.5–69.5) | 3 / 3 / 7 | 1 | 10 | 105 | 0.81% |
| NWCL1 wind | 53/179 | 59 | 40 h (3.2–68.8) | 14 / 18 / 24 | 2 | 25 | 93 | 0.73% |
| MDLL1 lake stage change | 63/179 | 83 | 53 h (46–71) | 0 / 0 / 0 | 2 | 24 | 70 | 4.53% |
| MCHL1 Pass context | 24/179 | 28 | 56.5 h (41.3–70) | 0 / 0 / 0 | 0 | 6 | 145 | 68.47% |

The Phase 4 event evidence-screen labels across all 189 events are 56 Coastal-supported, 7 Compound-supported, 85 Indeterminate, and 41 River-supported. These are pre-existing rule-based evidence categories, not independent causal labels. The results do not establish causal discrimination: no downstream rainfall or local tributary inflow archive was available, and a DENL1 non-rise cannot rule out river input closer to MAUL1.

### Selected nonresponse controls

These 63 controls were previously selected, not randomly sampled. The fractions below are descriptive alarms in those intervals, not unbiased operational false-alarm rates. At each control's first screen trigger, the catalog recorded no response within 6, 12, or 24 hours for each signal:

| Screen | Controls with at least one signal | Signal episodes | Signal-present hours |
|---|---:|---:|---:|
| Coastal composite | 15/63 | 19 | 171 |
| River composite | 15/63 | 15 | 763 |
| NWCL1 residual | 41/63 | 62 | 1,082 |
| NWCL1 wind | 38/63 | 78 | 632 |
| MDLL1 lake stage change | 59/63 | 138 | 1,300 |
| MCHL1 Pass context | 19/63 | 39 | 391 |

This frequent control activity, especially for wind, residual, and lake-component screens, limits the evidence for useful event discrimination. A screen trigger does not by itself indicate an imminent MAUL1 rise.

## Coastal timing and propagation consistency

The proposed full sequence NWCL1 setup/residual → MDLL1 response → MCHL1 Pass response → MAUL1 rise was not consistently observed. Only 2 events had the strict four-step residual → lake → Pass-context → MAUL1 ordering (`maul1-response-0134`, onset 2023-11-23 11:00 UTC; and `maul1-response-0152`, onset 2024-09-29 01:00 UTC). A broader strictly ordered sequence with any three or more of those screens appeared in 17/179 events. These are screen timestamp orders, not measured water-wave travel times.

Among events with both screens available, residual confirmation preceded MDLL1 lake confirmation in only 8/33; 25 were simultaneous or in reverse order. MDLL1 confirmation preceded MCHL1 context in 13/21 (positive median 4 h, range 1–7 h); 8 were simultaneous or reversed. MCHL1 context preceded MAUL1 onset in all 24 paired events, with median lead 56.5 h and range 39–71 h, but its mean pre-onset missing fraction was 68.47%, and HADS/USGS matching does not independently validate a sensor. Each six-hour rolling screen blurs physical onset; timestamp ordering within a few hours is weak evidence, and the approximate ±6-hour pairwise screen timing uncertainty should be considered in addition to roughly ±1-hour catalog onset precision.

Lead-time sensitivity to fixed magnitude thresholds was explored without selecting a threshold on these data. At 0.75× thresholds, strict coastal detections increased from 3 to 8 events (median 61 h); at 1.25×, they fell to 2 (median 70.5 h). River detections changed from 14 to 16 and 14, respectively. These same-sample sensitivities are exploratory, not external validation.

## Illustrative cases

- **11 December 2018, event `maul1-response-0044`:** the coastal composite and lake-change screen were credited 70 h before onset. No river or residual screen was detected; the wind screen was active at the 72 h window boundary. The Phase 4 classification is Indeterminate, illustrating that an early coastal screen can coexist with insufficient evidence for a pathway classification.
- **8 May 2021, event `maul1-response-0094`:** the river screen was credited 68 h before onset and wind 55 h before. No coastal composite, residual, or lake screen was detected in the assessment period. The catalog label is Compound-supported, which is not an independent attribution and does not resolve how much of the event was river-driven.

These cases were selected from the same event sample for illustration; neither is independent validation. Full fields and screen coverage are in `case-studies.json` and `event-leads.json`.

## Interpretation and next scientific steps

The answer to whether coastal observations can ever precede MAUL1 is yes at the level of retrospective valid-time evidence screens. The stronger operational question remains unanswered. The strict coastal composite was uncommon and did not produce a credited lead inside 24 hours; wind and individual station signals produced earlier flags but also many selected-control signals. Since observation receipt times are absent, actual lead to forecasters could be shorter or zero.

The next high-value work is to acquire quality-controlled local rainfall/tributary observations and source receipt timestamps; have hydrologists review a small set of predeclared coastal, river, compound, and conflicting cases; verify the Phase 3B onset uncertainty against independent event evidence; and continue authentic Phase 6 prospective shadow collection until enough independent events accrue for event-blocked validation. Do not tune and validate a threshold on the same 189 events. Keep MCHL1 shadow-only and preserve all frozen models and prospective archives.
