# Phase 6.15 — Frozen-model MCHL1 training support audit

**Status: MCHL1 remains shadow-only. No frozen model, feature gate, forecast, or prospective archive was changed.** This is a reproducible description of the committed Phase 5 training samples and Phase 6 frozen artifacts, not a new skill evaluation.

## Method and provenance

`python scripts/audit_mchl1_model_support.py` selects the Phase 5A rows with the canonical `_training_mask` and Phase 5B's committed calibration rows with the same target embargo and MAUL1-stage requirements used to fit its final multivariable models. It checks every reconstructed row count against the frozen model metadata before reporting results. MCHL1 predictors are counted separately for 6-, 24-, and 72-hour native-stage changes. Ridge value and missingness coefficients are mapped through each artifact's active-column mask; these are standardized target-change slopes in feet per training standard deviation.

The audit is pinned to `site/data/prospective/model-artifacts.json`, artifact SHA-256 `c98d96c83e80110aa03165929f6eb4355bae5a38e590e8599a79f63ae0652a72`. Training archives are `site/data/history/phase5a/features.csv.gz`, `site/data/history/phase5a/predictions.csv.gz`, and the Phase 5B model/report archives. The Phase 5 calibration window is 2016-01-01 through 2022-12-31 with the existing 72-hour target embargo.

## Availability in the final fit

Each cell gives usable / training rows, after flagging extreme sentinel-derived changes, and the effective unavailable percentage. The archived table also labels some sentinel-derived changes as nonmissing; those rows are listed in parentheses and are not usable measurements. Remaining unavailable rows are median-imputed by the frozen transform.

| Frozen model | Horizon | Training rows | MCHL1 Δ6h | MCHL1 Δ24h | MCHL1 Δ72h |
|---|---:|---:|---:|---:|---:|
| Phase 5A MAUL1-only | 6h | 54,115 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5A MAUL1-only | 12h | 53,874 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5A MAUL1-only | 24h | 53,830 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5A coastal | 6h | 54,115 | 172 usable (176 reported; 4 sentinel); 0.3178% usable; 99.6822% unavailable | 154 usable (158 reported; 4 sentinel); 0.2846% usable; 99.7154% unavailable | 110 usable (112 reported; 2 sentinel); 0.2033% usable; 99.7967% unavailable |
| Phase 5A coastal | 12h | 53,874 | 166 usable (170 reported; 4 sentinel); 0.3081% usable; 99.6919% unavailable | 148 usable (152 reported; 4 sentinel); 0.2747% usable; 99.7253% unavailable | 104 usable (106 reported; 2 sentinel); 0.1930% usable; 99.8070% unavailable |
| Phase 5A coastal | 24h | 53,830 | 154 usable (158 reported; 4 sentinel); 0.2861% usable; 99.7139% unavailable | 136 usable (140 reported; 4 sentinel); 0.2526% usable; 99.7474% unavailable | 92 usable (94 reported; 2 sentinel); 0.1709% usable; 99.8291% unavailable |
| Phase 5B coastal-tidal | 6h | 54,115 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5B coastal-tidal | 12h | 53,874 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5B coastal-tidal | 24h | 53,830 | Not a predictor | Not a predictor | Not a predictor |
| Phase 5B full multivariable | 6h | 54,115 | 172 usable (176 reported; 4 sentinel); 0.3178% usable; 99.6822% unavailable | 154 usable (158 reported; 4 sentinel); 0.2846% usable; 99.7154% unavailable | 110 usable (112 reported; 2 sentinel); 0.2033% usable; 99.7967% unavailable |
| Phase 5B full multivariable | 12h | 53,874 | 166 usable (170 reported; 4 sentinel); 0.3081% usable; 99.6919% unavailable | 148 usable (152 reported; 4 sentinel); 0.2747% usable; 99.7253% unavailable | 104 usable (106 reported; 2 sentinel); 0.1930% usable; 99.8070% unavailable |
| Phase 5B full multivariable | 24h | 53,830 | 154 usable (158 reported; 4 sentinel); 0.2861% usable; 99.7139% unavailable | 136 usable (140 reported; 4 sentinel); 0.2526% usable; 99.7474% unavailable | 92 usable (94 reported; 2 sentinel); 0.1709% usable; 99.8291% unavailable |

