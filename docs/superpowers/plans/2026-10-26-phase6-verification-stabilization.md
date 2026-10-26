# Phase 6 Verification Stabilization Implementation Plan

> **For agentic workers:** Execute this plan inline. Use test-driven development and preserve all frozen artifacts and authentic archives.

**Goal:** Stabilize Phase 6 scientific timing, verification sensitivity, and source missing-value handling while preserving historical evidence.

**Architecture:** Add retrospective audit code that reads immutable issue and observation archives and writes results only to a separate research output. Pin the first authentic issue and training target conventions in regression tests; harden source parsers before aggregation; clarify dashboard labels without recomputing or changing skill.

**Tech Stack:** Python standard library and unittest, existing NumPy model replay, vanilla JavaScript smoke tests.

**Spec:** `docs/phase6-methodology.md`, `docs/phase6-operations.md`, `docs/phase7-data-quality.md`, Issue #25, and user mission in this task.

## Global Constraints

- Research/shadow only; no operational warnings or recommendations.
- Do not modify frozen Phase 5A/5B artifacts, original Phase 6 issues, or archived verification evidence.
- MAUL1 USGS 00065 remains native gage height; only direct 63160 NAVD88 supports comparison with 4.0 ft NAVD88.
- Do not fabricate missing observations, receipt times, issuance times, or independent skill.
- Use free GitHub-hosted infrastructure; no retraining, PETSS, or operational integration.
- All new numerical sensitivity results go to a separate experimental directory and never replace published metrics.

## Review Focus

- Off-hour issue versus hourly model anchor and target time — regression test against the first authentic archive and Phase 5 target convention.
- Exact-time versus ±30-minute verification matching — deterministic retrospective comparison from archived observations.
- NDBC missing markers before hourly aggregation — field-level parser tests for `999` direction and `99.0` speed/gust.
- USGS quality and missing-value distinctions — tests cover approved/provisional qualifiers, negative sentinels, and separate 00065/63160 datums.
- Prospective maturity and dependent hourly windows — site smoke test for labels and denominators without changing computed metrics.

---

### Task 1: Timing contract and immutable authentic regression fixture

**Files:** `tests/test_phase6_core.py`, new `tests/test_phase6_regression.py`, `docs/phase6-methodology.md`, `docs/phase6-operations.md`.

Assert Phase 5A target is exact hourly issue time + horizon, Phase 5B inherits that target convention, current forecast valid time is feature-anchor + horizon, and effective lead subtracts actual issuance. Load `d4935e479e83311c.json` as a read-only fixture; assert byte hash and original actual/valid timestamps. Document its historical 53m11s offset from the target grid and do not patch its record.

### Task 2: Retrospective verification matching sensitivity

**Files:** new `scripts/audit_phase6_verification_sensitivity.py`, new `tests/test_phase6_verification_sensitivity.py`, separate `research/phase6-verification-sensitivity/` output.

Compute exact-time and nearest-within-30-minute matches from archived authentic issues and source observation captures. Preserve original revisions and `performance.json`; report counts and paired metric deltas only as an experimental sensitivity.

### Task 3: Source missingness and quality safeguards

**Files:** `scripts/history_sources.py`, `scripts/phase6.py`, `tests/test_history_sources.py`, `tests/test_build.py`, `tests/test_phase6_sources.py`, `docs/phase7-data-quality.md`.

Reject NDBC standard-met missing markers at field level before hourly aggregation while retaining independent valid fields. Pin USGS negative sentinel handling, accepted approved/provisional qualifiers, CO-OPS field QC, HADS `9999999.0`, and datum separation. Do not rewrite historical input archives; state any experimentally observed numerical effect separately.

### Task 4: Prospective maturity and dependence labels

**Files:** `site/phase6.js`, `tests/phase6-site-smoke.cjs`, `docs/phase6-methodology.md`.

Display model anchor, nominal and actual issuance, valid time and effective lead separately. Make sample size, due/matured/verified counts, pending state, and overlapping-window dependence explicit. Leave metric calculations and historical skill unchanged.

### Task 5: Findings, issue update, and verification

**Files:** scientific findings note under `docs/`, Issue #25 comment, only regression tests/docs/site source and separate experiment outputs.

Record confirmed fixes, immutable-history limitation, unresolved source and independence constraints, Muse audit retrieval gap, and exact reproducibility commands. Run full Python tests, Node smoke tests, deterministic sensitivity reproduction, and frozen model comparison; open a ready-for-review PR without merging.
