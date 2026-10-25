# Significant-rise integration review

**Status: retrospective development evidence only. No forecast model or prospective record was changed.**

## Reviewed packages and provenance

- Challenger and historical Model Lab package: PR #54, reviewed head `241d99f8f0fc84f29c91ab3ba4ff40152dfff2f0c` (feature commit `36ea832de1307a029f23ebea2d75d478fe98eefd`). Its reproducible package, methodology, generated metrics, and tests were reviewed.
- Significant-rise audit: PR #55, reviewed head `1ef9f893cc3df2fc45b24cac31294e8c1143187b`. Its report, code, generated event/alert outputs, provenance, and tests were reviewed.
- Integration starts at `main` commit `a2bf95ff0a44171d30cc1bf67c1e7643890b9b38`. Reviewed commits were cherry-picked with `-x`; the rise audit code and generated artifacts retain the exact Agent 1 commit.

## Review and reconciliation

The Model Lab reproduces the published Phase 5A/5B baselines from the historical archives into temporary directories and pairs forecasts to observations by issue time, horizon, and target time. The trend challenger uses only issue-time native MAUL1 stage and the completed six-hour MAUL1 change. Its calibration targets are purged 72 hours before validation; future target values, NOAA future-valid astronomy, outcome labels, and MCHL1 do not enter challenger features. The archived 2023+ evaluation has already been inspected, and original source receipt times are absent, so this is not a pristine test or proof of operational availability.

The rise audit uses Phase 5B holdout rows and the existing Phase 6 target grouping/alert rules. Its exact counts reproduce the Model Lab: 109 grouped qualifying rises, 28 detections, 81 misses, 48 false alert clusters, and 305 false-positive target windows for Phase 5B coastal + tidal. It uses each row's archived actual and keeps issue time separate from valid time. It does not interpolate. MAUL1 remains native 00065 gage height; NWCL1 residual remains MLLW referenced. No NAVD88 threshold is applied.

Review also found the PR's committed event CSV export contained a literal truncation notice and omitted rows. The export has been regenerated from the reviewed audit code; its corrected CSV now contains the full 109 event groups, and the generated summary fingerprints the integrated source files.

The two hit rates use different units and answer different questions. The 28/109 grouped detection result credits a qualifying group when an alert is issued before its first qualifying target. The 202/1,859 target-window POD counts each qualifying hourly target window separately. The latter windows overlap and are correlated; these metrics are not contradictory and neither establishes 109 independent physical events. The event crosswalk shows that Phase 6 groups and Phase 3B response windows overlap many-to-many.

The diagnostic findings explain underforecast arithmetic, not forcing cause. Among missed Phase 5B groups, 57 were large subthreshold forecasts (median maximum predicted change 0.233 ft versus median observed qualifying target change 0.640 ft), 22 peaked from 0.40 to 0.50 ft, and two crossed the threshold only after the group's first qualifying target. Elevated NWCL1 setup and wind co-occurred with both hits and misses. False and hit-containing alert clusters also had similar median NWCL1 setup and wind. Those associations do not identify a causal predictor. The current predictor set does not include a validated local rainfall or urban tributary series.

## Challenger results

On the reused common 2023+ holdout, Phase 5B coastal + tidal MAE was 0.0626, 0.1219, and 0.1902 ft at 6, 12, and 24 hours. The damped-trend candidate scored 0.1721, 0.2443, and 0.2358 ft. At 24 hours it detected 0/109 groups, with 1,859 missed rise target windows and zero alert clusters. Its apparent 6h advantage over persistence (0.1721 versus 0.1742 ft) is not an improvement over MAUL1-only (0.0934 ft), and the candidate missed every grouped rise. It also had higher MAE than coastal + tidal in each reported holdout year and season.

The better rise detection by coastal models carries a false-alarm cost. MAUL1-only detected 1/109 groups with 8 false clusters and 33 false target windows; Phase 5A coastal detected 26/109 with 39 clusters and 222 false target windows; Phase 5B coastal + tidal detected 28/109 with 48 clusters and 305 false target windows. The full multivariable model detected 28/109 with 44 clusters and 260 false target windows. These are descriptive counts over a reused period, not independent-sample rates.

**Decision:** do not promote or shadow-test the bounded trend candidate. It fails both the significant-rise objective and the paired MAE comparison with coastal models. The reviewed package does not identify a new candidate with a robust enough benefit to justify a separate prospective experiment. Frozen Phase 6 coefficients and authentic archives remain untouched.

## Highest-value next study

Test whether locally resolved rainfall or tributary response explains event heterogeneity. First establish actual data access, continuity, drainage relevance, units, datum, QC, and receipt-time availability for the identified USGS precipitation and tributary candidates and NOAA MRMS. Archive eligible inputs prospectively with receipt timestamps and quality state. Then predeclare observed-only trajectory labels, event-blocked holdouts, and paired detection/false-alert plus MAE criteria before fitting any candidate. Until the predictor archive and design exist, no versioned model shadow is justified by these retrospective results.
