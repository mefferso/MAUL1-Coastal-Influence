# Phase 6.18 Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve the shared visual system and Current Forecast usability while preserving all scientific values, calculations, archive records, and existing view behavior.

**Approach:** Add tests first for CSS/responsive semantics and the forecast content contract, then make localized HTML, forecast template, Plotly presentation, and CSS changes. Use existing dependencies and archive-backed renderers.

**Files:**
- `tests/navigation-forecast-smoke.cjs`: asserts four-view navigation, accessible Current Forecast, shared tokens, responsive breakpoints, chart controls, and retained progressive disclosure.
- `tests/phase6-ui-regression.cjs`: dedicated regression tests for native-stage/freshness/tendency content, stale/missing/withheld states, datum distinction, exact preserved forecast values, disclosure model rows, and layout rules.
- `site/index.html`: improve Current Forecast structure and chart accessible description; retain all view panels, script order, IDs required by existing code, links, and datasets.
- `site/forecast-view.js`: improve current forecast semantic structure/class hooks and exact-state copy without changing record selection, numeric calculations, model names, source eligibility, or values.
- `site/phase6.js`: improve Plotly layout/config and preserve existing traces and data while enabling hover, zoom, pan, and reset.
- `site/style.css`: define design tokens and shared shell, typography, navigation, card, focus, table, and responsive rules.
- `site/research-dashboard.css`: align forecast/network cards to tokens and define Current Forecast responsive components.
- `docs/phase6-18-ui-redesign.md`: explain the visual hierarchy, immutable/scientific boundaries, accessibility, and limitations.

### Task 1: Forecast and dashboard UI regression tests

1. Add tests for all four views, title/status, forecast semantics, the 00065 vs NAVD88 boundary, unchanged values/model labels, observation fresh/stale/missing behavior, no-observation chart handling, disclosure tables, Plotly interaction options, reusable tokens, and mobile/desktop breakpoints.
2. Run the new tests and confirm failures identify missing UI contracts.

### Task 2: Forecast markup and chart presentation

1. Update the forecast panel wrapper and chart description/region semantics in `site/index.html` without changing existing IDs used by application code.
2. Refactor only the forecast output markup in `forecast-view.js` to expose stable semantic blocks/classes for stage, freshness, tendency, and forecast horizons; retain exact selection/eligibility/numerical logic and strings that communicate scientific limitations.
3. Adjust the Plotly layout and config in `phase6.js` for readable labels, legend, hover, and built-in interactions. Preserve `buildTraces` output and all trace data.
4. Run forecast, Phase 6 dashboard, and accessibility-structure tests.

### Task 3: Shared visual system and responsive layouts

1. Add design tokens and shared component rules in `style.css`.
2. Align forecast and research dashboard styles in `research-dashboard.css`, including desktop layout, tablet stacking, narrow mobile cards, long labels/tables, and visible focus.
3. Run visual regression smoke tests and inspect browser support availability. Save screenshots if browser tooling exists.

### Task 4: Documentation and full verification

1. Document before/after design intent, preserved scientific contracts, status behavior, screenshot/tooling evidence, and adoption-ready tokens.
2. Run full Python suite, all relevant JavaScript syntax/smoke tests, reproducibility checks required by CI, and static served-asset smoke validation.
3. Confirm archive/model/verification paths and scientific calculations have no diff; review final file list and create a focused PR.
4. Review required checks and deployment. Merge only when checks pass and immutable evidence remains unchanged; verify published Pages outcome.
