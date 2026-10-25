# Plan: rainfall and tributary observation acquisition

**Worktree:** `/tmp/maul1-rainfall-tributary-observations`  
**Branch:** `feature/rainfall-tributary-observations`  
**Base:** current main `6f110d3852d5473d2ff65942b2018bc04d38578f`  
**Spec:** `docs/superpowers/specs/2026-10-25-rainfall-tributary-acquisition-design.md`

## Global constraints

- Extend PR #60 receipt handling and reuse `validate_forcing_archive.py`, `fetch`, raw hashing and append-only receipts; do not fork the same provider acquisition logic.
- USGS 00045 remains accumulated precipitation with actual provider timestamp; never imply a rate or unreported accumulation interval.
- USGS 00065 remains station-native stage. No stage-to-discharge conversion or cross-datum subtraction.
- New candidate feeds remain noncritical to existing NOAA/USGS core collection; their individual health states must persist.
- MRMS must only archive area aggregates and required provenance, not full continental GRIB grids.
- Preserve Phase 6, authentic forecast archives, model features, dashboard and existing collector behavior.
- No predictive or causal claim; report only source verification and descriptive archive coverage.

## Task 1 — Add USGS local-rain and tributary schema coverage (TDD)

**Files:** `tests/test_collect_nwcl1_forcing.py`, `scripts/collect_nwcl1_forcing.py`, `scripts/validate_forcing_archive.py`

1. Add failing fixtures for parsing 00045 with inches, actual time, optional accumulation interval, series ID, qualifiers and raw provenance; reject malformed/nonfinite and unsupported units.
2. Add failing source-registry tests for USGS 301828090363100 00045; 07379960, 07378810, 07378746 00045 and 00065; assert no 00060 is requested for these sites and all new feeds are optional.
3. Extend USGS variable/unit parsing and metadata. Preserve 00065 native datum. Store 00045 as `precipitation` with semantic metadata and never infer rate/interval.
4. Verify old DENL1/MDLL1/MAUL1 inputs and parsing remain unchanged.

**Expected:** new tests fail before parser changes, pass afterward; existing collector fixtures stay green.

## Task 2 — Include candidate series in receipts and health (TDD)

**Files:** `tests/test_collect_nwcl1_forcing.py`, `scripts/collect_nwcl1_forcing.py`, `tests/test_forcing_archive.py`

1. Add failing checks that the source loop visits every registry site, assigns per-parameter criticality, and reports latest valid time, empty/failed status and invalid feature counts.
2. Add duplicate identity cases for separate time-series/sensor IDs and parameter codes while retaining exact receipt deduplication.
3. Implement the generalized source loop and identity-aware duplicate key; confirm the existing NWCL1 core failure behavior is unchanged.

**Expected:** candidate empties do not enter `critical_failures`; core failures still do; repeated exact receipt is skipped and distinct series identity is retained.

## Task 3 — Build a bounded MRMS basin aggregation path (TDD)

**Files:** new `scripts/collect_mrms_basin_qpe.py`, `tests/test_collect_mrms_basin_qpe.py`, `research/local-forcing-feasibility/mrms-requirements.txt`

1. Write deterministic synthetic tests for a simple polygon/grid weighted mean, valid-cell coverage, missing/negative pixels, one-hour valid interval, geometry nesting/difference, product identity, raw hash and receipt timestamps.
2. Implement an isolated fetch/decode/aggregate path for official MRMS 01H Pass2 and USGS NLDI basin geometries; validate all provider metadata and reject unsupported grid/period contracts.
3. Append only the three basin-level `forcing-1` precipitation records and an MRMS source-health snapshot to the existing archive. Retain full-grid SHA256 and retrieval URL/headers without saving the whole GRIB.
4. Add a read-only live smoke mode that performs a single latest product fetch and validates NLDI/GRIB contracts without writing the prospective archive.

**Expected:** synthetic aggregation tests pass without network; live smoke is explicit and returns a useful failed/unavailable health report if blocked or incompatible.

## Task 4 — Integrate optional collection and update source documentation (TDD)

**Files:** `.github/workflows/forcing-archive.yml`, `docs/prospective-forcing-archive.md`, `docs/rainfall-tributary-observation-acquisition.md`, `research/local-forcing-feasibility/source_inventory.json`, `research/local-forcing-feasibility/report.md`

1. Expand the PR workflow path filters and live smoke steps for the new USGS feeds and MRMS proof.
2. In scheduled Actions, keep the existing collection first; run MRMS in a separately health-reported step that cannot suppress core collector persistence. Install optional MRMS dependencies only in its step.
3. Document station identity, parameters, status evidence, observation semantics, datum/QC/gaps, MRMS product/geometry/cost/latency, duplicate/gauge-influence caveats, and no-skill status.
4. Record the actual hosted live smoke findings; if any endpoint cannot be verified, leave its current status explicitly unverified.

**Expected:** workflow syntax and path triggers are valid; smoke failures remain visible in health/CI without changing forecasts or the existing archive namespace.

## Task 5 — Full verification and PR

1. Run focused package tests and all repository tests; run compile checks and `git diff --check`.
2. Review the full diff against current main and confirm only acquisition, documentation, tests and workflow files changed; check Phase 6 and dashboard artifacts are unchanged.
3. Push `feature/rainfall-tributary-observations`, open a PR against `main`, inspect the hosted PR smoke result and update docs/implementation if needed.
4. Keep the PR open and unmerged.