Thus, for models that include MCHL1, **99.6822%–99.8291%** of training rows were either unavailable or sentinel-contaminated for a given predictor. This is descriptive row coverage, not an independent-sample confidence interval: hourly training rows are strongly serially dependent. The HADS/IEM station-history record begins in December 2022, at the very end of this model-training period, consistent with the sparse support.

### Sentinel contamination in the frozen training table

The archived HADS body contains `HGIRGZZ=9999999.0` on 12 rows in 2022-12-20 through 2022-12-25. This finite numeric missing-value sentinel was treated as stage by the historical parser and produced MCHL1 delta features near **±5,000,000 ft**. In the frozen calibration rows, four such rows occur in each Δ6h and Δ24h predictor and two in Δ72h for both MCHL1-bearing model families and all three forecast horizons. They were counted as observed by the original fit and have not been edited out of the frozen training archive or artifact.

The MCHL1 coefficients below therefore describe the fitted artifacts including these contaminated rows. Their small standardized values do not show that sentinel cases had low leverage, nor do they establish a clean MCHL1 relationship. The live parser now rejects the observed sentinel for future data; this does not repair or change any historical training data or frozen model.

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

The artifact value coefficients range from approximately **−0.0013 to +0.0025 ft per training standard deviation**. Missingness-indicator coefficients range from approximately **−0.0103 to +0.0148 ft per standard deviation**. These are coefficients of fits whose MCHL1 inputs included the sentinel-derived outliers above; coefficient magnitude alone cannot establish leverage, out-of-sample value, or causal contribution. No event-stratified or clean-input MCHL1 ablation establishes predictive benefit.

The inference distribution would change materially if present-day MCHL1 observations were admitted: the model learned predominantly from median-imputed MCHL1 inputs, with fewer than one in 300 training rows carrying an observation. A missingness indicator cannot substitute for adequate coverage of the value distribution. The current MCHL1 data remain unverified and excluded from model inputs; activating them now would be an unsupported training-to-inference shift.

## Consequence

- Phase 5A MAUL1-only and Phase 5B coastal-tidal contain no MCHL1 predictors and therefore cannot have learned an MCHL1 effect.
- Phase 5A coastal and Phase 5B full multivariable include the three MCHL1 changes, but usable support is sparse, concentrated at the end of calibration, and contaminated by HADS missing-value sentinel arithmetic in a few fitted rows.
- Do not claim that those models validated MCHL1 or its contribution. Do not activate the current MCHL1 feed, retrain, or alter frozen coefficients on this evidence.
- Keep MAUL1 native USGS 00065 distinct from the 4.0 ft NAVD88 threshold. No inference about the threshold follows from this training audit.

## Prospective baseline at the current archive snapshot

The committed `performance.json` snapshot used by PR #38 contained 12 verified forecasts per model at 6h and 8 per model at 12h. At 6h, persistence MAE/RMSE/bias were 0.0275/0.0341/−0.0171 ft; learned-model MAE ranged 0.0600–0.0753 ft. At 12h, persistence was 0.0438/0.0480/−0.0425 ft; learned-model MAE ranged 0.0507–0.0899 ft. Every learned model had higher MAE than persistence in these small, quiet-period samples. At 24h there were no matured verified forecasts. No ≥1.00-ft rapid rises or independent event groups had verified; POD at ≥0.25 ft was therefore undefined, while isolated 0.25-ft false alarms appeared for some models. These overlapping forecast samples do not support event skill claims or general model rankings.

The archive's 2026-10-23 07:32Z source capture contained 380 MCHL1 candidate observations; its 06:00Z completed bin was present, and the 6/24/72-hour native changes were −0.156/−0.171/−0.303 ft. They remained shadow-only and absent from the forecast feature vector. This demonstrates source availability and calculation only, not physical datum, provider QC, shared-source identity, or predictive benefit.

## Historical MCHL1 / USGS overlap status

Two new five-day UTC windows were fetched through GitHub Actions and their exact provider bodies are committed under `site/data/research/mchl1-usgs-overlap/`. `comparison.json` records the response hashes, request URLs, valid counts, interval/missingness summaries, sentinel and qualifier counts, exact-time differences, and change comparisons; it can be reproduced offline with `scripts/probe_mchl1_usgs_overlap.py --raw-input-dir ...`.

