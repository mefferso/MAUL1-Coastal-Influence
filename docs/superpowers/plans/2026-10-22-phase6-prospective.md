# Phase 6 Prospective Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the Phase 5A/5B models and deploy an auditable hourly prospective issuance and verification system with a research dashboard.

**Architecture:** Reconstruct and freeze existing calibration-only model states first, then add source adapters and immutable issue snapshots, independent verification and metrics, and a separate dashboard module. A single scheduled GitHub Actions workflow serializes issuance and verification, stores append-only records, and lets the existing Pages workflow publish successful updates.

**Tech Stack:** Python 3.12, existing NumPy and repository parsers, JSON/CSV.gz, GitHub Actions, vanilla JavaScript/SVG.

**Spec:** `docs/phase6-methodology.md` (requirements from the user-supplied Phase 6 assignment).

## Global Constraints

- Only frozen Phase 5A MAUL1-only/coastal and Phase 5B coastal+tide/full models are prospective candidates; no prospective refit or gate.
- Horizons are exactly 6, 12, and 24 hours from actual issuance.
- MAUL1 00065 stays native gage height; 63160 NAVD88 stays separate; no −1.38-ft shift or 4.0-ft NAVD88 inference.
- Only completed issue-time observations with source receipt times before actual issuance may enter a snapshot.
- Maximum input age is 2 hours for latest MAUL1 stage and 3 hours for other stations; missing/stale inputs cause explicit abstention or documented model imputation.
- Authentic forecast and verification files are create-only; simulations are isolated; late verification changes append revisions.
- No historical reacquisition, PETSS-Plots change, paid service, or operational claim.

## Review Focus

- Source valid-time or receipt-time lies after issuance: verify it is rejected from features.
- USGS/NWCL1 quality, unit, datum, or station identity changes: verify source row is retained as excluded/diagnostic.
- Partial or empty API response: verify the source status and unaffected model statuses remain explicit.
- Concurrent/rerun action: verify unique records, no overwrite, and push retries on stale `main`.
- Missing exact verification target or late correction: verify pending state and numbered immutable revisions.

---

### Task 1: Freeze and replay the existing estimators

**Files:** Create `scripts/phase6_models.py`, `site/data/prospective/model-artifacts.json`, and `tests/test_phase6_models.py`.

**Interfaces:** `freeze_models(root) -> dict`; `load_artifacts(path) -> dict`; `predict_frozen(artifact, features) -> (forecast_ft, imputed_feature_count)`.

- [ ] Write tests for all required model names/horizons, no gate/retrospective model, stable artifact hash, and `1e-8 ft` replay of the published Phase 5A/5B holdout rows.
- [ ] Run the new tests and confirm failure because the Phase 6 artifact/inference API is absent.
- [ ] Reconstruct complete Phase 5B preprocessing state from its stored calibration selection and the committed calibration archive; extract Phase 5A final-fit state without changing its parameters.
- [ ] Serialize every transform, feature order, clipping bound, interval width, version, source hash, and code hash; implement inference using only that artifact.
- [ ] Run the focused tests, compare the complete eligible holdout, then run all existing tests.

### Task 2: Capture and validate real issue-time sources

**Files:** Create `scripts/phase6_sources.py`, `tests/test_phase6_sources.py`, and `tests/test_phase6_sources_live.py`.

**Interfaces:** `fetch_snapshot(now_utc, fetcher=...) -> snapshot`; `aggregate_completed_bins(snapshot, issue_time) -> index`; each source result includes status, request, retrieval time, normalized observations, and response hash.

- [ ] Test real parser code against empty, partial, bad-timestamp, wrong-station, wrong-unit, wrong-datum, stale, and source-error responses; assert no interpolation or silent carry-forward.
- [ ] Run tests to confirm failures for missing adapters and validation behavior.
- [ ] Add recent-window USGS, CO-OPS, and IEM/HADS requests using established identifiers/parsers; retain raw valid time, retrieval time, QC, unit, datum, and provenance.
- [ ] Enforce completed hourly bins and the 2-hour MAUL1 / 3-hour other-source age rules; preserve 63160 separately and exclude retrospective-only prediction features absent capture evidence.
- [ ] Add a live-source smoke command for GitHub Actions that reports each provider response without allowing local restricted-egress workarounds.
- [ ] Run focused parser/age tests and the live-source smoke on the PR runner.

