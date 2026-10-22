# Phase 5A experimental water-level hindcast

MAUL1 stage 00065, ft, native gage-height reference (no NAVD88 conversion)

This is retrospective research evidence, not operational advice or a probability forecast. Models use only completed hourly bins at each issue time. The 2023 onward period is a temporally held-out verification set; calibration case studies are not independent tests.

## Holdout verification

| Horizon | Model | N (paired) | MAE (ft) | RMSE (ft) | Bias (ft) | MAE skill vs persistence | Skill 95% block interval |
|---:|---|---:|---:|---:|---:|---:|---|
| 6 h | persistence | 32429 | 0.1743 | 0.2028 | -0.0000 | 0.0 | [0.000, 0.000] |
| 6 h | stage_trend | 32429 | 0.1571 | 0.1882 | -0.0004 | 0.09897443971892173 | [0.089, 0.109] |
| 6 h | maul1_only | 32429 | 0.0933 | 0.1214 | 0.0019 | 0.464678496872147 | [0.446, 0.483] |
| 6 h | maul1_plus_river | 32429 | 0.0931 | 0.1210 | 0.0040 | 0.4658692153797863 | [0.447, 0.484] |
| 6 h | maul1_plus_coastal | 32429 | 0.0631 | 0.0841 | 0.0054 | 0.6381231742015744 | [0.625, 0.652] |
| 6 h | maul1_all | 32429 | 0.0641 | 0.0849 | 0.0126 | 0.632390014874622 | [0.619, 0.646] |
| 12 h | persistence | 32338 | 0.2415 | 0.2874 | -0.0001 | 0.0 | [0.000, 0.000] |
| 12 h | stage_trend | 32338 | 0.2351 | 0.2815 | -0.0002 | 0.026804952585307462 | [0.017, 0.036] |
| 12 h | maul1_only | 32338 | 0.1627 | 0.2113 | 0.0045 | 0.32656200770418353 | [0.304, 0.348] |
| 12 h | maul1_plus_river | 32338 | 0.1618 | 0.2101 | 0.0098 | 0.3299464083820449 | [0.308, 0.351] |
| 12 h | maul1_plus_coastal | 32338 | 0.1216 | 0.1602 | 0.0006 | 0.4963569940769318 | [0.478, 0.513] |
| 12 h | maul1_all | 32338 | 0.1223 | 0.1608 | 0.0128 | 0.4936751378480507 | [0.475, 0.511] |
| 24 h | persistence | 32297 | 0.2401 | 0.3208 | -0.0005 | 0.0 | [0.000, 0.000] |
| 24 h | stage_trend | 32297 | 0.2321 | 0.3127 | -0.0007 | 0.03339009409692373 | [0.021, 0.046] |
| 24 h | maul1_only | 32297 | 0.2151 | 0.2919 | 0.0107 | 0.10411164946469531 | [0.079, 0.128] |
| 24 h | maul1_plus_river | 32297 | 0.2156 | 0.2904 | 0.0211 | 0.10209197630989453 | [0.076, 0.126] |
| 24 h | maul1_plus_coastal | 32297 | 0.1910 | 0.2580 | -0.0177 | 0.20442053968922924 | [0.179, 0.230] |
| 24 h | maul1_all | 32297 | 0.1911 | 0.2574 | 0.0018 | 0.20414403263998115 | [0.179, 0.230] |

## Files

`summary.json`, `cv.json`, `verification.json`, `uncertainty.json`, `case-studies.json`, `models.json`, `provenance.json`, `predictions.csv.gz`, and `features.csv.gz` contain full machine-readable results and issue-level audit data.
