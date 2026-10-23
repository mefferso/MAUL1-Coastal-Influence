# v1.1 Forecaster Dashboard Redesign

## Intent
Make the public static application understandable to LIX forecasters in its first screenful while preserving all v1.0.0 research and data.

## Goals
- Three accessible views: Current Forecast (default), Forecast Verification, Historical Research.
- A compact current conditions and single-issuance forecast overview, including persistence, model spread, valid times, and uncertainty only where archived.
- Preserve the full prospective scorecard and all historical event tooling in their own views.
- Keep the application labeled Research / Shadow Evaluation / Not Operational.

## Non-goals and anti-goals
No changes to model inference, forecast archives, historical datasets, verification metrics, event classifications, or model preference. No conversion of native MAUL1 00065 to NAVD88 and no operational advice.

## Approaches
- Separate pages: clearer boundaries but duplicates loading and complicates static deployment.
- Progressive disclosure with accessible tabs around existing modules: recommended because it preserves the current static architecture and calculation/data pipelines.
- Rebuild as a framework application: adds dependencies and regression risk without scientific benefit.

## Implementation
Keep the existing current-observation renderer and Phase 6 scorecard. Add accessible keyboard-operated views; move historical controls/charts into Historical Research, prospective scorecard/archive into Forecast Verification, and render one-issuance native-stage guidance plus a chart in Current Forecast. The chart may connect only same-issuance valid-time points. Keep full model values expandable and state no preferred model exists.

## Verification
Add focused navigation and forecast rendering regression tests; run focused Node tests plus available repository workflows. Do not create v1.1.0 tag until checks, deployment, and interactive live browser inspection succeed. v1.0.0 remains immutable.
