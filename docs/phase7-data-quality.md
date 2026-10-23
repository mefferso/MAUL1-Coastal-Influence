# Phase 7 historical data quality and clean experiment

## Status and scope

Phase 7 adds a separate, reproducible research copy of the archived hourly input series. Original hourly archives, Phase 5A/5B datasets, frozen model artifacts, and authentic prospective records remain unchanged. The cleaner rejects only machine-identifiable non-finite values and the established MCHL1 HADS missing sentinel, including values contaminated when a sentinel was averaged into an hourly bin. It does not clip statistical outliers or large but finite values from the other stations.

Reproduce the data audit and cleaned copy with:

```sh
python scripts/phase7_data.py --input site/data/history/hourly \
  --output work/phase7/cleaned-hourly --summary work/phase7/data-audit.json
```

Rebuild the Phase 5A retrospective candidate against that separate clean copy with:

```sh
python scripts/phase7_experiment.py --workdir work/phase7 \
  --outdir work/phase7/results
```

The Phase 5A estimator, feature definitions, training/holdout seam, 72-hour embargo, and issue-time bin convention are reused unchanged. The 2023-onward result is a previously inspected historical benchmark, not a pristine independent test. The experiment is retrospective and forecast-ineligible.

## Archive audit findings

The source snapshot has 130 monthly hourly files, January 2016 through October 2026, containing 4,137,183 station/variable rows. The archive is an hourly aggregation, not the original observation receipt log. Measured hourly series are timestamp-unique. The hourly grid is not proof of continuous usable observations: each series has longer periods with no valid value, and MCHL1 also has entirely unrecorded hours. The archive horizon includes empty future bins; those bins are missing and are not treated as observations.

| Series | Grid slots | Usable | Coverage | Longest gap between usable observations | Finite input range | Start |
|---|---:|---:|---:|---:|---:|---|
| DENL1 stage | 94,968 | 94,478 | 99.48% | 134 h | 9.555 to 46.2 ft | 2016-01 |
| DENL1 discharge | 94,968 | 94,645 | 99.66% | 2 h | 294.25 to 266,000 cfs | 2016-01 |
| MAUL1 stage | 94,968 | 87,655 | 92.30% | 837 h | -0.6 to 7.19 ft | 2016-01 |
| MDLL1 stage | 92,064 | 90,953 | 98.79% | 433 h | -2.01 to 6.385 ft | 2016-05 |
| NWCL1 water | 94,968 | 94,501 | 99.51% | 193 h | -1.936 to 5.986 ft | 2016-01 |
| MCHL1 stage | 34,344 | 30,684 | 89.34% | 1,527 h | -1.49 to 9,999,999.0 ft before cleaning | 2022-12 |

MCHL1 has 33,600 timestamped rows and 744 unrecorded hourly slots in its December 2022–October 2026 span; 2,895 of its recorded rows are explicitly missing before applying the additional sentinel cleaning.

The MCHL1 archive contains **21 invalid hourly stage values**: two exact `9999999.0` sentinels and 19 near-five-million-foot hourly means produced by averaging a sentinel with valid reports. There are also **206** MCHL1 derived stage-change rows with magnitude at least one million feet; these are sentinel arithmetic, not hydrology. The archived Phase 4 quality report independently recorded **594 adjacent MCHL1 stage jumps**, all approximately 9,999,996–9,999,999 ft. They are repeated pairwise jump flags and must not be read as 594 distinct bad observations.

Across the same hourly archive, finite ranges for DENL1, MAUL1, MDLL1 and NWCL1 observed water remain within the broad ranges shown above. Those ranges alone cannot validate sensors, and no hard plausibility thresholds were imposed. The existing quality report has thousands of NWCL1/NWCL1-NDBC gust-jump flags (3,199 and 2,928); gust is not stage and these flags are retained for provider-level review rather than treated as proof of invalid records.

The separate cleaner marks the 21 MCHL1 contaminated stage rows and 206 derived changes missing while retaining row timestamps, units, datum labels, coverage, source labels, and explicit cleaning reasons. It preserves all original monthly input SHA-256 values in the audit output. No historical MCHL1 readings are converted to MAUL1 datum or to NAVD88.

## Timestamp, source and issuance-time constraints

The historical feature engine indexes hourly bins by their UTC start and uses only the last completed bin (`issue time - 1 hour`), with exact endpoint differences and no interpolation. The MAUL1 target remains USGS 00065 native gage height. This is a valid-time causality rule; the historical archives lack original source retrieval/receipt timestamps, so they cannot establish that each historical predictor had actually arrived before its modeled issuance. That is a material limitation for operational interpretation.

The hourly table labels its source as derived monthly hourly aggregation. That field does not preserve all underlying provider response bodies, QC qualifier semantics, or sensor changes. Timestamp and native datum alignment are checked by the existing feature engine; datum changes make a difference unavailable. Same-station changes are not cross-station elevation conversions.

