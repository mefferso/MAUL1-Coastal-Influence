# Forcing Archive Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover missed NOAA and USGS observations with real valid and retrieval timestamps and report archive completeness without changing archived forecasts.

**Architecture:** Extend the existing collector with provider time-window acquisition, immutable raw response references, append-only revision-aware receipts, and recovery classification. Add a deterministic archive report, wire it into Actions summaries, and keep archive-only pushes from invoking Pages deployment.

**Tech Stack:** Python 3.12 standard library, unittest, GitHub Actions YAML, GitHub Contents/Actions API.

**Spec:** `docs/superpowers/specs/2026-10-31-forcing-archive-recovery-design.md`

## Global Constraints

- Research / Shadow Evaluation / Not Operational.
- Preserve NOAA MLLW and direct USGS MAUL1 63160 NAVD88 gates; never convert 00065 to 63160.
- Preserve old receipts and archived Phase 6 forecasts; append actual retrievals only.
- Recovery rows carry current acquisition time and never claim availability before that time.
- Keep MRMS outside scheduled collection until the captured GRIB passes metadata/timestamp verification.
- Do not add new scheduled workflows or generated archive report blobs.

## Review Focus

- Six-hour collector gap: assert all provider-returned valid times are retained with recovery classification and actual current `retrieved_at`.
- USGS pagination: assert following pages preserves all rows and raw hashes.
- NOAA range boundary: assert windows stay within the documented 31-day limit and keep MLLW in water-level requests.
- Receipt revision: assert changed values/status/QC at one valid time append while identical receipts deduplicate.
- Issue-time audit: assert rows retrieved after an issue are excluded even when their `valid_time` is earlier.

---

### Task 1: Provider history recovery and receipt provenance

**Files:**
- Modify: `scripts/collect_nwcl1_forcing.py`
- Modify: `scripts/validate_forcing_archive.py`
- Test: `tests/test_collect_nwcl1_forcing.py`
- Test: `tests/test_forcing_archive.py`

**Interfaces:**
- Keep `collect(out_dir, now=None, opener=None, sleeper=time.sleep)` as the injected-clock/injected-network entry point.
- Add NOAA range URL/chunk helpers and USGS continuous URL/page helpers; all parsers receive the actual acquisition timestamp and content-addressed raw path.
- Add `acquisition_mode` (`prospective` or `delayed_recovery`) to observation receipts; `retrieved_at` remains actual request completion UTC.

- [ ] **Step 1: Write failing tests** for NOAA date-range URL parameters, bounded NOAA windows, USGS OGC continuous `time` filters, USGS pagination, recovery tagging, prior-receipt immutability, revision-aware deduplication, and a six-hour collector outage.
- [ ] **Step 2: Run the targeted tests and confirm the expected failures.**

Run: `python -m unittest tests.test_collect_nwcl1_forcing tests.test_forcing_archive -v`

Expected: failures for missing range acquisition/pagination/classification and the six-hour recovery assertions.

- [ ] **Step 3: Implement bounded range acquisition** that starts from the earliest receipt on first recovery, then uses an overlapping source watermark; keeps NOAA windows within its documented limit; follows USGS `next` links; retains each raw page and response metadata; and records actual retrieval times.
- [ ] **Step 4: Keep append-only deduplication revision-aware** by including source-reported approval/QC/modification and accumulation metadata in semantic identity; do not rewrite or remove any existing receipt.
- [ ] **Step 5: Re-run targeted tests.**

Run: `python -m unittest tests.test_collect_nwcl1_forcing tests.test_forcing_archive -v`

Expected: PASS, including six-hour gap recovery with observation valid times unchanged and retrieval times set to the injected post-gap clock.

### Task 2: Archive completeness and availability report

**Files:**
- Create: `scripts/archive_completeness.py`
- Create: `tests/test_archive_completeness.py`

**Interfaces:**
- Add `build_report(root, issue_times=None) -> dict` and a CLI with JSON output plus an optional GitHub step-summary append.
- Input receipts remain JSONL under `research/prospective-forcing-archive/receipts/`; issue times come from authentic attempt records in `site/data/prospective/attempts/`.

- [ ] **Step 1: Write failing tests** for unique timestamps, cadence and gap statistics, observed retrieval latency, repeated values, revisions, recovered/prospective counts, and issue-time feature availability.
- [ ] **Step 2: Run the new tests and confirm failures** because the report module is not present.

Run: `python -m unittest tests.test_archive_completeness -v`

Expected: import/function failures for the report contract.

- [ ] **Step 3: Implement the report** with deterministic grouping by source/station/parameter/variable; compute cadence from unique valid times, preserve revisions as counts, and only mark a record issue-available when both valid and actual retrieval times are no later than the issue time.
- [ ] **Step 4: Run the report tests.**

Run: `python -m unittest tests.test_archive_completeness -v`

Expected: PASS for all coverage and issue-availability fixtures.

### Task 3: Workflow safety, operational documentation, and archive/MRMS assessment

**Files:**
- Modify: `.github/workflows/forcing-archive.yml`
- Modify: `.github/workflows/site.yml`
- Modify: `docs/prospective-forcing-archive.md`
- Modify: `docs/rainfall-tributary-observation-acquisition.md`
- Modify: `research/local-forcing-feasibility/source_inventory.json`
- Test: existing publisher and collector/report suites

- [ ] **Step 1: Add workflow assertions/documented validation** for completeness summaries, safe use of `.github/scripts/publish-with-rebase-retry.sh`, archive-only `paths-ignore`, and continued absence of MRMS from scheduled collection.
- [ ] **Step 2: Run focused existing tests** and confirm the changed workflow/docs do not alter collector assumptions.
- [ ] **Step 3: Update operations and source notes** with the October 25–31 baseline run/status counts, source coverage/latency, NOAA/USGS range query provenance, Git/API growth baseline, site rebuild scope, NOAA MRMS product-table definition and captured decoder discrepancy, and NLDI upstream-catchment provenance.
- [ ] **Step 4: Run all repository unit tests and relevant smoke/syntax checks.**

Run: `python -m unittest discover -s tests -v`

Expected: PASS; report any pre-existing failure with its output, do not alter archived forecast/model artifacts.

- [ ] **Step 5: Review the diff and create a reviewable, unmerged pull request** targeting the current `main` SHA inspected for this task.
