# Design A — Forecaster Console

## Intent

Create a compact, coherent research interface that lets a forecaster understand the current MAUL1 native-stage observation, its source age, and the archived experimental 6/12/24-hour guidance quickly. The visual refresh must keep all four existing views, calculations, records, links, and scientific caveats reachable.

## Goals

- Use a single tokenized visual system across Current Forecast, Forecast Verification, Historical Research, and Model Lab.
- Keep a persistent, conspicuous “RESEARCH / SHADOW EVALUATION / NOT OPERATIONAL” banner.
- Lead Current Forecast with native 00065 stage, source freshness, recent tendency where already supported, named-model guidance and valid times, then the existing trajectory chart.
- Show the current station network and a compact Leaflet map by default, using only coordinates already in `site/app.js`.
- Keep 63160 direct NAVD88 separate from 00065 native stage; preserve the 4.0 ft threshold only for verified direct 63160 observations.
- Preserve MCHL1's shadow-only and forecast-ineligible status, every output value/state/label, and existing research/verification limitations.
- Keep all existing report links, data links, controls, charts, tables, and event explorers reachable through the four views.
- Ensure the static frontend and read-only data snapshot use repository-relative paths and work at a GitHub Pages project base path.
- Document a fixed data snapshot SHA/time, the token system, model/station colors, component patterns, and disclaimer placement.

## Non-goals and anti-goals

- No scientific calculations, source observations, forecast values, model outputs, timestamps, archives, thresholds, or verification results change.
- No forecast issuance, data collection, automated evidence refresh, authenticated calls, warning, probability, advisory, or operational decision language.
- No model selection/ranking by unverified skill, no independent-event claims from overlapping hourly windows, and no reinterpretation of uncertainty intervals.
- No production Pages changes, redirect, replacement, or merge. Design A remains isolated in a separate preview repository if GitHub permissions support it.
- No framework, build step, paid service, or new runtime dependency.

## Approaches considered

1. **Replace only the Current Forecast styles.** Lowest risk, but the other three views would retain competing palettes and spacing. It misses the requested shared design system.
2. **Rebuild the site as a new application.** Allows a clean component model, but adds framework/build/dependency risk and makes preserving all existing scientific views harder.
3. **Restyle the existing four-view static application in place, add shared tokens and small view-level layout helpers, then publish a read-only copy at a separate Pages base path.** This preserves established interactions and data contracts while giving Design A a consistent interface. **Selected.**

## Layout and interaction

- Compact identity header and persistent research-status strip.
- Four keyboard-operable tabs with deep-link hashes.
- Current Forecast: current native stage and freshness, three horizon cards with featured model name/valid time/change, trajectory chart with all existing forecast traces, visible station map and list, then existing detailed diagnostics and model tables in disclosure.
- Verification, Historical Research, and Model Lab keep their controls and outputs, restyled with the same typography, spacing, surfaces, status labels, chart palette, focus treatment, and responsive rules.
- Desktop uses a wide content column with a two-column station map/list region; mobile at 390 px uses one column with no page-level horizontal scrolling. Long tables may scroll inside their own labeled regions.
- Chart theme uses persistent legends, labeled datum/units, UTC hover details, existing documented interval meanings, responsive sizing, and restrained mode-bar options.
- Missing, stale, withheld, abstained, and error states remain text-labeled and visually neutral.

## Implementation calls

- Reuse the existing system font stack and tabular numerals; do not depend on a remote font loading successfully.
- Reuse existing verified station coordinates and existing forecast/observation datasets. No new sensor/network requests are added by the preview.
- All internal asset/data links stay relative to the copied static root; production repository/document links remain explicitly production links.
- If a separate repository cannot be created or Pages enabled with available account actions, publish a downloadable static preview artifact from the draft PR if available and report that no working preview URL exists.

## Approval and scope

The task's detailed requirements authorize this design direction and implementation. The implementation is limited to the requested isolated source branch and a separate preview publication; the production default branch and Pages site are not targets.
