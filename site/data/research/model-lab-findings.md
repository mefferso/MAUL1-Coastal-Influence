# Model Lab findings

**Research / Shadow Evaluation / Not Operational.**
**Retrospective / Development Evidence.** The 2023 onward holdout has already been inspected and is not an independent prospective test.

## Historical challenger results

The bounded damped-trend challenger used only the latest completed MAUL1 6-hour change. Settings were selected using nested forward calibration folds ending before each validation block; the final settings were frozen before applying them to the reused 2023+ historical benchmark. These are valid-time hindcasts; source receipt-time availability is not archived.

| Horizon | Paired n | Persistence MAE | Challenger MAE | Challenger skill vs persistence | Challenger MAE − persistence | Challenger MAE − MAUL1-only | Improvement vs MAUL1-only 95% block interval | Beats both? |
|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 6 h | 32,475 | 0.1742 ft | 0.1721 ft | 0.0124 | -0.0022 ft | 0.0787 ft | -0.0838 to -0.0735 ft | No |
| 12 h | 32,445 | 0.2415 ft | 0.2443 ft | -0.0116 | 0.0028 ft | 0.0814 ft | -0.0873 to -0.0754 ft | No |
| 24 h | 32,406 | 0.2403 ft | 0.2358 ft | 0.0184 | -0.0044 ft | 0.0204 ft | -0.0260 to -0.0151 ft | No |

Positive MAE differences mean the challenger is worse.

## Reproduced model benchmark

These five methods were compared on the same eligible rows within each horizon after regenerating the Phase 5A and Phase 5B reports into temporary directories. The 2023+ period is reused historical evidence.

| Model | 6h MAE (ft) / skill | 12h MAE (ft) / skill | 24h MAE (ft) / skill |
|---|---:|---:|---:|
| Persistence | 0.1742 / 0.0% | 0.2415 / 0.0% | 0.2403 / 0.0% |
| Phase 5A MAUL1-only | 0.0934 / 46.4% | 0.1629 / 32.5% | 0.2154 / 10.3% |
| Phase 5A coastal | 0.0631 / 63.8% | 0.1218 / 49.6% | 0.1911 / 20.4% |
| Phase 5B coastal + tidal | 0.0626 / 64.1% | 0.1219 / 49.5% | 0.1902 / 20.8% |
| Phase 5B full multivariable | 0.0638 / 63.4% | 0.1223 / 49.4% | 0.1911 / 20.4% |

## Predictor-family ablations

Same-row MAE deltas below compare each Phase 5A/5B family with MAUL1-only; negative values improve MAE. The 2023+ holdout is reused development/evaluation evidence.

| Horizon | Model family | Paired n | MAE (ft) | Δ MAE vs MAUL1-only (ft) |
|---:|---|---:|---:|---:|
| 6 h | MAUL1-only | 32,475 | 0.0934 | +0.0000 |
| 6 h | MAUL1 + DENL1 river | 32,475 | 0.0931 | -0.0002 |
| 6 h | MAUL1 + coastal observations | 32,475 | 0.0631 | -0.0303 |
| 6 h | MAUL1 + all Phase 5A context | 32,475 | 0.0641 | -0.0293 |
| 6 h | MAUL1 + coastal + UTC harmonics | 32,475 | 0.0626 | -0.0307 |
| 6 h | Full multivariable | 32,475 | 0.0638 | -0.0295 |
| 6 h | NOAA future-valid retrospective sensitivity † | 32,475 | 0.0894 | -0.0039 |
| 12 h | MAUL1-only | 32,445 | 0.1629 | +0.0000 |
| 12 h | MAUL1 + DENL1 river | 32,445 | 0.1621 | -0.0008 |
| 12 h | MAUL1 + coastal observations | 32,445 | 0.1218 | -0.0412 |
| 12 h | MAUL1 + all Phase 5A context | 32,445 | 0.1224 | -0.0405 |
| 12 h | MAUL1 + coastal + UTC harmonics | 32,445 | 0.1219 | -0.0411 |
| 12 h | Full multivariable | 32,445 | 0.1223 | -0.0406 |
| 12 h | NOAA future-valid retrospective sensitivity † | 32,445 | 0.1561 | -0.0068 |
| 24 h | MAUL1-only | 32,406 | 0.2154 | +0.0000 |
| 24 h | MAUL1 + DENL1 river | 32,406 | 0.2159 | +0.0005 |
| 24 h | MAUL1 + coastal observations | 32,406 | 0.1911 | -0.0243 |
| 24 h | MAUL1 + all Phase 5A context | 32,406 | 0.1913 | -0.0242 |
| 24 h | MAUL1 + coastal + UTC harmonics | 32,406 | 0.1902 | -0.0253 |
| 24 h | Full multivariable | 32,406 | 0.1911 | -0.0243 |
| 24 h | NOAA future-valid retrospective sensitivity † | 32,406 | 0.2157 | +0.0002 |

