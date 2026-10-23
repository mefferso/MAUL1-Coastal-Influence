# Phase 9 implementation plan

Base: `main` at `5a97ec743bd668c173b3373b8ea7868510048879` (Phase 8 merge).

## Current architecture

`site/index.html` is a static single-page app. `site/app.js` renders historical event charts and Phase 3B–5B research panels. `site/phase6.js` reads immutable prospective latest/history archives and performance JSON, presenting authentic forecasts and verification. `.github/workflows/phase6.yml` serializes hourly issue/verification archive updates; `.github/workflows/site.yml` validates and deploys `site/` to Pages on main. Phase 6’s issue record includes latest raw source observations, datum/QC/provenance, completed-bin feature diagnostics and the frozen forecast output. The compact `latest.json` omits underlying raw values such as features; the dashboard must hydrate the latest authentic full issue record through its history index.

## Scope and file responsibilities

- `site/index.html`: create a focused Research Dashboard section above historical study panels; move the existing Phase 6 panel into it, retain all historical sections below.
- `site/research-dashboard.js`: render source-stamped current conditions and five-station evidence availability from the latest authentic archive; never infer NAVD88 or causality.
- `site/style.css`: responsive layout and accessible status/table styling for the new dashboard.
- `tests/research-dashboard-smoke.cjs`: pure rendering regression checks for data, stale/missing inputs, unverified MCHL1 and datum gates.
- `.github/workflows/site.yml`: syntax-check and run the new dashboard smoke test during existing PR validation.
- `docs/research-v1.md`: purpose, network, provenance, architecture, verified Phase 7/8 findings, authentic prospective status, scientific limitations and maintenance guidance.
- `README.md`: point users to the release guide and clarify research application purpose.

## Tasks

1. Add failing rendering tests for freshness/stale values, native stage vs NAVD88, threshold hard gate, station status and missing inputs.
2. Implement a pure dashboard renderer and browser bootstrap that hydrates only the latest authentic issue. Display explicit indeterminate evidence classification when screen inputs are incomplete; retain source/status/QC/valid-time/retrieval-time information.
3. Add dashboard markup, responsive styles and relocate the existing Phase 6 panel without changing forecasts or archival behavior.
4. Add CI checks and comprehensive release documentation using existing Phase 7/8 and Phase 6 results, not new model metrics.
5. Run focused Node tests and available regression checks; open a PR against `main`, inspect workflow checks, resolve failures, request review, merge only when required checks pass, then verify Actions deployment and published page.
