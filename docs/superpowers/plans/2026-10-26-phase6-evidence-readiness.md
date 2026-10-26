# Phase 6.17 Evidence Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, prospective-only readiness view to the Phase 6 page using existing metrics and immutable records, plus explicit proposed challenger gates.

**Architecture:** Keep archive generation and evidence storage untouched. A pure browser helper will summarize existing `history/index.json`, `performance.json`, `latest.json`, and a versioned gate configuration; the current Phase 6 updater already refreshes the underlying index and metrics from newly appended verification revisions. The UI will distinguish overlapping issue-target samples from the existing outcome-defined event groups and will not infer unsupported episode counts.

**Tech Stack:** Python unittest, browser JavaScript, GitHub Pages static assets.

**Spec:** User request in this thread; current `docs/phase6-methodology.md` and `docs/phase6-16-scientific-correctness-audit.md`.

## Global Constraints

- Research/shadow evaluation only; no operational advice or forecast changes.
- Do not modify `.github/workflows/`, `scripts/phase6.py`, or anything under `site/data/prospective/`.
- Do not modify any authentic issue, verification revision, source evidence, or Phase 5A/5B artifact.
- Retain native MAUL1 00065 datum, the Phase 6.16 timing erratum, and actual issue versus feature-anchor distinction.
- Do not claim independent skill from overlapping hourly targets or invent receipt times/event episodes.
- Proposed promotion gates remain inactive until explicitly owner-approved in configuration.

## File Map

- `site/phase6-readiness.js`: pure deterministic summary and HTML renderer.
- `site/phase6-readiness-gates.json`: editable proposed thresholds and explicit pending approval metadata.
- `site/phase6-readiness.css`: small styles matching existing research cards/tables.
- `site/phase6.js`, `site/index.html`: load/render readiness panel from existing generated metrics.
- `tests/phase6-readiness-smoke.cjs`, `tests/phase6-site-smoke.cjs`: browser-summary and presentation assertions.
- `tests/test_phase6_core.py`: sample completeness, missingness, and existing event-grouping behavior.
- `docs/phase6-17-evidence-readiness.md`, `docs/phase6-methodology.md`: observed current counts, evidence interpretation, gate criteria and remaining limits.

## Tasks

- [ ] Pin hashes of all current authentic issue and verification files outside the repository.
- [ ] Add Python tests for paired sample counts, due/mature/verified/abstained states, missing metric rows, and exact 24-hour event-group boundary.
- [ ] Add JS tests for deterministic summary counts, source missingness/age labels, event suppression, gate approval state, and prominent prospective-only rendering.
- [ ] Run the tests red; implement the pure readiness helper and configuration; run them green.
- [ ] Wire the readiness panel into the existing Phase 6 view; leave existing score calculations and archive updater unchanged.
- [ ] Document latest-main evidence counts, gate proposal/rationales, and unsupported false-alert episode claims.
- [ ] Run full Python, relevant Node tests, frozen-model replay, deterministic summary rerun, and final immutable-hash comparison.
- [ ] Open a ready-for-review PR, review required CI, merge only after checks and parity pass, then verify Pages publication.
