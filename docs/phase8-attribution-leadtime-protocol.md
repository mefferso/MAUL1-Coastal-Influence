# Phase 8 — causal-evidence screening and advance-warning verification protocol

**Status: preregistered research plan, not computed scientific results.** Phase 8 is distinct from the already-inspected Phase 3B/4 classifications, Phase 5 hindcasts and authentic Phase 6 forecasts. It does not approve operational use.

## Motivation and archived baseline

Phase 3B identified 189 meaningful MAUL1 native-stage response events, 179 with known onsets, and 63 seven-day controls. Phase 4's provisional rule-based evidence summary found 41 river-supported, 56 coastal-supported, 7 compound-supported, and 85 indeterminate event records (the categories are evidence screens, not verified physical causes). Phase 7 compared coastal-tidal and MAUL1-only historical predictions over 56 response-event groups, but these were **not** externally classified coastal events and did not demonstrate an advance-warning lead before MAUL1 itself rises. Do not conflate these 56 groups with Phase 4's 56 coastal-supported events.

## Scientific questions and explicit estimands

1. **Lead before MAUL1 response:** At each MAUL1 event with an independently determined onset time, determine when the *first sustained*, eligible upstream/coastal evidence was available **as of decision time**, including minimum six-hour persistence confirmation and the completed-bin lag. Report lead in elapsed hours from first eligible detection to MAUL1 onset. Evidence timestamp is the first time the screen was **confirmed**, never the first hour of the persistence window.
2. **False signals:** For independent controls, count how often the same predeclared evidence screens triggered without MAUL1 response in the next 6/12/24 hours. State control selection and censoring; 63 already-selected controls are not a random background exposure sample.
3. **Coastal vs river discrimination:** Keep Phase 4 river/coastal/compound/indeterminate as *screen outcomes*, never causal truth. Independent attribution needs external hydrometeorological evidence and, where possible, agency-reviewed cases. Unknown must remain unknown.
4. **Forecast value:** Among authentic prospective issued forecasts only, calculate MAE, rise detection, false alarms, calibration, and paired skill versus persistence/MAUL1-only at 6/12/24h; distinguish model signal from persistence and avoid overlapping issue-time pseudo-replication.

## Predeclared event accounting

- Use Phase 3B revised MAUL1-first event IDs and timestamps, not legacy transitive all-station groups.
- Preserve 189 event records; report exclusions and denominators separately for onset-known (179), predictor-covered, quality-eligible, pre-event lead identifiable, and nonresponse controls.
- Define assessment windows `[-72h,+24h]` around onset for diagnostics; report pre-onset evidence separately from concurrent and post-onset detection. A result appearing after onset has **no early-warning lead**, even if it correlates strongly with MAUL1.
- Prevent double counting of closely spaced events: assign eligible detections to at most one event for primary hit accounting. Publish duplicate/ambiguous matches as separate sensitivity results rather than pretending independence.
- Never optimize a lag/window/threshold by choosing the best values on a test event and then reporting performance on that same event. Use physically defined candidates and separately labeled exploratory sensitivity analyses.
- Attribute measured lead to the **decision-time screen confirmation**, including completed-bin and availability rules. Historical receipt times were not archived, so distinguish *valid-time retrospective lead* from *actual operational lead*. The former is only an upper-bound/idealized diagnostic without arrival-time data.
- Report onset-detection uncertainty due to hourly aggregation, incomplete observations, and coarse gauge temporal resolution.

## Evidence pathways and sensitivity

- **Coastal:** NWCL1 astronomical residual (same-hour observed minus predicted on same MLLW reference); NWCL1 wind transport; MDLL1 native stage change. Use the original Phase 4 fixed six-hour screen and 72–24h baseline as the primary comparator. Investigate propagation with separately labeled 3/6/12/24/36h lookbacks and physically motivated positive lag assumptions; do not fit causality by maximizing correlation.
- **River:** DENL1 discharge and antecedent changes; explicitly note rainfall/local tributaries downstream of DENL1 are missing forcing components.
- **Pass Manchac:** MCHL1 is optional context only, with unverified source QC, sensor identity and vertical datum. Never substitute USGS 073802302 readings as MCHL1 data in an existing model. Separate experimental within-station changes require source-specific provenance and period-level gates.
- **Compound:** simultaneous independent forcing evidence; do not infer proportions or interactions solely from classification overlap.
- **Indeterminate:** preserve when no pathway meets evidence or observations/QC are inadequate; do not turn absent support into evidence of zero contribution.

## Required outputs for subsequent implementation

1. `site/data/research/phase8/event-leads.json` with per-event id, MAUL1 onset, independent event windows, first *confirmed* predictor timestamp per pathway, evidence availability/QC, lead hours (negative if post-onset), class-screen source, exclusion reason, and provenance.
2. `site/data/research/phase8/control-alarms.json` including denominator/control exposure and matched forward outcome windows with censoring accounted for.
3. `site/data/research/phase8/summary.json` with event-level eligible N, median/P10/P90 pre-onset lead, missed events, detected-after-onset events, false signals in controls, window sensitivities, and no unsupported confidence statements.
4. `docs/phase8-results.md` separating real computed results from unknowns and recommending whether the current data justify any prospective **shadow-only** signal.
5. Deterministic tests for event overlap, onset edge, signal only after onset, incomplete six-bin persistence, no datum mixing, no future time access, and missing-data attribution.

## Strict gates

- Preserve Phase 5 frozen models, immutable Phase 6 authentic archives, and original Phase 3/4/7 data.
- MAUL1 USGS 00065 native gage height must **never** be evaluated against the 4.0 ft NAVD88 coastal threshold without independently verified conversion or direct USGS 63160 elevation.
- No new operational alert or model promotion based on retrospective comparisons.
- Preserve canonical five-station network: DENL1, NWCL1, MDLL1, MCHL1, MAUL1.
- Do not imply that successful CI or large counts of overlapping hours establish physically correct causal attribution.
- When scientific evidence is insufficient, report the coverage problem, observational ambiguity, and how it may bias results.

## Execution sequence

First inspect the current main and methodology; then implement deterministic **read-only** event-time tables and tests; run the existing event and verification workflows plus new tests; inspect actual event-level denominators and edge cases; build controls and sensitivity checks; finally publish a research report. Use a focused PR, merge only after required checks pass. Prefer reusable scripts over dashboard additions. If authentic prospective case counts remain too low, let Phase 6 continue to collect them without synthetic backfills.
