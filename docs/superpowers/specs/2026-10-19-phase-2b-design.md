# Phase 2B Independent Event Identification and Verification

## Goal

Determine, without predictor-influenced target selection, whether the five-station archive contains repeatable river or lake signals that precede meaningful MAUL1 rising-water episodes.

## Target-event design

MAUL1 alone defines target episodes. From the hourly native-gage-height series,
identify contiguous rising episodes using a fixed antecedent 72-hour baseline,
requiring at least 48 valid baseline hours. A candidate must have a positive
rise exceeding both a robust baseline-change threshold and fixed physical
safeguards: at least 0.25 ft total rise, at least 3 hours duration, and a
positive maximum hourly rise. A 6-hour separation after a falling/flat reset
prevents one response from being split into noise; overlapping candidates are
merged. If the archive starts during a sustained rise or lacks the antecedent
baseline, the episode is retained with `already_underway` or
`unavailable_baseline`, not silently discarded.

Each episode records onset, peak, duration, maximum rise, coverage, missingness,
datum status, and limitations. MAUL1 00065 remains native gage height; direct
63160 NAVD88 is retained separately and is the only threshold-qualified series.

## Predictor episodes and matching

DENL1 discharge, NWCL1 residual, and MDLL1 stage use their own fixed-baseline,
positive-rise episode detectors. Predictor signals never determine target-event
membership. Each predictor episode is matched at most once to the nearest
eligible MAUL1 response in predeclared search windows: DENL1 0–72 hours, NWCL1
0–18 hours, and MDLL1 0–18 hours. A predictor after target onset is not a lead.
Unmatched predictor episodes and unmatched MAUL1 responses are emitted. A
matched timing result is `detected_not_validated`, never reliable forecast skill.

Sally and Beta 2020 are linked as one potentially dependent hydrometeorological
episode because their windows overlap. Summary counts are descriptive event
counts only; hourly observations are never treated as independent samples.

## Output and UI

`site/data/verification.json` is a separate structured artifact containing
target episodes, predictor episodes, matches, unmatched signals, case-study
notes, summary counts, and explicit data-quality/datum limitations. Existing
raw archives, hourly products, legacy correlations, and event charts remain
unchanged. The dashboard adds a compact Independent Event Verification card
with a table, status/lead labels, unmatched counts, and selected event markers.

## Case-study handling

The generated report explicitly includes August 2016, Beta 2020, November 2024,
and at least two other configured windows, including April 2025. It reports
insufficient coverage or nonresponse evidence rather than manufacturing a
classification. No percentages, forecast probabilities, causal attribution,
unverified NAVD88 conversion, or universal propagation lag are produced.

## Testing and operations

Deterministic tests cover fixed-baseline target selection, multiple episodes,
falling observations, missing data, already-underway starts, overlap linkage,
one-to-one matching, negative/positive lead signs, post-onset predictors,
unmatched/nonresponse records, datum protection, and reproducible verification
output. GitHub Actions runs the analysis, validates JSON, executes Python and
site tests, and deploys only after verification passes.
