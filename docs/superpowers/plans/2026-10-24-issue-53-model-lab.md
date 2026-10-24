# MAUL1 Model Lab Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax.

**Goal:** Add a separate, reproducible historical Model Lab with paired diagnostics and one rigorously evaluated challenger while preserving the three existing tabs and all Phase 6 evidence.

**Architecture:** A Python report generator reads only existing Phase 5A/5B and hourly archives, validates reproduction, fits a bounded damped-trend challenger through nested chronological calibration folds, and writes one compact report JSON. An independent Model Lab tab renders that report and selected case plots without connecting the historical experiment to Current Forecast or Forecast Verification.

**Tech Stack:** Python 3.12, NumPy, unittest, vanilla JavaScript, Plotly, GitHub Actions and Pages.

**Spec:** `docs/model-lab-methodology.md` and GitHub Issue #53.

## Global Constraints

- Preserve Current Forecast, Forecast Verification, and Historical Research behavior and data contracts.
- No changes to frozen Phase 6 model artifacts, authentic prospective archives, forecast issuances, or verification revisions.
- Use MAUL1 USGS 00065 native gage height; no NAVD88 conversion.
- Do not use NOAA future-valid predictions or unverified MCHL1 values in the challenger.
- Historical valid-time archives have no receipt-time ledger; findings remain retrospective and not proven available at issue.
- Label all experiments Research / Shadow Evaluation / Not Operational and Retrospective / Development Evidence.

## Review Focus

- Target-time leakage across temporal folds — test embargo and feature availability.
- Unequal sample rows across model scores — test common issue/target identity and missing-model abstention.
- Overlapping forecasts inflating event sample size — test grouping by event IDs.
- Baseline drift during reproduction — verify exact Phase 5A/5B score parity.
- Dashboard interference — test all original tab IDs, selectors, and smoke behavior remain present.

---

### Task 1: Historical experiment and report generator

- [x] Add failing tests for fold purge, issue-time-only challenger, paired identity, metrics/uncertainty, event grouping, and future-feature perturbation.
- [x] Implement `scripts/model_lab.py` with deterministic baseline reproduction checks, nested forward validation, paired diagnostics, ablations, case studies, and provenance.
- [x] Generate `site/data/research/model-lab.json` and `docs/model-lab-findings.md` from committed archives only; confirm source archives remain unmodified.

### Task 2: Isolated Model Lab dashboard

- [x] Add a fourth ARIA tab/panel while retaining existing IDs and content.
- [x] Build controls for horizon, regime, and historical case; render paired metrics, ablations, event/failure tables, provenance, and issue-time marker chart.
- [x] Add JS tests and smoke assertions that original views remain intact and historical predictions never appear in prospective components.

### Task 3: Validation and release

- [x] Add generated-report validation and all new tests to CI.
- [x] Run full Python and JavaScript suites, deterministic double generation, existing dashboard smoke tests, and frozen Phase 6 artifact checks.
- [ ] Open PR, require green CI, merge to main, and verify Pages deployment and report availability.
