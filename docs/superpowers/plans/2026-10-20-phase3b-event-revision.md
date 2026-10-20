# Phase 3B Event Validation Revision Implementation Plan

> **For agentic workers:** Implement inline under the user's explicit authorization; tests are written first.

**Goal:** Add an auditable MAUL1-only physical response catalogue and independent observed nonresponse windows while preserving the legacy Phase 3B analysis.

**Architecture:** Keep existing episode detection, groups, matches, and outputs as legacy comparison. Add a MAUL1 stage turning-point detector using smoothed native gage-height excursions and recovery separation; evaluate existing predictor signals only after event times are fixed. Add fixed non-overlapping windows with uniform coverage and overlap exclusions. Emit machine-readable records and a concise dashboard summary.

**Tech Stack:** Python 3.12 standard library, unittest, existing GitHub Actions historical validation and Pages workflows.

**Spec:** User-pasted Phase 3B Scientific Corrections and Event Validation (2026-10-20).

## Global Constraints

- MAUL1 00065 stays native gage height and never establishes NAVD88 thresholds.
- Do not infer causality, forecast skill, operational lead, or automatic recommendations.
- Preserve existing Phase 3B results for comparison and all missingness/datum safeguards.
- Do not use predictor behavior to define primary target events.

## Review Focus

- Missing observations split event runs and censor uncertain starts; never interpolate.
- Predictor-only episodes cannot merge target events.
- Response and control intervals plus antecedent/recovery buffers cannot overlap.
- Threshold and recovery sensitivity is declared independently of matches.
- Historical NAVD88 threshold eligibility remains unchanged.

### Task 1: MAUL1 response event catalogue

**Files:** Modify `scripts/validate_phase3b.py`; test `tests/test_validate_phase3b.py`.

- [ ] Add failing synthetic tests for separate MAUL1 cycles, predictor independence, recovery, and gaps.
- [ ] Implement MAUL1-only event detection and threshold/recovery sensitivity.
- [ ] Match existing predictor detections to fixed target onset times; retain coverage and uncertainty.

### Task 2: Negative controls and outputs

**Files:** Modify `scripts/validate_phase3b.py`, `.github/workflows/phase3b.yml`, `site/app.js`, `site/index.html`; test `tests/test_validate_phase3b.py`.

- [ ] Add failing tests for control overlap, completeness, and non-overlapping independence.
- [ ] Build fixed seven-day control candidates with explicit categories and exclusions.
- [ ] Emit revised JSON/CSV/Markdown alongside legacy outputs and render compact dashboard summary.
- [ ] Run full tests, historical workflow, report generation, Pages deployment, and inspect generated outcomes.
