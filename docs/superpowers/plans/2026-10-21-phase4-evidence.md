# Phase 4 Evidence Implementation Plan

> Implement inline using superpowers:executing-plans; perform a fresh whole-branch scientific/code review.

**Goal:** Deliver transparent retrospective evidence classification and causal valid-time research replay.
**Architecture:** Separate hourly evidence engine from archive orchestration and report rendering; preserve existing scientific products.
**Tech Stack:** Python standard library, unittest, existing static JavaScript and GitHub Actions.
**Spec:** docs/superpowers/specs/2026-10-21-phase4-evidence.md

## Global Constraints
No forecasts, alerts, probabilities, attribution fractions, historical datum conversions, new downloads or PETSS changes. Keep five-station identities and all Phase 3B products.

## Review Focus
Completed-bin replay eligibility; nonoverlapping evidence versus compound; quality/datum boundaries; full feature-window seam protection; named cases cannot become reference truth.

### Task 1: Evidence engine
Create scripts/evidence.py and tests/test_evidence.py. Interface: assess(index, issue, thresholds) returns evidence states/metrics/explanations using completed trailing hourly bins only. Tests first: missing/failed QC, no independent lake, compound coexistence, opposing winds, disjoint signals, native datum boundaries, future mutation invariance, observed nonresponse. Run focused unittest red then green. Freeze physical thresholds before archive evaluation.

### Task 2: Archive evaluation
Create scripts/phase4.py. Consume frozen phase3b validation.json plus archived hourly observations. Generate historical.json, replay.json.gz, sensitivity.json, cases.json, summary.json, report.md and CSV exports. Assess all 189 response events, 63 eligible controls, fixed-clock case snapshots, sensitivity variants and embargo/dependence audit. Tests cover calibration exclusion, deterministic output, replay differences and legacy preservation. Run full archive and inspect representative classifications.

### Task 3: Website, Actions and scientific review
Add compact Phase 4 section and report links, preserving charts and existing dashboard. Add no-download Phase 4 Actions workflow, reproducibility check and PR CI. Execute Python and site tests and deterministic full rerun. Fresh reviewer checks science/code, address material findings with regressions. Commit code and generated outputs, open PR, inspect Actions, merge main and verify deployment.
