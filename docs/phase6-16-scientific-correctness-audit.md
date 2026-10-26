# Phase 6.16 scientific correctness and verification audit

**Status:** research / shadow evaluation only. This audit does not establish independent operational skill. Frozen Phase 5A/5B artifacts, authentic issue files, archived observation captures, and prior verification revisions remain immutable.

Repository growth and workflow reliability are documented separately in the [Phase 6.17 sustainability report](phase6-17-sustainability.md). The [MCHL1 evidence determination](mchl1-determination.md) consolidates its shadow-only disposition and reopening criteria.

## Timing contract and historical erratum

Phase 5A builds its target at the exact hourly feature anchor plus the requested horizon; Phase 5B inherits that convention. The updated prospective issuer floors the execution timestamp to the completed UTC feature hour, records that anchor, and sets valid time to anchor plus horizon. Actual issue time stays separate, and effective lead is valid time minus actual issue time. Verifying observations retain their own valid timestamp and capture/receipt context; no observation is invented or shifted.

The first authentic issue, `site/data/prospective/archive/issues/d4935e479e83311c.json`, is an immutable pre-fix record (SHA-256 `ec468750e739cbb07e234e1277c16850d77b44f2d081291efbb63dd70fa78feb`). It was actually issued at 2026-10-22T13:53:11Z, with nominal time 13:53:09Z, and valid times at actual issue plus 6/12/24 hours. Relative to its 13:00 feature anchor and Phase 5 target convention, those targets are 53m11s late. This is a historical erratum; the original file and its verification evidence must remain as archived. New records include an explicit feature anchor and valid-time basis. Comparisons spanning the old issue must disclose the contract discontinuity.

## Retrospective matching sensitivity

`scripts/audit_phase6_verification_sensitivity.py` compares exact valid-time matches with nearest captured observations within ±30 minutes, using only the first archived capture at or after target and no interpolation. Full output and input hashes are in `research/phase6-verification-sensitivity/`. Across 42 issues and captures, each model/horizon gains one matched target under the window rule. MAE differences range from −0.0060 ft to +0.0008 ft. This difference includes changed sample composition and is not a correction to published results or an independent skill claim. Original verification outputs are unchanged.

## Source QC, missing values, and NWCL1 residuals

`scripts/audit_phase6_source_missingness.py` read-scans committed normalized monthly source data and records hashes, station/product counts, finite ranges, and QC in `research/phase6-source-qc-audit/`. It finds 944,998 NWCL1 water observations with exact-time MLLW prediction pairs; 933,172 pass stored CO-OPS QC and 11,826 have nonzero flags. The feature path only pairs completed same-hour observed/predicted MLLW values with acceptable QC. Historical raw records retain rejected rows for audit; rejected flags are not converted into usable residuals.

The audit found 315 exact 9,999,999-ft HADS sentinel records in archived MCHL1 source rows, and reports no retained HADS numeric values at or above 1,000,000 ft in normalized monthly archives. Existing Phase7 contamination evidence (21 contaminated hourly values, 206 derived changes, 10 Phase5 predictor cells) is historical audit evidence only; no original feature or model artifact was repaired in place. USGS negative missing markers and NDBC 99.0 m/s speed/gust sentinel conversions were not found among normalized archived rows. New parsing drops nonfinite values, USGS negative sentinels, and field-specific NDBC sentinels before aggregation; valid independent wind fields survive a missing direction or gust.

NWCL1 residual eligibility depends on matching observed and predicted MLLW timestamps, units and acceptable QC. This audit confirms archive-level pairing counts and tests the hourly feature eligibility path. It does not prove every provider product was captured without delay or that historical provider records had source receipt times. NDBC normalized history is not a Phase 6 feature input. Previous normalized NDBC data cannot recover rows discarded when WDIR=999 caused the old parser to discard the entire row; source bodies are not archived.

MAUL1 USGS 00065 is native gage height and is never interpreted as NAVD88. Only verified direct 63160 may be compared to 4.0 ft NAVD88; 63160 remains outside model features. MCHL1 datum remains unverified and relative-change-only. No operational threshold or advisory recommendation is introduced.

## Dashboard interpretation and evidence limits

The dashboard exposes issued/matured/verified sample counts by model/horizon, nominal slot, feature anchor, actual issue time, valid time and effective lead. N counts issue-target pairs. Hourly forecast windows overlap, so these counts are not independent samples; historical overlapping-window results must be labeled as such. Event metrics remain subject to the existing minimum independent-event gate. Labels clarify interpretation without changing computed skill.

The October 25 Muse audit was requested as source material. No matching artifact or findings were located in repository history, Issue #25, or connected Drive search. This report therefore records the confirmed repository findings and does not attribute unverified conclusions to that audit.

## Reproducibility

- Run source audit: `python scripts/audit_phase6_source_missingness.py --output research/phase6-source-qc-audit`
- Run matching sensitivity: `python scripts/audit_phase6_verification_sensitivity.py --output research/phase6-verification-sensitivity`
- Tests pin the immutable first authentic issue hash and timestamps, Phase 5 target convention, QC/sentinel handling, NWCL1 residual pairing, and sensitivity matching behavior.
- Audit JSON includes input hashes. Generated experimental reports are separate from frozen issuances and verification archives.
