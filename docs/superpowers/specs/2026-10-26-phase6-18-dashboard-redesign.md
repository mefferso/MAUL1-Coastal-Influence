# Phase 6.18 Research Dashboard UI Design

## Intent

Make the research dashboard feel like one professional meteorological research product, with a clear entry point at Current Forecast. Help readers quickly distinguish the latest authentic MAUL1 native 00065 stage and its source freshness from experimental guidance at 6, 12, and 24 hours. Keep the other three views and all research datasets available.

## Goals

- Establish reusable color, spacing, typography, border, status, and surface tokens in the existing CSS stack.
- Give Current Forecast a clear hierarchy: research status, current native-stage evidence, source age and supported recent tendency, then experimental horizon guidance and an interactive Plotly chart.
- Keep detailed model comparisons behind keyboard accessible disclosure controls.
- Make stale, missing, withheld, and unavailable conditions explicit without assigning operational risk colors or recommendations.
- Maintain responsive behavior, accessible navigation, and existing links and datasets.
- Add regression coverage for desktop/mobile layout rules, status copy, scientific labels, progressive disclosure, accessible chart presentation, and all four views.

## Non-goals and constraints

- No prediction, feature, verification, datum, or metric changes.
- No modifications to immutable authentic issues, verification revisions, model artifacts, or source archives.
- Do not treat native 00065 and direct NAVD88 63160 as equivalent; the Current Forecast chart remains limited to eligible native 00065 data and model guidance.
- Do not add dependencies or external paid services.
- Retain the existing four views, links, datasets, model names, values, availability, and scientific caveats.

## Approaches considered

1. **CSS-only reskin.** Lowest JavaScript risk, but cannot improve the forecast content hierarchy or the Plotly interaction and accessibility settings.
2. **Replace the site shell and rebuild the forecast view.** Allows broad visual control but risks breaking established research views, navigation, and source-to-display safeguards.
3. **Focused progressive redesign of the existing view.** Add shared CSS tokens and component patterns, improve forecast semantic markup, retain the current data selection/rendering rules, and adjust Plotly layout/config only. This preserves the archive-backed behavior while addressing hierarchy, responsiveness, and chart usability.

## Selected approach

Use approach 3. The request specifies the research dashboard direction and asks to preserve working interactions, so changes stay inside the existing HTML/CSS/JS structure. We will present the existing latest observation, observation freshness, six-hour feature change where present, and the same three forecast horizons more clearly. The model detail tables remain in `<details>`. The chart keeps the current exact traces and datums while exposing Plotly’s interactive controls and a clearer visual layout.

## Design details

- Add CSS custom properties for ink, muted text, ocean accent, paper/surface, borders, spacing, radii, shadow, content width, and focus ring. Use neutral status pills with text; avoid warning/risk color semantics.
- Improve shell/header and four-view tab spacing, focus/selected states, and narrow-screen horizontal tab use without changing tab behavior or hash links.
- Render the current native-stage model anchor and latest eligible observation as distinct labeled evidence blocks. Retain the observation’s freshness and retrieval timestamps and retain the existing feature-time tendency calculation/output.
- Keep 6/12/24 cards in a readable grid where space permits, stack them on mobile, and preserve their model-comparison disclosure tables.
- Keep the native-stage forecast chart separate from direct 63160 NAVD88 content, label valid time and units, preserve issue-time marker and trace values, and enable standard Plotly hover/zoom/pan/reset interactions.
- Preserve current missing and stale copy paths; give the chart a programmatic name and adjacent text description/fallback.

## Verification

- Add focused Node UI regression checks and extend current navigation/forecast smoke tests.
- Run full Python tests and all relevant Node syntax/smoke tests.
- Run a local static-server smoke check for all linked assets and dashboard data paths.
- Inspect computed responsive layout where a browser runtime is installed. Save before/after screenshots if available; otherwise record the tooling limitation.
- Confirm the diff excludes `site/data`, model artifacts, and verification calculations.
- Use GitHub PR checks and Pages deployment outcome for publication validation.
