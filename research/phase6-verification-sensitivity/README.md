# Phase 6 retrospective verification matching sensitivity

Research-only comparison. Original verification revisions and `performance.json` are unchanged.

- Authentic issues: 42
- Archived observation captures: 42
- Exact matching: same valid timestamp.
- Window matching: nearest archived observation within ±30 minutes.
- Both use the first archived capture at or after the target; no interpolation or imputed observation.

| Model / horizon | Exact N | Exact MAE (ft) | ±30 min N | ±30 min MAE (ft) | ΔN | ΔMAE (ft) |
|---|---:|---:|---:|---:|---:|---:|
| persistence:12h | 37 | 0.1340 | 38 | 0.1313 | 1 | -0.0027 |
| persistence:24h | 34 | 0.2454 | 35 | 0.2419 | 1 | -0.0036 |
| persistence:6h | 39 | 0.1942 | 40 | 0.1898 | 1 | -0.0044 |
| phase5a_coastal:12h | 37 | 0.1896 | 38 | 0.1890 | 1 | -0.0006 |
| phase5a_coastal:24h | 34 | 0.1530 | 35 | 0.1539 | 1 | 0.0008 |
| phase5a_coastal:6h | 39 | 0.1789 | 40 | 0.1761 | 1 | -0.0028 |
| phase5a_maul1_only:12h | 37 | 0.0955 | 38 | 0.0943 | 1 | -0.0012 |
| phase5a_maul1_only:24h | 34 | 0.2365 | 35 | 0.2305 | 1 | -0.0060 |
| phase5a_maul1_only:6h | 39 | 0.2005 | 40 | 0.1966 | 1 | -0.0038 |
| phase5b_coastal_tidal:12h | 37 | 0.1854 | 38 | 0.1846 | 1 | -0.0007 |
| phase5b_coastal_tidal:24h | 34 | 0.1503 | 35 | 0.1500 | 1 | -0.0003 |
| phase5b_coastal_tidal:6h | 39 | 0.1815 | 40 | 0.1788 | 1 | -0.0027 |
| phase5b_full_multivariable:12h | 37 | 0.1898 | 38 | 0.1898 | 1 | 0.0001 |
| phase5b_full_multivariable:24h | 34 | 0.1572 | 35 | 0.1554 | 1 | -0.0017 |
| phase5b_full_multivariable:6h | 39 | 0.1819 | 40 | 0.1795 | 1 | -0.0025 |

The comparison is sensitive to sample composition as well as timestamp tolerance. These are alternative retrospective matches, not a correction to published verification and not independent-sample skill claims.