### Task 3: Issue immutable forecasts and attempt audits

**Files:** Create `scripts/phase6_forecast.py`, `tests/test_phase6_forecast.py`.

**Interfaces:** `issue_forecast(snapshot, actual_issue_time, nominal_slot, artifacts, run_metadata) -> record`; `write_immutable(record, archive_root) -> path`.

- [ ] Test exact valid-time arithmetic, actual-vs-nominal time, eligible/ineligible MAUL1 cases, model-independent statuses, and no-write-on-existing-path.
- [ ] Run the tests and confirm they fail before implementation.
- [ ] Build Phase 5A/5B feature rows from captured completed bins; issue persistence, frozen MAUL1-only, coastal, coastal+tide, and full models independently for each horizon.
- [ ] Write one create-only issuance plus an immutable compressed feature/source snapshot and audit attempt; isolate simulated runs.
- [ ] Run focused tests and historical replay regression.

### Task 4: Verify outcomes and compute prospective diagnostics

**Files:** Create `scripts/phase6_verify.py`, `scripts/phase6_metrics.py`, `tests/test_phase6_verify.py`, `tests/test_phase6_metrics.py`.

**Interfaces:** `verify_due(forecast_records, observations, ingestion_time) -> revisions`; `compute_metrics(forecasts, latest_verifications) -> dict`.

- [ ] Test not-due records, exact/horizon-matched targets, missing targets, immutable forecasts, idempotent results, and numbered late-observation revisions.
- [ ] Test rise confusion counts at 0.25/0.50/1.00 ft, underforecast tails, event grouping/lead time, interval upper-bound exceedance, and input-age strata.
- [ ] Run tests to confirm expected failures, then implement verification after completed target periods only and keep every revision.
- [ ] Suppress unstable event skill when independent event count is below the documented minimum; run focused and full test suites.

### Task 5: Add the prospective dashboard

**Files:** Modify `site/index.html` and `site/app.js`; create `site/phase6.js` and `tests/phase6-site-smoke.cjs`.

**Interfaces:** Dashboard consumes `latest.json`, `history/index.json`, and `performance.json`; missing files render an explicit no-authentic-issuance state.

- [ ] Test no-data, archived forecasts, verified overlays, model selector, horizon labels, and research/datum warnings before implementing the renderer.
- [ ] Add a separate Prospective Forecast Verification section with recent observed MAUL1 stage, forecast intervals, immutable history, sample-size-aware metrics, event displays, availability, and limitations.
- [ ] Ensure it reads archived forecast values only and distinguish model/horizon without clutter.
- [ ] Run site smoke and existing historical rendering tests.

### Task 6: Automate, document, and validate the end-to-end release

**Files:** Create `.github/workflows/phase6.yml`; modify `.github/workflows/phase5a.yml`, `.github/workflows/phase5b.yml`, `.github/workflows/site.yml`; create `docs/phase6-operations.md`.

- [ ] Test workflow helper logic for stale-branch push recovery and the shared single-writer lock.
- [ ] Add hourly UTC issuance plus verification, manual simulation/live dispatch, PR source smoke, least-privilege permissions, audit artifacts, and idempotent retry-safe push logic.
- [ ] Make Phase 5A/5B report commits rebase/retry safely after concurrent main updates; have successful Phase 6 archive commits trigger Pages deployment.
- [ ] Document source limits, schedule delays, actual issue time, model hashes, eligibility, no-backfill rule, failure recovery, manual simulation, and revision semantics.
- [ ] Run all repository tests, live-source checks, site smoke, artifact replay, PR Actions, merge, and verify the first authentic scheduled/current-time forecast. If source availability prevents it, retain the explicit abstention and report the limitation.
