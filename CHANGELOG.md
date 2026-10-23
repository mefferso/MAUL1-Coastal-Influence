# Changelog

## v1.0.0 release candidate — 2026-10-23

**Status: Shadow Evaluation / Not Operational. The release tag is held pending interactive verification of the published page.**

- Consolidates the latest authentic MAUL1 observation context, DENL1/NWCL1/MDLL1/MCHL1 context cards, and authentic 6-, 12-, and 24-hour Phase 6 forecast guidance.
- Keeps persistence comparisons and prospective verification separate from historical hindcasts and Phase 8 retrospective precursor screens.
- Shows source provenance, observation freshness, missing inputs, model artifact identity, verification counts, errors, and uncertainty intervals where available.
- Preserves native MAUL1 00065 stage; the 4.0 ft NAVD88 reference is considered only for a separate, fresh, eligible USGS 63160/NAVD88 record.
- Keeps MCHL1 unverified, shadow-only, and excluded from frozen forecasts; no Phase 5 model or authentic issuance archive was changed.
- Adds regression checks for malformed, future, stale, and inconsistent timestamps/QC, direct-elevation gating, missing values, and accessible scrollable forecast tables.
- Documents current prospective sample sizes and the limits of historical coastal-versus-river precursor findings.

See [Research v1.0 documentation](docs/research-v1.md) for methods, limitations, operating instructions, and troubleshooting. This software does not issue warnings or establish coastal causation or operational forecast skill.