### Phase 6 qualifying-rise groups (physical independence unproven)

The existing Phase 6 rule groups outcome-defined 24-hour rises ≥0.50 ft when qualifying target times are no more than 24 hours apart. These target-time groups are not established independent hydrologic events. Lead is to the first qualifying verification target, not physical onset.

| Model | Grouped rises (not proven independent) | Detected / missed | Detection fraction | Median lead to first qualifying verification target |
|---|---:|---:|---:|---:|
| Persistence | 109 | 0 / 109 | 0.0% | — |
| Phase 5A MAUL1-only | 109 | 1 / 108 | 0.9% | 20.0 h |
| Phase 5A coastal | 109 | 26 / 83 | 23.9% | 12.5 h |
| Phase 5B coastal + tidal | 109 | 28 / 81 | 25.7% | 11.0 h |
| Phase 5B full multivariable | 109 | 28 / 81 | 25.7% | 12.0 h |
| Bounded damped-trend challenger | 109 | 0 / 109 | 0.0% | — |

The 24-hour trend challenger flagged **0** observed ≥0.50 ft target rises and missed **1,859** such overlapping target windows. These are correlated hourly windows; grouped event metrics are reported separately. The candidate did not beat MAUL1-only at 6, 12, or 24 hours (6h: 0.1721 vs 0.0934 ft; 12h: 0.2443 vs 0.1629 ft; 24h: 0.2358 vs 0.2154 ft). **No challenger is promoted.**

† NOAA future-valid prediction is retrospective-only without capture-time evidence; it is not an eligible causal feature.

The report JSON includes paired MAE for persistence, MAUL1-only, river-only addition, coastal addition, all Phase 5A families, causal harmonic/tidal experiments, and full multivariable models. Future-valid-time NOAA astronomical values are explicitly marked retrospective-only because archive capture times are unavailable. MCHL1 remains context-only in historic reports and is excluded from this challenger.

## Events and failure diagnostics

MAUL1 qualifying event rows are grouped by the existing Phase 3B event IDs. Hourly overlapping forecasts within one group are not independent sample units. Underforecast tails, quiet/falling conditions, high DENL1 flow, NWCL1 residual/wind conditions, MDLL1 context, and 24-hour threshold alert episodes are available in the compact report. Event windows are outcome-defined verification strata, not the physical onset time of a rise.

## Reproduction and limitations

Phase 5A/5B baseline parity: **matched**. The original scripts were directed to temporary output directories and did not rewrite historical records. All sources and code are hashed in `site/data/research/model-lab.json`.

Historical findings do not establish prospective skill. Original source receipt times are missing, so hourly valid-time bins cannot prove real-time availability. The 2023+ period was previously inspected. Case studies were selected algorithmically from those same reused outcomes. Provisional/quality limitations remain those of the source archive. No challenger was connected to Phase 6 issuance; a new, isolated, prospective shadow study is required before any operational interpretation.

## Reproduce

```sh
mkdir -p /tmp/maul1-reproduce/phase5a /tmp/maul1-reproduce/phase5b
python scripts/phase5a.py --root . --outdir /tmp/maul1-reproduce/phase5a
python scripts/phase5b.py --root . --out /tmp/maul1-reproduce/phase5b
python scripts/model_lab.py --root . --reproduction-dir /tmp/maul1-reproduce
```