| UTC window, end exclusive | MCHL1 usable / expected | USGS usable / expected | Exact matched timestamps | Native stage difference at matched times | Matched 6h / 24h / 72h changes |
|---|---:|---:|---:|---:|---:|
| 2022-12-20 to 2022-12-25 | 373 / 480 (77.7083%) | 462 / 480 (96.25%) | 373 | Median, mean, and full range 0.000 ft | 337 / 269 / 94; all change differences 0.000 ft |
| 2024-11-14 to 2024-11-19 | 479 / 480 (99.7917%) | 479 / 480 (99.7917%) | 479 | Median, mean, and full range 0.000 ft | 454 / 382 / 191; all change differences 0.000 ft |

In each window every usable MCHL1 timestamp had an exact USGS timestamp and identical value. In 2022, MCHL1 had a 60-minute maximum valid-data gap and 12 `9999999.0` missing sentinels; USGS had a 60-minute maximum gap and 18 missing expected quarter-hour slots. In 2024 each usable series had one missing slot and a 30-minute maximum interval. The largest valid adjacent 15-minute stage change was identical in the paired series (0.27 ft in 2022 and 0.07 ft in 2024). Median offset did not shift between the first and second halves of either window. HADS response CSVs contained no QC/qualifier column; USGS raw IV rows carried qualifier `A` throughout the returned query, whose formal operational meaning is not inferred here.

The exact identity across all 852 usable pairs and identical changes is strong evidence that the two products may share an upstream observation stream, but it cannot establish whether there are two instruments, the same sensor, or a provider copy. These short samples do not establish long-term gauge-zero stability, a vertical-datum crosswalk, instrument replacement history, or QC independence. The 2022 match count is limited by MCHL1 coverage; a zero difference is not independent instrument validation.

### Authoritative station metadata and remaining gaps

The [NWS HADS LIX directory](https://hads.ncep.noaa.gov/hsas/LIX_dcps.shtml) identifies **MCHL1 / DCP CE678A12** as Pass Manchac near Highway 51 with stage (`HG`) reporting. [IEM's LA_DCP history](https://mesonet.agron.iastate.edu/sites/networks.php?network=LA_DCP&station=MCHL1) lists the MCHL1 station/product from 2022-12-20, and archived RRSLIX SHEF reports show `HGIRG/DIN15` reports. This supports the station code, approximate location, and 15-minute product cadence, but the records retrieved here do not provide a sensor serial number, installation/replacement log, datum benchmark, gauge-zero history, or HADS QC flag definition. The two overlap bodies show no HADS qualifier columns.

[USGS NWIS site metadata](https://waterservices.usgs.gov/nwis/site/?format=rdb&sites=073802302) describes 073802302 as “Pass Manchac nr. Lake Maurepas, LA”; its NWIS IV response identifies parameter 00065 as “Gage height, feet,” and reports site coordinates near the HADS location. The USGS site's documented gauge-zero/datum information (including its own −0.18 ft NAVD88 datum reference in site metadata) applies only to that USGS station; it is not a conversion for HADS MCHL1. USACE stations [85420](https://rivergages.mvr.usace.army.mil/WaterControl/stationinfo2.cfm?sid=85420) and [85420LA](https://rivergages.mvr.usace.army.mil/WaterControl/stationinfo2.cfm?sid=85420LA) are separate station identifiers in the same Pass Manchac area. Available USACE station records do not document that either is the HADS DCP, USGS 073802302 instrument, or a datum crosswalk between them. Do not equate station names or proximity with sensor identity.

PR #37's separate Sep 1–5, 2026 probe **reported** 365 exact matches and 0.000-ft differences, but its raw response was not independently reanalyzed here. Taken together, the reported 2026 sample and the two archived raw periods support near-identical reported data products in these snapshots. They do not establish independent instruments or physical/datum continuity. All results remain diagnostic-only and forecast-ineligible.

## Limitations and next evidence

This audit does not quantify feature ablation on independent storm events, because the training overlap is sparse and the prospective archive has not yet verified any independent rise events. Rates and coefficients are descriptive; temporal dependence makes an ordinary binomial confidence interval inappropriate. A useful follow-up would evaluate frozen-model ablation on independently defined events after enough authentic prospective cases accrue, while separately completing HADS sensor/datum/QC and multiple-period USGS overlap research. Matching measurements would still not establish independent instrument validation.
