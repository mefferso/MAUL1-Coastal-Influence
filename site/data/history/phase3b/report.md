# Phase 3B — Independent historical validation

**Status: exploratory historical validation. No forecast model, causal classifier, or skill claim.**

## Main finding

The archive contains descriptive timing associations, but it does not establish that the five-station network provides demonstrably useful advance warning. Event onsets, matching thresholds, and observation coverage remain uncertain; no independent causal ground truth or pre-issued forecast opportunities exist. Probability of detection, false-alarm ratio, and critical success index are therefore reported as unavailable.

## Data and detection audit

The analysis used 130 UTC months (2016-01 through 2026-10) and retained source-level unresolved months in the coverage audit. The selected target detector produced 593 detected MAUL1 rise episodes, grouped into 101 target-containing time clusters with a fixed 72-hour cross-station separation rule. These are algorithmic clusters, not verified independent storms.

| Station | Variable | Valid hours | Missing hours | Not yet observed | Expected hours |
|---|---|---:|---:|---:|---:|
| DENL1 | discharge | 94645 | 49 | 274 | 94968 |
| DENL1 | stage | 94478 | 216 | 274 | 94968 |
| MAUL1 | elevation | 2441 | 957 | 274 | 3672 |
| MAUL1 | stage | 87655 | 7039 | 274 | 94968 |
| MCHL1 | stage | 30705 | 2621 | 274 | 33600 |
| MDLL1 | stage | 90953 | 837 | 274 | 92064 |
| NWCL1-NDBC | gust | 86048 | 3558 | 274 | 89880 |
| NWCL1-NDBC | wind | 86048 | 3558 | 274 | 89880 |
| NWCL1-NDBC | wind_direction | 86048 | 1326 | 274 | 87648 |
| NWCL1-NDBC | wind_u | 86048 | 3558 | 274 | 89880 |
| NWCL1-NDBC | wind_v | 86048 | 3558 | 274 | 89880 |
| NWCL1 | prediction | 94968 | 0 | 0 | 94968 |
| NWCL1 | water | 94501 | 193 | 274 | 94968 |
| NWCL1 | wind | 94018 | 676 | 274 | 94968 |
| NWCL1 | wind_direction | 94018 | 676 | 274 | 94968 |
| NWCL1 | wind_u | 94018 | 676 | 274 | 94968 |
| NWCL1 | wind_v | 94018 | 676 | 274 | 94968 |

Monthly retrieval errors, empty successful queries, and not-queried sources are shown separately in `coverage.json`; a source month without rows is not labeled as an observed hourly gap. Gap interval timestamps are machine-readable in that file.

| Detector sigma | MAUL1 detected episodes | Target-containing groups | Groups with advance timing association | Descriptive group matches | All target detector records |
|---:|---:|---:|---:|---:|---:|
| 1.5 | 992 | 25 | 15 | 18 | 2164 |
| 2.0 | 593 | 101 | 64 | 75 | 1410 |
| 2.5 | 327 | 155 | 75 | 86 | 871 |

The sensitivity results show that episode counts change materially with the pre-existing 1.5/2.0/2.5 robust-sigma setting. The 72-hour baseline, minimum 48 baseline changes, 3-hour minimum persistence, fixed station-specific minimum rise, positive consecutive changes, and 6-hour reset were kept fixed. Thresholds were not reselected on the same archive to claim skill.

Quality review retained 6721 automated flag(s) as candidates, chiefly NWCL1:gust (3199), NWCL1-NDBC:gust (2928), MCHL1:stage (594). Direct MAUL1 NAVD88 archive observations above 4.0 ft: 0; native 00065 values are excluded from that count.

The month-reset counterfactual in `validation.json` reports local left-censor, early-onset, and reclassified/missed-onset counts by detector series. Each disagreement is an audit flag, not a scientifically verified false event.

## Precursor timing

| Predictor | Matched event groups | Median lead | Interquartile range | Range |
|---|---:|---:|---:|---:|
| DENL1 | 40 | 24.0 h | 11.75–48.5 h | 3.0–72.0 h |
| NWCL1 | 0 | unavailable | unavailable | unavailable |
| MDLL1 | 35 | 4.0 h | 2.5–6.5 h | 1.0–11.0 h |

The lead table includes detected time groups with available onset records. The coverage-qualified subset (0.9 hourly completeness in each station-specific matching window) is summarized separately in `validation.json`; all retained/excluded groups remain in `events.csv` and `exclusions.csv`.

These are retrospective onset differences conditional on the detector finding a signal and a MAUL1 episode within the fixed 0–72 h DENL1 or 0–18 h NWCL1/MDLL1 window. Simultaneous signals are not advance notice. They do not account for real-time data latency or demonstrate actionable warning. NWCL1 residual alone is not coastal evidence; MDLL1 and independent wind context are reported separately.

## Nonresponse, missed events, and metrics

