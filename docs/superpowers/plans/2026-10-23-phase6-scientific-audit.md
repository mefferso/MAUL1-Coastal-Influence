# Phase 6 Scientific Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

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

- [ ] Test nonzero active feature and indicator coefficients, inactive columns, and no-MCHL1 model results.
- [ ] Run the new tests and verify they fail for missing functions.
- [ ] Implement exact calibration-row selection matching Phase 5A/5B model training, then report per-feature nonmissing counts/rates and mapped coefficients for all models/horizons.
- [ ] Run new tests and regenerate the report from the committed artifacts.
- [ ] Record limitations and inference mismatch without activating features.

### Task 2: Prospective scorecard denominators and pending horizons

**Files:**
- Modify: `site/phase6.js`
- Modify: `tests/phase6-site-smoke.cjs`

**Interfaces:** `showMetrics(report)` renders model/horizon records from `performance.json`, plus a pending row when no mature records exist for 24h.

- [ ] Add smoke assertions for RMSE, sample/interval/event denominators, and 24-hour pending status.
- [ ] Run the site smoke test and verify the new assertions fail.
- [ ] Render MAE, RMSE, bias, persistence MAE/skill, threshold POD and false-alarm counts/ratios, interval coverage with denominator, and independent-event count for 6/12/24h.
- [ ] Run the site smoke test and full repository unit/smoke suite.

### Task 3: Review and publish

- [ ] Verify generated audit findings against raw archive rows and artifact masks.
- [ ] Confirm no model artifact, feature vector, source eligibility, or prospective archive changed.
- [ ] Create a focused PR, wait for all checks, and merge only if all required checks pass.
