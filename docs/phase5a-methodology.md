# Phase 5A hindcast methods

## Scope and target

This is a retrospective research comparison of 6, 12, and 24 hour water-level point hindcasts for MAUL1. The target is station 07380215 parameter 00065 in feet using its native `gage height` reference. No conversion to NAVD88 is performed. Results are not operational forecasts, flood guidance, or probabilities of exceeding a threshold. No new observations are acquired.

## Issue-time information

The archive labels each hourly aggregate by its hour start. A forecast issued at time `t` uses the latest completed hourly bin labelled `t - 1 hour`. All changes use exact hourly endpoints, preserve each station's native datum, and are missing when an endpoint is unavailable or a datum changes. The predictor families are MAUL1 stage history, DENL1 discharge and stage, NWCL1 observed-minus-predicted same-hour residual and wind, MDLL1 and MCHL1 stage changes, and causal Phase 4 river/coastal present/unknown flags. MCHL1 datum is unverified and is used only for within-station differences. Phase 4's causal quality mode is applied. Retrospective quality findings and event labels are not predictors.

The comparison includes persistence, a bounded and shrunk MAUL1 trend forecast, and standardized ridge models for MAUL1-only, MAUL1 plus river context, MAUL1 plus coastal context, and all available context. Ridge imputation medians, scaling, missingness indicators, target clipping, and trend caps are estimated using training rows only. Every forecast is an anomaly relative to the latest MAUL1 stage, then added to that stage. Missing current MAUL1 stage means no forecast.

## Temporal design

Calibration covers archive years 2016–2022. Forward blocked annual folds from 2017 through 2022 select ridge penalties and trend settings by pooled calibration MAE. Calibration hindcasts are expanding monthly refits; parameter choices for a year only use forward folds completed before that year. The held-out period begins after the split seam: an issue is scored only when its entire 72-hour feature lookback starts at least 72 hours after 2023-01-01. Holdout models and parameters are frozen using calibration observations whose target times precede the split by the 72-hour embargo. No holdout outcome is used for fitting or selection.

Metrics are evaluated on paired issue/target rows shared by the methods at each horizon. They include MAE, RMSE, bias, and MAE skill relative to persistence. Skill intervals use deterministic 1,000-replicate seven-day moving-block resampling of the paired holdout sequence. Outcome-based rising/quiet groups and Phase 3B event windows are descriptive evaluation strata only. Case-study timelines show the four preselected Phase 3B periods; calibration cases are explicitly not independent holdout tests.

Symmetric empirical 80% intervals use the calibration 90th percentile absolute error and report empirical holdout coverage. These intervals are exploratory and are not calibrated probabilities. Missing predictors are retained with explicit missing indicators and per-row imputation counts. The issue-level feature and prediction tables preserve statuses and target exclusions for audit.

## Reproduction and limitations

Install `requirements-phase5a.txt` and run `python scripts/phase5a.py`. Results are written under `site/data/history/phase5a/`. `provenance.json` records the SHA-256 of every monthly input archive and the Phase 3B validation table. The hourly archive ends at its last genuinely observed bin; future grids are not treated as observations. The temporal holdout does not establish transfer to other stations, regimes, or future operating conditions.
