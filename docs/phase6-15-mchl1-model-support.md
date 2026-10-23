# Phase 6.15 — Frozen-model MCHL1 training support audit

**Status: MCHL1 remains shadow-only. No frozen model, feature gate, forecast, or prospective archive was changed.** This is a reproducible description of the committed Phase 5 training samples and Phase 6 frozen artifacts, not a new skill evaluation.

## Method and provenance

`python scripts/audit_mchl1_model_support.py` selects the Phase 5A rows with the canonical `_training_mask` and Phase 5B's committed calibration rows with the same target embargo and MAUL1-stage requirements used to fit its final multivariable models. It checks every reconstructed row count against the frozen model metadata before reporting results. MCHL1 predictors are counted separately for 6-, 24-, and 72-hour native-stage changes. Ridge value and missingness coefficients are mapped through each artifact's active-column mask; these are standardized target-change slopes in feet per training standard deviation.

The audit is pinned to `site/data/prospective/model-artifacts.json`, artifact SHA-256 `c98d96c83e80110aa03165929f6eb4355bae5a38e590e8599a79f63ae0652a72`. Training archives are `site/data/history/phase5a/features.csv.gz`, `site/data/history/phase5a/predictions.csv.gz`, and the Phase 5B model/report archives. The Phase 5 calibration window is 2016-01-01 through 2022-12-31 with the existing 72-hour target embargo.

## Availability in the final fit

Each cell gives observed / training rows and the observed percentage. All unavailable rows are median-imputed by the frozen transform; where the binary missingness feature varies, its standardized ridge slope is listed separately below.

| Frozen model | Horizon | Training rows | MCHL1 Δ6h | MCHL1 Δ24h | MCHL1 Δ72h |
|---|---:|---:|---:|---:|---:|
| Phase 5A MAUL1-only | 6h | 54,115 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5A MAUL1-only | 12h | 53,874 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5A MAUL1-only | 24h | 53,830 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5A coastal | 6h | 54,115 | 176 / 0.3252% observed; 99.6748% missing | 158 / 0.2920% observed; 99.7080% missing | 112 / 0.2070% observed; 99.7930% missing |
| Phase 5A coastal | 12h | 53,874 | 170 / 0.3156% observed; 99.6844% missing | 152 / 0.2821% observed; 99.7179% missing | 106 / 0.1968% observed; 99.8032% missing |
| Phase 5A coastal | 24h | 53,830 | 158 / 0.2935% observed; 99.7065% missing | 140 / 0.2601% observed; 99.7399% missing | 94 / 0.1746% observed; 99.8254% missing |
| Phase 5B coastal-tidal | 6h | 54,115 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5B coastal-tidal | 12h | 53,874 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5B coastal-tidal | 24h | 53,830 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5B full multivariable | 6h | 54,115 | 176 / 0.3252% observed; 99.6748% missing | 158 / 0.2920% observed; 99.7080% missing | 112 / 0.2070% observed; 99.7930% missing |
| Phase 5B full multivariable | 12h | 53,874 | 170 / 0.3156% observed; 99.6844% missing | 152 / 0.2821% observed; 99.7179% missing | 106 / 0.1968% observed; 99.8032% missing |
| Phase 5B full multivariable | 24h | 53,830 | 158 / 0.2935% observed; 99.7065% missing | 140 / 0.2601% observed; 99.7399% missing | 94 / 0.1746% observed; 99.8254% missing |

Thus, for models that include MCHL1, each MCHL1 predictor was missing in **99.6748%–99.8254%** of training rows. This is descriptive row coverage, not an independent-sample confidence interval: hourly training rows are strongly serially dependent. The HADS/IEM station-history record begins in December 2022, at the very end of this model-training period, consistent with the sparse observed support.

## Learned coefficients and interpretation

Each cell is `value coefficient / missingness-indicator coefficient` in feet of target change per training standard deviation. These are fitted standardized ridge slopes, not feature importance or independent validation.

| Model | Horizon | Δ6h feature | Δ24h feature | Δ72h feature |
|---|---:|---:|---:|---:|
| Phase 5A coastal | 6h | +0.000320 / −0.000680 | +0.000580 / +0.002302 | +0.000455 / −0.001622 |
| Phase 5A coastal | 12h | +0.000648 / +0.000471 | +0.001207 / +0.003043 | +0.000754 / −0.002651 |
| Phase 5A coastal | 24h | +0.002200 / −0.001307 | −0.001103 / +0.013221 | +0.000396 / −0.008259 |
| Phase 5B full multivariable | 6h | +0.000326 / −0.000112 | +0.000586 / +0.002408 | +0.000460 / −0.002540 |
| Phase 5B full multivariable | 12h | +0.000706 / +0.001154 | +0.001208 / +0.003539 | +0.000777 / −0.004187 |
| Phase 5B full multivariable | 24h | +0.002515 / −0.001356 | −0.001269 / +0.014841 | +0.000383 / −0.010297 |

