# Phase 6 Scientific Audit Implementation Plan

> Execution record: completed in the PR branch; see the linked scientific report and workflow checks.

**Goal:** Reproduce the frozen models' MCHL1 training support and clarify the Phase 6 prospective scorecard.

**Architecture:** A read-only Python audit reads Phase 5A/5B training archives and the frozen artifact, calculating per-model/horizon availability and learned coefficients. A small update to the existing Phase 6 renderer exposes existing summary statistics and labels horizons with no verified outcomes as pending.

**Tech Stack:** Python 3.12, stdlib `unittest`, existing NumPy model artifacts, vanilla JavaScript.

**Spec:** `docs/superpowers/specs/2026-10-23-phase6-scientific-audit-design.md`

## Global Constraints

- Frozen models and authentic prospective archives remain unchanged.
- MCHL1 remains shadow-only; its native datum remains unverified.
- MAUL1 00065 is not converted to the 4.0 ft NAVD88 threshold.
- Independent events remain withheld below five groups.
- Use only matured archived outcomes; no backfilled prospective forecasts.

## Review Focus

- Missing MCHL1 columns or model-family changes: audit every model/horizon and report no-feature cases explicitly.
- Sparse training support: distinguish missing rate from coefficient existence and report value and missingness coefficients separately.
- Coefficient-to-column mapping: test active masks with inactive columns and intercept handling.
- No 24-hour verification: show pending, not zeros.
- Small/overlapping event counts: retain sample denominators and the five-group event gate.

### Task 1: Reproducible MCHL1 frozen-model support audit

**Files:**
- Create: `scripts/audit_mchl1_model_support.py`
- Create: `tests/test_audit_mchl1_model_support.py`
- Create: `docs/phase6-15-mchl1-model-support.md`

**Interfaces:** `audit_model_support(root: Path) -> dict`; `coefficient_for(artifact_model: dict, feature_index: int, missingness: bool = False) -> float`.

- [x] Test nonzero active feature and indicator coefficients, inactive columns, and no-MCHL1 model results.
- [x] Run the new tests and verify they fail for missing functions.
- [x] Implement exact calibration-row selection matching Phase 5A/5B model training, then report per-feature nonmissing counts/rates, sentinel contamination, and mapped coefficients for all models/horizons.
- [x] Run new tests and regenerate the report from the committed artifacts.
- [x] Record limitations and inference mismatch without activating features.

### Task 2: Prospective scorecard denominators and pending horizons

**Files:**
- Modify: `site/phase6.js`
- Modify: `tests/phase6-site-smoke.cjs`

**Interfaces:** `showMetrics(report)` renders model/horizon records from `performance.json`, plus a pending row when no mature records exist for 24h.

- [x] Add smoke assertions for RMSE, sample/interval/event denominators, and 24-hour pending status.
- [x] Run the site smoke test and verify the new assertions fail.
- [x] Render MAE, RMSE, bias, persistence MAE/skill, threshold POD and false-alarm counts/ratios, interval coverage with denominator, and independent-event count for 6/12/24h.
- [x] Run the site smoke test and full repository unit/smoke suite.

### Task 3: Review and publish

- [x] Verify generated audit findings against raw archive rows and artifact masks.
- [x] Confirm frozen artifacts, prospective archives, and MCHL1 shadow-only eligibility remain unchanged; correct the ingestion parser's handling of HADS missing sentinels.
- [x] Create a focused PR; required checks and merge are pending final sentinel-correction rerun.
