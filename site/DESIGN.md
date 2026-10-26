# Design A — Forecaster Console

This is a static, read-only research preview. It uses the production frontend and the fixed production data tree from commit `e236d8946fe7acbfb764f1ba60960f9bb806881e` (2026-10-26 15:03:15 UTC). The snapshot is not refreshed in the preview. No collectors, forecast issuances, authenticated requests, or archive writes are included.

## Scientific presentation rules

- The persistent status strip above navigation reads **RESEARCH / SHADOW EVALUATION / NOT OPERATIONAL**. It explicitly says the page contains archived experimental evidence and has no warnings or advisory recommendations.
- MAUL1 stage and its forecast guidance use native USGS 00065 gage height. Direct USGS 63160 NAVD88 elevation appears only in its own separate datum treatment; the 4.0 ft NAVD88 comparison is never applied to 00065.
- MCHL1 is marked “shadow-only” and “forecast-ineligible” in the station list and map popup.
- Prospective verification and retrospective hindcast evidence remain in separate views. Skill values retain their sample counts and maturity labels. Historical hourly windows retain their existing overlap caveats.
- Model bounds retain their archived within-model meaning. Model spread is not shown as calibrated cross-model uncertainty or flood probability.
- Missing, stale, withheld, abstained, unavailable, and error states retain explicit text labels and use quiet neutral status styling.

## Shared design tokens

Defined in `style.css` and consumed by the other view stylesheets:

| Token group | Tokens | Use |
|---|---|---|
| Surfaces and text | `--color-page`, `--color-surface`, `--color-surface-soft`, `--color-ink`, `--color-muted` | Page, cards, secondary text |
| Brand and focus | `--color-ocean`, `--color-ocean-dark`, `--color-accent`, `--color-focus`, `--focus-ring` | Header, selected tab, links, keyboard focus |
| Borders and spacing | `--color-border`, `--color-border-strong`, `--space-*`, `--radius-*`, `--shadow-card` | Shared geometry and separation |
| Status | `--color-status-bg`, `--color-status-ink` | Neutral labels for data state, never risk severity |
| Datum | `--color-navd88` | Direct NAVD88 plot series only |
| Stations | `--station-denl1`, `--station-nwcl1`, `--station-mdll1`, `--station-mchl1`, `--station-maul1` | Station list, maps, and research plots |
| Models | `--model-persistence`, `--model-phase5a-maul1-only`, `--model-phase5a-coastal`, `--model-phase5b-coastal-tidal`, `--model-phase5b-full-multivariable`, `--model-challenger` | Forecast traces, diagnostics, and model swatches |

The type stack uses installed UI/system fonts with sans-serif fallbacks; all numeric scientific values use tabular numerals. No remote font is required.

## Model and station colors

`chart-theme.js` is the shared chart color source and mirrors the CSS tokens:

| Series | Color |
|---|---|
| DENL1 | `#a3592a` |
| NWCL1 | `#147d92` |
| MDLL1 | `#7562a5` |
| MCHL1 (shadow-only) | `#806649` |
| MAUL1 native 00065 | `#173f5f` |
| Persistence | `#68767e` |
| Phase 5A MAUL1-only | `#317c9a` |
| Phase 5A coastal | `#7562a5` |
| Phase 5B coastal + tidal | `#b56b2b` |
| Phase 5B full multivariable | `#3d7868` |
| Damped-trend challenger | `#b45260` |
| Direct 63160 NAVD88 | `#158177` |

All plots use the shared Plotly font, UTC hover/readout style, persistent legend, responsive layout, and restrained hover mode bar. Per-chart axes continue to state their units and datum. Plotly and Leaflet remain pinned to the site's existing CDN versions; the map uses its existing OpenStreetMap tile source.

## Components and responsive layout

- Compact console identity header, preview label, persistent research-status strip, and four keyboard-operable deep-linked tabs.
- Current Forecast: native stage and freshness first; existing 6/12/24-hour guidance follows with model identity and valid times; the full single-issuance trajectory follows; then the station map/list. Detailed source diagnostics remain under “Detailed source and datum notes.”
- Shared cards, status labels, forms, scrollable tables, disclosure summaries, and Plotly chart framing across all four views.
- At desktop widths the network map and current station list sit side by side. At 390 px they stack; horizon cards stay in a compact three-column row, long tables scroll inside their own labeled regions, and the page does not gain horizontal overflow.
- Visible keyboard focus, roving tab navigation, keyboard-enabled map markers, and reduced-motion support.

## Existing feature inventory retained

- **Current Forecast:** authentic issuance freshness and cycle history; MAUL1 native-stage anchor and eligible observation; source time, retrieval time, QC, and freshness; observed recent native-stage tendency; 6/12/24 guidance; each existing model and status; valid times and effective lead; archived within-model intervals and caveats; interactive single-issuance chart; current condition station cards; source links; NWCL1 residual/wind, DENL1, MDLL1, and MCHL1 context; separate direct 63160 NAVD88 availability/threshold treatment; model details and diagnostics.
- **Forecast Verification:** rolling-window and horizon selectors; stage, MAE, and error charts; scorecard; paired sample counts, maturity and due/unverified states; prospective evidence readiness; archive cycle history; immutable issuance selector and forecast details; verification revisions, model artifacts, performance archive links, and methodology caveats.
- **Historical Research:** event selector, replay-through-UTC control and reset; DENL1 discharge, NWCL1 water/residual, MDLL1, MCHL1, MAUL1, and NWCL1 wind plots; station map and coordinates; coverage, retrieval/quality, and discovery context; onset timing, independent-response episodes, and timing matches; Phase 3B, Phase 4, Phase 5A, and Phase 5B reports, case studies, model comparisons, uncertainty report, provenance, and downloadable issue-level forecast data.
- **Model Lab:** horizon, verification regime and historical case selectors; paired metrics and uncertainty; annual/seasonal robustness; predictor-family ablations; rise detection/false-alert and input-coverage reports; trajectory and threshold timing; selected historical case chart; event failure diagnostics; significant-rise investigation and event explorer; predictor context plots; diagnosis and limitations; methodology, provenance, promotion criteria and linked machine-readable reports.

Every prior dataset or report link remains in its original view. Internal assets and data use relative paths from the static site root, including the `/MAUL1-Preview-A/` Pages base path.
