# Dashboard guide — v1.1.0 candidate

**Research / Shadow Evaluation / Not Operational**

The application opens to **Current Forecast**. Use the keyboard arrows, Home/End, or a click to move between the three views. The selected view is reflected in the URL fragment so a view can be linked directly.

## Current Forecast

The first card shows the latest authentic archived MAUL1 observation, its valid and retrieval times, freshness, source quality, datum, and recent six-hour change where present. The compact network cards show DENL1 discharge, NWCL1 lake/wind context, MDLL1 native gage height, and MCHL1 shadow-only context. The observation screen calls the overall evidence indeterminate unless the complete evidence screens are available; the individual measurements are not a causal coastal-versus-river classification.

The 6-, 12-, and 24-hour panels show forecast valid time, effective lead, persistence stage, and the spread of available frozen model outputs. Expand model details to inspect each native-stage value, change, and archived interval. No model is preferred. Model spread is not a calibrated probability range or confidence interval. The chart joins only the anchor and forecast horizons from the same authentic issuance. It does not connect separate historical issuances. Its vertical reference is native MAUL1 USGS 00065 gage height.

A separate direct USGS 63160 NAVD88 observation remains shown only when eligible under the existing freshness, QC, chronology, and provenance checks. It is not mixed into the native-stage forecast chart. The 4.0 ft NAVD88 threshold is never drawn or calculated on the native-stage axis.

## Forecast Verification

This view retains the authentic prospective Phase 6 archive, immutable issue selector, subsequent observation records, scorecard, persistence comparison, event group counts, interval coverage, observation delays, and completeness. It is separate from historical hindcasts. Forecast rows overlap in time; a small row count does not equal an independent event sample. Model superiority remains unestablished when independent rising-water events are insufficient.

## Historical Research

Historical event replay, station plots, map, onset analysis, independent event diagnostics, interpretation, lag correlations, quality reports, continuous event discovery, Phases 3B–5B, Phase 7 cleaning, Phase 8 precursor findings, methods, and provenance remain in this view. The historical toolbar is scoped to this view. When opened, charts and the map are resized so hidden-view initialization does not leave them blank.

The v1.1 redesign changes navigation and presentation only. It does not modify forecast calculations, source archives, verification records, model artifacts, or event classifications. MCHL1 remains unverified, shadow-only, and forecast-ineligible. Native MAUL1 `00065` remains distinct from direct `63160` NAVD88 elevation. The v1.0.0 tag remains unchanged; v1.1.0 is not released until its checks, deployment, and interactive published-page verification are complete.
