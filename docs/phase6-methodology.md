# Phase 6 prospective forecast verification

## Purpose and boundary

Phase 6 freezes the existing Phase 5A/5B estimators and tests them prospectively using observations captured from the established DENL1, NWCL1, MDLL1, MCHL1, and MAUL1 network. It does not tune models on prospective outcomes, use Phase 5B's unsuccessful gate, turn retrospective NOAA predictions into causal features without a pre-issue capture record, or make forecasts operational. MAUL1 gage height remains in its native datum; direct NAVD88 readings, if present, remain separate.

## Frozen inference

The artifact contains Phase 5A MAUL1-only and coastal models plus Phase 5B coastal+tide and full multivariable models for 6, 12, and 24 hours. It preserves feature order, coefficients, intercept, imputation medians, scaling arrays, missingness transformations, active columns, target clipping, interval width, source report and code hashes, and model version. Persistence is computed directly from the latest valid MAUL1 observation. Freezing must reproduce every eligible published holdout forecast within `1e-8 ft` before the artifact can be used.

## Issue-time observations and eligibility

The scheduled UTC workflow records its nominal slot and actual execution and issue times independently. All source retrievals finish before the actual issue time. Hourly inputs use only completed UTC bins; no interpolation or implicit carry-forward is allowed. The maximum age is 2 hours for the latest MAUL1 stage and 3 hours for other station inputs. A forecast cycle is eligible when that MAUL1 requirement is met; otherwise each model abstains and the attempt is still recorded. Stale, absent, rejected, or partial inputs remain explicit. The issue archive stores the transformed feature vector and immutable source snapshot with valid times, retrieval times, QC, datum, units, source identity, and hashes.

Each authentic issue is create-only and records all five model statuses at all three horizons, exact `valid_time = model_feature_anchor + horizon`; record actual issuance separately and calculate actual effective lead time, frozen model version/hash, target stage and interval bounds, and issue-time features. A rerun creates a separate actual issuance or audit attempt; it cannot replace an earlier file. Dispatch simulations are isolated from the authentic archive.

## Independent verification and metrics

Verification reads immutable issue records only after their valid times and observation bins have completed. Forecast and verification files are separate. Reprocessing identical observations is idempotent. A later correction creates a numbered verification revision and retains its predecessor. The dashboard reports prospective outcomes only from the archive, with issued/matured/verified and due-but-unverified counts, observation retrieval delay, error by MAUL1 input age, MAE, RMSE, bias, persistence comparisons, rise hits/misses/false alarms (0.25, 0.50, 1.00 ft), underforecast tails, intervals and event-level lead. A due-but-unverified target is not assigned a cause; it may reflect delayed or absent observation data. Overlapping forecasts are not treated as independent events; event skill is withheld when event counts are too small.

The intended event grouping is outcome-defined and fixed before prospective performance review: a qualifying event is a native-stage rise of at least 0.50 ft within 24 hours; qualifying observations with less than 24 hours between consecutive event windows belong to one event. Forecast event detection is the first archived forecast issued before the observed threshold time that predicts at least the same threshold within its matching horizon. Event lead is threshold time minus that forecast's actual issue time. These outcome labels do not enter model predictors. Event metrics remain suppressed until five independent groups have verified observations.

## Sources and workflow

Use USGS NWIS for MAUL1, DENL1, and MDLL1; NOAA CO-OPS station 8761927 for NWCL1 water level, prediction, and wind products; and the established IEM/NWS HADS feed for MCHL1. Keep MCHL1's native datum unverified and relative-change-only. USACE 85420/85420LA is never relabeled MCHL1. Preserve direct MAUL1 parameter 63160 NAVD88 observations separately from parameter 00065.

A free GitHub Actions workflow issues forecasts hourly on a fixed UTC schedule and verifies mature records in a serialized run. It also offers manual dispatch for simulations and, when explicitly selected, a genuine current-time issuance. Delayed runs use their actual issuance time and never backdate. Create-only records, per-run audit files, a shared concurrency group, and retry-safe Git pushes protect the archive. Successful forecast-data commits trigger the existing Pages deployment. The dashboard starts with an explicit no-issuance state rather than fabricated data.

## Limitations

Source outages, provisional or delayed observations, the unverified MCHL1 datum, the existing models' hourly calibration target, and small prospective event counts can limit inference. The 80% intervals are frozen historical intervals, not calibrated flood probabilities. Every output remains research-only and does not imply equivalence to a NAVD88 flood threshold.


### Phase 6.1 prospective timing clarification

Phase 5 models construct features at an exact UTC hour and predict the corresponding grid target at anchor plus 6, 12, or 24 hours. For future Phase 6 issuances, archive this model feature anchor explicitly. Keep actual issuance time distinct: the effective available lead is the grid target minus the actual issuance, and may be less than the nominal horizon when a scheduled job runs late. Do not backdate issuance or alter previously archived forecast objects, including the first authentic Phase 6 issue. All event lead-time evaluations must use actual issuance timestamps.
