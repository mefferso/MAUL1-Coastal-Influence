# Changelog

## v1.1.0 candidate — 2026-10-23

**Status: Research / Shadow Evaluation / Not Operational. Release tag pending checks, deployment, and interactive published-page verification.**

- Reorganizes the application into Current Forecast, Forecast Verification, and Historical Research views; Current Forecast opens by default.
- Adds 6-, 12-, and 24-hour single-issuance forecast summaries, persistence comparisons, model details, valid times, and a native-stage chart using one authentic issuance at a time.
- States that no preferred model has been established and labels model-output spread separately from archived model intervals.
- Keeps historical events, five-station charts, map, forcing evidence, hindcasts, data-quality findings, and precursor research accessible in Historical Research.
- Preserves the immutable v1.0.0 release, all data archives, frozen models, and the Phase 6 prospective scorecard.
- Adds accessible keyboard-operable view navigation and regression checks for views, forecast chronology/datum, missing horizons, and single-issuance chart traces.

See [Dashboard v1.1 guide](docs/dashboard-v1.1.md) for the new navigation and display interpretation. The v1.1.0 release tag remains pending until required checks, deployment, and interactive live-site verification succeed.

## v1.0.0 — 2026-10-23

**Status: Released baseline · Shadow Evaluation / Not Operational.** The v1.0.0 release and tag are preserved unchanged.

- Consolidates the latest authentic MAUL1 observation context, DENL1/NWCL1/MDLL1/MCHL1 context cards, and authentic 6-, 12-, and 24-hour Phase 6 forecast guidance.
- Keeps persistence comparisons and prospective verification separate from historical hindcasts and Phase 8 retrospective precursor screens.
- Shows source provenance, observation freshness, missing inputs, model artifact identity, verification counts, errors, and uncertainty intervals where available.
- Preserves native MAUL1 00065 stage; the 4.0 ft NAVD88 reference is considered only for a separate, fresh, eligible USGS 63160/NAVD88 record.
- Keeps MCHL1 unverified, shadow-only, and excluded from frozen forecasts; no Phase 5 model or authentic issuance archive was changed.
- Adds regression checks for malformed, future, stale, and inconsistent timestamps/QC, direct-elevation gating, missing values, and accessible scrollable forecast tables.
- Documents current prospective sample sizes and the limits of historical coastal-versus-river precursor findings.

See [Research v1.0 documentation](docs/research-v1.md) for methods, limitations, operating instructions, and troubleshooting. This software does not issue warnings or establish coastal causation or operational forecast skill.
