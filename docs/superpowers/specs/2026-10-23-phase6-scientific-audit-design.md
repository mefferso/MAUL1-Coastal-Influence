# Phase 6 scientific audit and scorecard design

## Intent

Make the frozen models' historical support for MCHL1 explicit and make the prospective dashboard easier to interpret without implying skill from a small, overlapping quiet-period sample.

## Goals

- Reproduce MCHL1 feature availability for each frozen model and 6-, 12-, and 24-hour horizon from the committed training archives and exact frozen artifacts.
- Report missing percentages, learned value and missingness coefficients where applicable, and the resulting training-to-inference support mismatch.
- Show MAE, RMSE, bias, sample sizes, persistence comparison, rise detection denominators, interval denominators, independent-event counts, and explicit pending 24-hour results in the Phase 6 scorecard.
- Preserve source and model provenance and all existing safeguards.

## Non-goals and anti-goals

- Do not retrain, modify, or replace frozen models.
- Do not activate MCHL1, infer datum conversion, or treat MCHL1/USGS agreement as independent sensor validation.
- Do not manufacture historical prospective forecasts or add MCHL1 to the inference feature set.
- Do not classify coastal, river, or mixed events without defensible independent evidence.

## Constraints

- Preserve the five-station network and authentic immutable prospective archives.
- MAUL1 native USGS 00065 must not be equated with the 4.0 ft NAVD88 threshold.
- Report independent events as insufficient until the existing five-event gate is met; overlapping issues are not independent samples.
- Keep the existing site architecture and Python/vanilla JavaScript stack.

## Approaches

1. Add a read-only Python audit script over the committed data/artifacts, pin its model-family support logic in unit tests, and commit the resulting scientific note. This is recommended because it reproduces findings without touching model fitting or forecast archives.
2. Manually inspect JSON and publish a prose-only note. This is quicker but harder to reproduce and easier to mis-map coefficients.
3. Change feature activation or refit models to use current MCHL1. This is excluded because the training support and independent datum/QC validation are inadequate.

For the scorecard, use the current archived `performance.json` and render its metrics plus empty 24-hour rows. Do not synthesize data or extend verification with estimates.

## Implementation calls

- Native execution in this session, following the user's explicit autonomous execution authorization.
- Audit coefficients are mapped through each artifact's active-column mask, including separate value and missingness-indicator columns.
- A horizon with no matured verifications is labeled pending; no metric is shown as zero.
