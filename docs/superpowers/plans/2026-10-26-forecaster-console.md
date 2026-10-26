# Forecaster Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task. Keep the source branch unmerged.

**Goal:** Build Design A as a coherent four-view research dashboard and publish a static, read-only preview at a separate GitHub Pages project URL if repository permissions allow.

**Architecture:** Preserve the existing static HTML/JS application and scientific data contract. Add shared CSS and Plotly tokens, improve only presentation and path handling, add a visible Current Forecast station network using current verified coordinates, and package the existing frontend plus referenced read-only data snapshot separately. The production repo receives a draft PR only.

**Tech Stack:** Existing HTML, CSS, vanilla JavaScript, Plotly, Leaflet, Python/Node test suites; GitHub Pages only.

## Files and responsibilities

- `site/index.html`: compact header, persistent status banner, Current Forecast order and visible map/network; preserve all four panels and links.
- `site/style.css`, `site/research-dashboard.css`, `site/phase6-readiness.css`, `site/model-lab.css`, `site/significant-rise.css`: shared tokens and coherent component styling across views.
- `site/chart-theme.js`: shared Plotly layout/config and palette constants.
- `site/forecast-view.js`, `site/phase6.js`, `site/app.js`, `site/performance-explorer.js`, `site/model-lab.js`, `site/significant-rise.js`: route chart and station colors through shared tokens; presentation-only changes.
- `site/network-map.js`: render the default Current Forecast station map/list using coordinates already present in `app.js`; MCHL1 is explicitly shadow-only.
- `site/DESIGN.md`: document design tokens, colors, components, disclaimer placement, feature inventory, and data snapshot provenance.
- `tests/forecaster-console-ui.cjs` and existing JS smoke tests: regression checks for scientific display contracts, navigation, shared palette, map coordinates/status, layout and relative paths.
- `docs/forecaster-console/`: desktop/mobile before/after screenshots for all four views when the browser tool is available.
- Preview repository (only if supported): static frontend and minimum complete read-only site-data snapshot at repo root, plus Pages configuration; no collectors, schedules, authenticated calls, or evidence writes.

## Task 1 — Record baseline

1. Capture the source snapshot SHA/time from production `main` and inspect available app/data path contracts.
2. Record baseline asset sizes for initial HTML/CSS/JS and enumerate all view features/links.
3. Capture four-view desktop/mobile baseline screenshots where browser tooling permits.

## Task 2 — Establish regression coverage (TDD)

1. Add a Node regression test for the persistent research banner, all four panels, default-visible map and station list, 00065/63160 distinction, MCHL1 state, pinned snapshot banner, token/theme use, relative paths, and expected feature links.
2. Run it and verify it fails against the current implementation for the intended missing UI behavior.
3. Add focused tests for map coordinate equality and shared Plotly theme/palette contract.

## Task 3 — Shared design system

1. Define shared page, surface, border, type, spacing, radius, focus, station, and model tokens.
2. Migrate existing view styles to token-driven shared card, heading, table, status, form, disclosure, and chart patterns.
3. Apply responsive and reduced-motion rules; ensure table overflow remains local and contrast/focus states are visible.
4. Run CSS/HTML smoke checks and verify existing tabs still work.

## Task 4 — Current Forecast console

1. Replace the large version hero with a compact identity header and persistent research-only banner; move version metadata to footer/About.
2. Reorder existing current-stage, freshness, tendency, and 6/12/24 guidance fields into the specified reading sequence without changing values or selection behavior.
3. Make the station network visible at load and add a compact map using exact repository coordinates. Explicitly mark MCHL1 shadow-only.
4. Keep all archived forecast traces and use the shared chart theme; preserve the datum split and interval semantics.
5. Keep model-detail and diagnostic sections available via disclosure.

## Task 5 — Shared chart/navigation and other views

1. Apply common chart layout/modebar, persistent legends, UTC hover labels, model/station colors, and resize behavior.
2. Restyle verification, Historical Research, and Model Lab without removing controls, calculations, values, datasets, or linked reports.
3. Test tabs by mouse/keyboard and deep-link selection; test stale/missing/unavailable states.

## Task 6 — Snapshot and preview packaging

1. Use fixed production `main` snapshot `e236d8946fe7acbfb764f1ba60960f9bb806881e`, timestamped 2026-10-26T15:03:15Z, for read-only data; record the digest/provenance in the PR and preview About section.
2. Package only static frontend assets, libraries/CDN references already in use, and data files needed for every retained view/link.
3. Create `MAUL1-Preview-A` and enable Pages from `main` if available; verify it loads at `/MAUL1-Preview-A/`.
4. If GitHub repository/Pages actions are unavailable, configure a downloadable preview artifact on the draft PR if the available workflow permissions allow; do not claim a working URL.

## Task 7 — Verification and review

1. Run all existing Node site smoke tests and complete Python suite; run new UI regression tests.
2. Verify frozen source and scientific artifacts are byte-identical; compare data snapshot hashes.
3. Capture four-view before/after screenshots at ~1440 and 390 px and test chart/map rendering, controls, empty/stale states, and base-path links in a real browser where available.
4. Report initial HTML/CSS/JS payload before/after, preview URL or exact publication blocker/artifact, feature inventory, limitations, and draft PR link. Leave PR unmerged.