The event table retains 3 detected MAUL1 groups without a qualifying earlier signal, 28 predictor-only groups, 32 groups with detected predictors only after target onset, 2 coincident groups with no positive lead, and 0 groups with uncertain target onset. The 0.9-coverage screen leaves 0 target groups for descriptive network-availability summaries.

The control audit retained 0 well-observed quiet month(s) under a 90% coverage screen for MAUL1 stage, DENL1 discharge, NWCL1 residual, and MDLL1 stage; 130 months are retained with source/coverage/signal exclusion reasons. Quiet means no detector candidate in those series, not no forcing.

These are descriptive response/nonresponse counts, not false alarms or missed forecasts: the archive does not encode forecast issuance times, independent forcing labels, or all intervening runoff. Event-level POD, FAR, and CSI are `unavailable` because prediction opportunities, response labels, event independence, and uniform coverage requirements are not established.

## Event independence and future split

Episodes were grouped across stations before splitting. The primary rule connects records whose active intervals overlap or are separated by at most 72 hours; 48, 72, 96-hour sensitivity counts are in the JSON report. This rule cannot prove meteorological independence. A fixed Jan 1, 2023 calibration/holdout boundary and 72-hour seam embargo are recorded for future work; they do not constitute Phase 4 holdout results. The available archive and current labels do not support a statistically defensible independent forecast holdout claim.

## Priority cases

### August 2016 Louisiana flood
UTC window 2016-08-09T00:00:00Z to 2016-08-23T00:00:00Z (end exclusive). Canonical Phase 2B verification: 1 target episode(s), 0 timing match(es), 6 unmatched predictor record(s).
MAUL1 native stage coverage: 221/336 hours; datum gage height. The detailed UTC observation/signal timeline and other station coverage are in `cases.json`.
Observed continuous-archive UTC signal timeline: 2016-08-06T03:00:00Z DENL1 predictor_signal (detected); 2016-08-07T08:00:00Z DENL1 predictor_signal (detected); 2016-08-07T16:00:00Z MDLL1 predictor_signal (detected); 2016-08-08T01:00:00Z MDLL1 predictor_signal (uncertain); 2016-08-08T08:00:00Z DENL1 predictor_signal (detected); 2016-08-09T21:00:00Z MDLL1 predictor_signal (uncertain); 2016-08-10T22:00:00Z DENL1 predictor_signal (detected); 2016-08-11T13:00:00Z MDLL1 predictor_signal (detected).
Independent context: NOAA NCEI Storm Events 657049 (13-AUG-16 21:00:00, Ascension, Flood; source `Emergency Manager`) — NCEI narrative states two days of heavy rain drained into the Amite River, record river levels, and backwater flooding; it reports about 16,000 homes/businesses with varying damage.
Independent context: NOAA NCEI Storm Events 657054 (15-AUG-16 07:00:00, St. James, Flood; source `Emergency Manager`) — NCEI narrative links record Amite River levels to upstream flow/backwater flooding along the Blind River.
The canonical target episode begins already underway with unknown onset; retrospective signals cannot resolve a prior lead or establish cause. MCHL1 availability is incomplete for this period.

### Tropical Storm Beta
UTC window 2020-09-18T00:00:00Z to 2020-09-29T00:00:00Z (end exclusive). Canonical Phase 2B verification: 1 target episode(s), 0 timing match(es), 8 unmatched predictor record(s).
MAUL1 native stage coverage: 264/264 hours; datum gage height. The detailed UTC observation/signal timeline and other station coverage are in `cases.json`.
Observed continuous-archive UTC signal timeline: 2020-09-15T07:00:00Z MDLL1 predictor_signal (uncertain); 2020-09-17T07:00:00Z DENL1 predictor_signal (no_signal); 2020-09-19T01:00:00Z MAUL1 MAUL1_candidate_response (uncertain); 2020-09-19T08:00:00Z DENL1 predictor_signal (uncertain); 2020-09-19T17:00:00Z MAUL1 MAUL1_candidate_response (detected); 2020-09-19T21:00:00Z DENL1 predictor_signal (no_signal); 2020-09-20T09:00:00Z DENL1 predictor_signal (no_signal); 2020-09-20T09:00:00Z MDLL1 predictor_signal (detected).
Independent context: NOAA NCEI Storm Events 921987 (22-SEP-20 19:00:00 CDT, Livingston, Storm Surge/Tide; source `Other Federal Agency`) — NCEI narrative reports 4.04 ft NAVD88 at USGS MAUL1 and 5.47 ft NAVD88 at USACE TSPL1 at 19:00 CDT; its episode narrative describes persistent moderate/strong onshore east and northeast winds and impacts Sep 19–23.
Independent context: NOAA NCEI Storm Events 921979 (21-SEP-20 06:00:00 CST, Orleans, Storm Surge/Tide; source `Other Federal Agency`) — NCEI narrative reports 3.83 ft MHHW at NOS New Canal NWCL1 and a separate 4.66 ft NAVD88 at USACE PRSL1. The NWCL1 MHHW value is not directly interchangeable with NAVD88.
The canonical target episode begins already underway with unknown onset; retrospective signals cannot resolve a prior lead or establish cause. MCHL1 availability is incomplete for this period.
NCEI’s event narrative is a documented external report of 4.04 ft NAVD88 at MAUL1 on Sep 22 local time (source field “Other Federal Agency”). It is not a direct archived 63160 row and is kept as contextual evidence pending instrument/report provenance; the historical gage-height series is still not converted or used to claim the threshold.

