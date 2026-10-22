# Phase 5B methods and limitations

Phase 5B extends the Phase 5A retrospective native-stage hindcast using its committed feature and prediction tables and the already archived hourly data. It does not reacquire historical data. The target is MAUL1 USGS parameter 00065 in its native gage-height reference; no conversion to NAVD88 is attempted and the historical 4.0-ft NAVD88 threshold is not evaluated.

## Inputs and issue-time contract

An issue is a regular UTC hour. Predictor observations are the last completed hourly bin ending no later than the issue time. The six-hour, 72-hour and other feature differences require exact endpoints and the same declared unit and datum; no interpolation is used. The forecast target is indexed at `issue time + horizon`. Forecasts fit stage change from current MAUL1 stage and add that modeled change back to the current native stage. Phase 3B event intervals and Phase 4 classes are evaluation strata only.

The 2016–2022 calibration period and 2023-onward historical holdout match Phase 5A. Holdout results are a reused historical benchmark because those years have already been inspected. Forward CV validation blocks begin at least six days after each calendar-year boundary, and training targets end 72 hours before the boundary. Final holdout fits use calibration targets ending 72 hours before 2023. Every model uses train-only median imputation, standardization, and target clipping.

## Candidate models

The periodic-only candidate adds UTC 24-hour and 12.42-hour sine/cosine harmonics and MAUL1 causal history. A 14.765-day sine/cosine term is included only as an approximate spring-neap calendar proxy; it is not derived from station constituents. The coastal-tidal candidate adds completed NWCL1 same-datum residual changes, MDLL1 changes, and NWCL1 wind vectors. The full candidate adds completed DENL1 discharge/stage, MCHL1 supporting stages, and Phase 4 issue-time evidence states. Ridge penalties are selected from a small fixed grid using pooled forward-fold calibration MAE for each model and horizon. Phase 5A persistence, MAUL1-only, and coastal models remain comparators.

NOAA CO-OPS astronomical predictions in this archive are labeled by valid time and MLLW datum, but no archived capture/receipt time or issue-time availability ledger establishes that each value was genuinely available before historical issuance. They are not used by causal model selection or gating. A separately identified `maul1_astro_retrospective` candidate uses the prediction change between the completed issue bin and future target valid time after exact unit/datum compatibility checks. Its skill is a retrospective sensitivity only, not advance forecast skill. NOAA prediction coverage alone cannot establish availability or valid delivery lead time.

## Issue-time selection and verification

The selector uses only the absolute six-hour MAUL1 change available at issue time. On blocked forward calibration out-of-fold predictions it chooses between persistence below a threshold and the best causal advanced candidate above it. The threshold and candidate are fitted only from calibration OOF errors. Missing values fall back to persistence. No future rise labels enter forecast features or the selector. Outcome-defined rising and rapid-rise groups appear only in verification. Annual, seasonal, Phase 3B event, Phase 4 category, and issue-time model strata retain explicit counts. Seven-day moving-block bootstrap intervals account for temporal dependence more appropriately than independent-row formulas; Phase 3B event summaries group overlapping issue forecasts by event.

Central 80% symmetric empirical intervals use the calibration-period residual distribution (OOF residuals for new models; prequential calibration predictions for Phase 5A comparators). Holdout coverage, interval width, and rising-period undercoverage are reported without re-calibrating on holdout outcomes.

Post-2022 case illustrations are mechanically selected from the largest positive 24-hour observed changes with non-overlapping 72-hour issue windows. They are outcome-selected and retrospective, so they do not estimate real-time case-selection skill. August 2016 and Tropical Storm Beta 2020 remain calibration-era examples, not independent holdout verification.

## Limits and prospective verification

The 2023-onward evaluation has previously been inspected. Local harmonics are not a validated coastal tide model and NWCL1 phase is not assumed to transfer unchanged to MAUL1. NOAA prediction advance availability is unverified. Archive hourly bins do not preserve original receipt times, and source measurements may be provisional or incomplete. Empirical prediction intervals do not establish flood probabilities. No output is operational guidance.

A free prospective research study should freeze the code and candidate set, issue and archive predictions at predeclared UTC times, store every input with source and receipt timestamps, and score against future complete MAUL1 observations after a predeclared duration. Report all issued cases, missing-input behavior, persistence comparisons, rises missed, and grouped uncertainty. Do not integrate into PETSS-Plots or NWS workflows without a separate validation and authorization decision.
