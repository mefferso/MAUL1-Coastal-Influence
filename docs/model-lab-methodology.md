# Model Lab methodology and predeclared challenger protocol

**Status:** Retrospective research / development evidence only. It is not prospective verification, an operational forecast, a warning product, or a probability forecast.

## Data and baseline reproduction

The Lab consumes only the committed 2016–2026 hourly valid-time archive, Phase 5A issue-feature and hindcast tables, Phase 5B hindcast tables, and their published methodology. Before computing new results, run the existing Phase 5A and Phase 5B programs to temporary directories and compare their deterministic score summaries with the committed results. Never write regenerated hindcasts into the source archive.

MAUL1 is USGS station 07380215 parameter 00065 in feet and native gage-height datum. No NAVD88 conversion or 4.0 ft NAVD88 threshold is used. Parameter 63160, future valid-time NOAA prediction values, and unverified MCHL1 stage levels are excluded from the challenger. The hourly archive preserves valid times but not original source receipt times. A completed bin at `issue_time - 1 hour` is the best available valid-time approximation, not proof that it was received before an actual historical issuance. The findings are therefore not evidence of real-time availability.

The 2023 onward holdout is reused historical development/evaluation evidence: it has already been inspected in prior research and is not a pristine independent test. All comparisons use common issue/target rows and observed outcomes. Missing forecasts are abstentions and are excluded from paired model scores, with eligible counts disclosed; they are never scored as zero error.

## Frozen experiment protocol

1. Reproduce the published Phase 5A and Phase 5B benchmark summaries from their original scripts into temporary output paths. Require all reported `n`, MAE, RMSE, bias, and persistence skill values to match committed summaries within `1e-8`.
2. Evaluate one new, small challenger: a bounded damped MAUL1 trend. It uses only the completed issue-time MAUL1 6-hour change and current native MAUL1 stage. Prediction is current stage plus `horizon × shrink × clip(change_6h / 6, -cap, +cap)`. It has no external predictor, outcome label, or future valid-time input.
3. The fixed hyperparameter menu is window-independent (6-hour change), shrink `(0.10, 0.25, 0.50, 1.00)`, and slope cap in ft/hour `(0.01, 0.025, 0.05, 0.10)`. The menu and metric are frozen before evaluating challenger holdout scores. Within calibration years 2017–2022, each year uses only targets ending at least 72 hours before its validation year; its settings are selected using earlier completed forward folds only. Validation begins 144 hours after January 1 to provide the established 72-hour lookback plus 72-hour target purge. For 2017, before any fold exists, use the predeclared conservative default shrink `0.25`, cap `0.05 ft/hour`. The final challenger setting is the lowest pooled MAE across calibration forward folds. Holdout uses the selected setting without refitting or tuning.
4. Report the existing persistence, Phase 5A MAUL1-only/coastal, and Phase 5B coastal+tide/full models on identical cases with MAE, RMSE, bias, persistence skill, seven-day moving-block uncertainty versus both persistence and MAUL1-only, annual and seasonal scores, event/rise error, and predictor-availability counts. Outcome-defined rises are verification strata only. Overlapping hourly cases are clustered by the existing independent Phase 3B event IDs where applicable.
5. Use a deterministic 1,000-replicate seven-day moving-block bootstrap for paired MAE differences. The model is a historical challenger only; it is not added to Phase 6 artifacts, issuance streams, or archives. Promotion requires beating persistence and MAUL1-only in paired MAE, robustness across years and independent event groups, uncertainty excluding no improvement, adequate coverage, and a separately authorized prospective shadow experiment. Failure to meet any criterion is reported as no promotion.

## Regime definitions

- **Qualifying event:** a row assigned by the existing Phase 3B independent event catalog; counts and metrics are grouped by event ID. The catalog's event windows are not physical onset labels.
- **Phase 6 qualifying rise group:** at the 24-hour horizon, an outcome target with a native-stage rise of at least `0.50 ft`; target times within 24 hours are merged. Detection lead is measured to the first qualifying verification target, never interpreted as physical rise onset. Event skill is withheld below five groups.
- **Quiet/falling target:** observed target stage is at or below the latest issue-time MAUL1 stage. This is a retrospective verification stratum.
- **High DENL1 flow:** issue-time log discharge at or above its 2016–2022 calibration 90th percentile.
- **NWCL1 setup:** issue-time residual in feet relative to MLLW is at least `0.50 ft`; it is not compared with MAUL1 native gage height.
- **NWCL1 wind:** issue-time archived wind-vector magnitude is at least `5 knots`; original receipt-time availability is unknown.
- **MDLL1 rising context:** completed 24-hour MDLL1 stage change is at least `0.10 ft`; it is a within-station contextual stratum, not a cross-station water-level conversion.

These screens describe covariate conditions and outcomes in the historical archive. They do not establish physical causation or forecast availability. Phase 4 pathway labels and MAUL1 rise outcomes never enter challenger inputs.

## Provenance and interpretation

The generated report records source code and data SHA-256 hashes, archive time range, counts, missingness, exact hyperparameters, folds, and reproduction parity. Historical case selection is algorithmic and based on forecast errors/outcomes, so case plots are illustrations, not an independent evaluation set. No NOAA astronomical valid-time predictions are treated as known at historical issue time. MCHL1 remains excluded because its datum and quality support are unresolved. All charts are labeled **Retrospective / Development Evidence**.