### November 2024 coastal-advisory window
UTC window 2024-11-14T00:00:00Z to 2024-11-25T00:00:00Z (end exclusive). Canonical Phase 2B verification: 2 target episode(s), 1 timing match(es), 5 unmatched predictor record(s).
MAUL1 native stage coverage: 264/264 hours; datum gage height. The detailed UTC observation/signal timeline and other station coverage are in `cases.json`.
Observed continuous-archive UTC signal timeline: 2024-11-13T04:00:00Z MDLL1 predictor_signal (uncertain); 2024-11-13T06:00:00Z MAUL1 MAUL1_candidate_response (uncertain); 2024-11-14T02:00:00Z MDLL1 predictor_signal (detected); 2024-11-16T08:00:00Z MCHL1 MCHL1_support_episode (detected); 2024-11-16T09:00:00Z MAUL1 MAUL1_candidate_response (uncertain); 2024-11-16T09:00:00Z MDLL1 predictor_signal (detected); 2024-11-17T03:00:00Z MDLL1 predictor_signal (detected); 2024-11-17T10:00:00Z MAUL1 MAUL1_candidate_response (uncertain).
Independent context: NOAA NCEI Storm Events 1224701 (19-NOV-24 07:20:00 CST, St. Tammany, Flash Flood; source `Public`) — NCEI narrative reports Gause Boulevard was impassable due to heavy rainfall.
Independent context: NOAA NCEI Storm Events 1224686 (19-NOV-24 06:35:00 CST, St. Tammany, Flash Flood; source `Broadcast Media`) — NCEI narrative reports flooded roads and stalled vehicles in Mandeville.
The previously preliminary timing association is not treated as validation; NWCL1 residual, independent MDLL1 response, winds, and target onset uncertainty must be considered jointly. No causal conclusion follows from residual timing alone.

### April 2025 southeast-wind window
UTC window 2025-04-01T00:00:00Z to 2025-04-12T00:00:00Z (end exclusive). Canonical Phase 2B verification: 1 target episode(s), 0 timing match(es), 2 unmatched predictor record(s).
MAUL1 native stage coverage: 264/264 hours; datum gage height. The detailed UTC observation/signal timeline and other station coverage are in `cases.json`.
Observed continuous-archive UTC signal timeline: 2025-03-29T08:00:00Z MDLL1 predictor_signal (detected); 2025-03-30T01:00:00Z DENL1 predictor_signal (detected); 2025-03-30T19:00:00Z DENL1 predictor_signal (detected); 2025-03-31T13:00:00Z DENL1 predictor_signal (detected); 2025-03-31T14:00:00Z MAUL1 MAUL1_candidate_response (no_signal); 2025-03-31T14:00:00Z MDLL1 predictor_signal (uncertain); 2025-04-01T19:00:00Z MAUL1 MAUL1_candidate_response (detected); 2025-04-01T19:00:00Z MDLL1 predictor_signal (detected).
The April response is compared with all archived predictors and independent wind observations; missing periods and native datums remain explicit. Timing evidence alone cannot distinguish river, coastal, and compound mechanisms.
The reviewed NCEI detail release has no event rows in the selected Lake Maurepas/Pass Manchac corridor counties for this window; it contains Louisiana events elsewhere. No local entry is not evidence that local runoff or coastal forcing was absent.

## Datum and source safeguards

MAUL1 00065 remains native gage height. Only direct 63160 NAVD88 observations are eligible for the 4.0 ft NAVD88 threshold; this Phase 3B target detector does not use gage height to claim that threshold. NWCL1 positive residual is not sufficient to label coastal influence. A lack of DENL1 discharge response does not rule out downstream tributaries or local runoff. MCHL1 is not merged with either USACE station; NDBC winds remain an independent comparison.

## Files

- `validation.json`: audit, event groups, sensitivity, timing summaries, and split assignments.
- `summary.json`: compact dashboard result.
- `events.csv`: event-group level records with coverage and outcome state.
- `matches.csv`: per-group predictor timing, including lead and method status.
- `cases.json`: the four priority case reviews with compact UTC timelines.
- `coverage.json`: hourly denominator, gaps, and monthly source acquisition states.
- `exclusions.csv`: retained non-detections and explicit exclusion reasons.

This evidence supports further independent review and better-labeled data collection. It does not support operational forecasting or causal classification.