## Effect on historical training

Before cleaning, the archived Phase 5A feature table has 61,367 calibration-era issue rows. MCHL1 sentinel arithmetic appears in 10 predictor cells: four Δ6h values, four Δ24h values and two Δ72h values. Phase 6.15 reconstructed each frozen horizon's actual training mask and found these contamination rows in the MCHL1-bearing Phase 5A coastal and Phase 5B full models. They were not silently removed from the originals. Both model families have under 0.32% usable MCHL1 feature support, and the other frozen model families do not include MCHL1.

Run the cleaned Phase 5A model only as a side-by-side retrospective sensitivity. Its candidate coefficients and verification must not be interpreted as new prospective skill. This single correction cannot validate MCHL1: most of the MCHL1 series begins after the training seam, historical coverage is sparse before the seam, no independent sensor/datum/QC evidence is established, and the holdout is already inspected. MCHL1 remains forecast-ineligible and shadow-only.

### Cleaned-retraining sensitivity

Phase 5A was refit unchanged with only the cleaned archive substituted. The split, embargo, rows, target, and candidate predictors stayed the same. Persistence, MAUL1-only, and MAUL1-plus-river results were numerically unchanged. The MCHL1-bearing coastal and full candidates changed. On the already inspected 2023-onward holdout, MAE increased in all horizons:

| Horizon | Model | Original archive MAE (ft) | Cleaned MAE (ft) | Clean minus original (ft), 95% 7-day block interval | Common issue rows |
|---:|---|---:|---:|---:|---:|
| 6 h | MAUL1 + coastal | 0.0631 | 0.0670 | +0.0039 [0.0033, 0.0046] | 32,429 |
| 6 h | Full, including MCHL1 | 0.0641 | 0.0676 | +0.0035 [0.0028, 0.0042] | 32,429 |
| 12 h | MAUL1 + coastal | 0.1216 | 0.1247 | +0.0030 [0.0024, 0.0036] | 32,338 |
| 12 h | Full, including MCHL1 | 0.1223 | 0.1253 | +0.0030 [0.0025, 0.0035] | 32,338 |
| 24 h | MAUL1 + coastal | 0.1910 | 0.1942 | +0.0032 [0.0019, 0.0043] | 32,297 |
| 24 h | Full, including MCHL1 | 0.1911 | 0.1949 | +0.0038 [0.0025, 0.0050] | 32,297 |

Intervals are exploratory paired moving-block resamples of the same reused holdout (1,000 replicates, 168-hour blocks, seed 20261023). Thousands of consecutive issue rows overlap each event and are not independent evidence. The models continue to beat persistence in overall retrospective MAE; cleaning did not improve them.

Outcome-defined rising rows tell a mixed story. For target rise at least the calibration 90th percentile, the cleaned coastal/full models have slightly lower MAE than the original fits (6 h n=3,287: coastal 0.0870 to 0.0778 ft, full 0.0818 to 0.0750 ft; 12 h n=6,314: 0.1529 to 0.1470 and 0.1452 to 0.1427 ft; 24 h n=5,509: 0.3250 to 0.3123 and 0.3099 to 0.3060 ft). For issue-time rapid-rise rows (six-hour change at or above the calibration q90 of 0.275 ft), cleaned-model MAE is worse at every horizon (6 h n=2,112: coastal 0.0664 to 0.0801 ft, full 0.0676 to 0.0819 ft; 12 h n=2,111: 0.1297 to 0.1393 and 0.1336 to 0.1421 ft; 24 h n=2,115: 0.1833 to 0.1929 and 0.1863 to 0.1966 ft). Both strata are hourly, overlapping issue rows; the first uses future outcomes and is evaluation-only, while the second describes water already rising at issuance. These comparisons do not demonstrate earlier warning or independent-event skill.

The change is consistent with a small set of contaminated calibration rows influencing fitted MCHL1-bearing candidates, but it does not establish that correcting MCHL1 improves generalization. The observed overall holdout deterioration and opposing rise-stratum changes argue against promoting the cleaned fit. Keep frozen Phase 5 models as benchmarks and wait for a predeclared, independent event evaluation.

## Data validation requirements that remain open

- Recover the original provider observations and their retrieval/QC metadata for source-level reconciliation, especially all historical HADS sentinel and gap periods.
- Resolve HADS/USGS instrument identity, physical datum, gauge-zero continuity, and revisions using agency maintenance/benchmark records.
- Establish historical source receipt time if issuance-time availability is to be claimed.
- Build clean forward-chaining event evaluation only after predictors have sufficient pre-event coverage; do not use retrospective event class as a model feature.
- Keep coastal/river/mixed attribution unknown where independent forcing evidence is absent. Current archived samples do not support an operational lead-time or coastal-causation claim.
