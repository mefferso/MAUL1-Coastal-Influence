# Prospective coastal forcing observation archive — Phase A

**Research / Shadow Evaluation / Not Operational**

This is the first safety-critical building block for an **actual, issue-time auditable** forcing archive. It is **not** yet a live collector, a historical reconstruction, or a forecast change. In particular, the existence of these files does not mean observations have been fetched or archived.

## Scope and priority

1. **NWCL1 (NOAA CO-OPS 8761927):** raw wind vectors (east/north components in knots), water level and *same-datum* astronomical prediction. Preserve raw source response and provider status separately.
2. **MDLL1:** native water-level changes, source/sensor metadata and receipt timestamps.
3. **DENL1:** native discharge and stage, distinguished from coastal forcing.
4. **MAUL1:** native parameter `00065` for stage-change analysis; direct `63160` NAVD88 only when actually reported. Never infer a historical conversion.
5. **Independent Mid-Lake wind station:** add only after verifying a currently accessible raw data endpoint, sensor identity, height, averaging cadence, and historical continuity. WeatherFlow Mid-Lake 2024 records have not been recovered.
6. **PR #58 candidate stations:** add only after checking genuine current reporting, source ownership, datum, duplicate feeds, historical gaps, and API reliability.

Do not use FREL1 as a current observation source without evidence. MCHL1 remains shadow-only.

## Receipt schema (`forcing-1`)

Each newline in a dated JSONL batch is an independent **provider receipt**, not a model-ready hourly aggregate. Required fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Exactly `forcing-1` |
| `station_id`, `source`, `raw_id` | Station, upstream provider/feed identity, and original observation key |
| `variable`, `unit`, `datum` | Typed measurement; use `not_applicable` for wind/discharge, `unspecified` for uncertain water datum |
| `valid_time` | Actual observation/forecast valid time, UTC ISO8601 |
| `retrieved_at` | Actual provider retrieval time, UTC ISO8601 — never reconstructed from valid time |
| `value` | Finite numeric reading, or null if missing/rejected |
| `status`, `qc_flags` | Provisional/observed/missing/rejected and explicit QC annotations |

Optional fields for implementation: `product`, `provider_updated_at`, `sensor_id`, `sensor_metadata_version`, `observation_period_seconds`, `provider_url`, `raw_sha256`, `raw_path`, `fetch_status`, `retrieval_run_id`. Retain original provider payloads in immutable content-addressed raw files rather than silently normalizing away revisions.

**Important:** a `retrieved_at` timestamp proves only when *our collector saw the value*, not when it first became available. A provider publication timestamp, if reported, is additional evidence; don't fabricate it. For historical datasets without real receipts, use an explicitly different historical archive namespace and never populate `retrieved_at` with guessed dates.

## Validation

```bash
python -m unittest tests.test_forcing_archive -v
python scripts/validate_forcing_archive.py path/to/actual-observations.jsonl
```

No fictitious observation records are committed. Validation rejects missing provenance, improper units, unzoned dates, duplicate receipt keys within a batch, invalid values, and receipt times before valid times. Source-specific collector code must additionally enforce provider-specific QC and sensor/datum lineage; this validator does not certify physical validity.

## Next implementation increment — acquire, persist, and schedule real observations

- Build a small standard-library collector for the official NWCL1 provider endpoint, persisting raw response bytes, HTTP/retrieval status, actual receipt timestamp, explicit valid times, provenance/version metadata, and checked `forcing-1` receipts.
- Run live endpoint integration checks **before** claiming the connector is operational.
- Establish reliable recurring collection with failure/coverage diagnostics and a clear missed-run policy. If using GitHub Actions, verify scheduling, artifact retention, storage growth, permissions, deployment segregation and API rate limits. Do not fabricate observations for outages.
- In a subsequent increment, include MDLL1, DENL1, MAUL1, and verified independent wind feeds with distinct source metadata.
- Archive model issuance timestamps and receipts independently; permitted issue-time features may only consume actual receipts recorded by issuance.
- Only after coverage and QC testing: predeclare directional wind-duration/stress/relaxation features, compare against frozen baselines on a future evaluation period, and report missed rises **and** false alerts.

Never modify frozen Phase 6 forecast artifacts or genuine issuance/verification logs. No operational thresholds or advisory recommendations.