The value coefficients range from approximately **−0.0013 to +0.0025 ft per training standard deviation**. Missingness-indicator coefficients range from approximately **−0.0103 to +0.0148 ft per standard deviation**. They are small coefficients on a highly regularized model scale, but coefficient size alone does not measure out-of-sample value or causal contribution. The fit saw very few observed MCHL1 rows, and no event-stratified or MCHL1 ablation study establishes that this signal improves predictions.

The inference distribution would change materially if present-day MCHL1 observations were admitted: the model learned predominantly from median-imputed MCHL1 inputs, with fewer than one in 300 training rows carrying an observation. A missingness indicator cannot substitute for adequate coverage of the value distribution. The current MCHL1 data remain unverified and excluded from model inputs; activating them now would be an unsupported training-to-inference shift.

## Consequence

- Phase 5A MAUL1-only and Phase 5B coastal-tidal contain no MCHL1 predictors and therefore cannot have learned an MCHL1 effect.
- Phase 5A coastal and Phase 5B full multivariable include the three MCHL1 changes, but their effective observed support is sparse and concentrated at the end of calibration.
- Do not claim that those models validated MCHL1 or its contribution. Do not activate the current MCHL1 feed, retrain, or alter frozen coefficients on this evidence.
- Keep MAUL1 native USGS 00065 distinct from the 4.0 ft NAVD88 threshold. No inference about the threshold follows from this training audit.

## Prospective baseline at the current archive snapshot

The committed `performance.json` snapshot used by PR #38 contained 12 verified forecasts per model at 6h and 8 per model at 12h. At 6h, persistence MAE/RMSE/bias were 0.0275/0.0341/−0.0171 ft; learned-model MAE ranged 0.0600–0.0753 ft. At 12h, persistence was 0.0438/0.0480/−0.0425 ft; learned-model MAE ranged 0.0507–0.0899 ft. Every learned model had higher MAE than persistence in these small, quiet-period samples. At 24h there were no matured verified forecasts. No ≥1.00-ft rapid rises or independent event groups had verified; POD at ≥0.25 ft was therefore undefined, while isolated 0.25-ft false alarms appeared for some models. These overlapping forecast samples do not support event skill claims or general model rankings.

The archive's 2026-10-23 07:32Z source capture contained 380 MCHL1 candidate observations; its 06:00Z completed bin was present, and the 6/24/72-hour native changes were −0.156/−0.171/−0.303 ft. They remained shadow-only and absent from the forecast feature vector. This demonstrates source availability and calculation only, not physical datum, provider QC, shared-source identity, or predictive benefit.

## Historical MCHL1 / USGS overlap status

PR #37's single Sep 1–5, 2026 probe **reported** 365 exact timestamp matches and 0.000-ft native differences at the matched times, including available 6/24/72-hour changes. This is one short period and the overlap can result from a shared upstream measurement stream; it does not validate two independent instruments. I attempted a separate Dec 20–25, 2022 query in this environment, but the egress proxy returned HTTP 403 for both providers before either request reached USGS or HADS, so no result is claimed for that period.

The overlap probe now supports multiple separated windows and stores exact source response bodies alongside SHA-256 hashes, request URLs, source-specific interval/gap summaries, exact-time offsets, half-window offset change, and raw provider qualifier counts. A hosted Actions run is needed to complete the additional-period measurements; until it returns usable raw artifacts, the only numeric overlap finding remains the reported single September 2026 result. HADS's 15-minute directory interval and operator identity do not certify sensor, gauge-zero, datum, QC semantics, or relationship to USGS 073802302.

## Limitations and next evidence

This audit does not quantify feature ablation on independent storm events, because the training overlap is sparse and the prospective archive has not yet verified any independent rise events. Rates and coefficients are descriptive; temporal dependence makes an ordinary binomial confidence interval inappropriate. A useful follow-up would evaluate frozen-model ablation on independently defined events after enough authentic prospective cases accrue, while separately completing HADS sensor/datum/QC and multiple-period USGS overlap research. Matching measurements would still not establish independent instrument validation.
