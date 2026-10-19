# Phase 2A Historical Corrections and Event-Onset Analysis

## Goal

Extend the existing five-station historical explorer with provenance-preserving
retrieval, non-interpolated hourly analysis products, experimental event-onset
diagnostics, and an inspectable research-only UI section.

## Design

`scripts/build.py` remains the acquisition boundary. Every MCHL1 source is
queried independently for every event window, with a per-period status of
`retrieved`, `queried_unavailable`, `not_queried`, or `retrieval_error` and no
station relabeling or datum conversion. USGS 00065, 63160, and the existing
−1.38-ft relationship remain separate in the stored rows and threshold logic.

`scripts/analyze.py` becomes the derived-analysis boundary. It creates a
one-hour UTC grid from actual observations only, records per-hour coverage and
missingness, computes the requested station-specific trailing changes and
vector wind statistics, and exposes a deterministic onset detector. Onsets use
only observations at or before the candidate timestamp, a pre-event robust
baseline, a MAD-derived robust sigma, and persistence. Results are emitted per
predictor, event, and sensitivity threshold with reliable/uncertain/unavailable
status. Existing correlation output remains under an explicitly named legacy
diagnostic field.

The website adds a compact event-onset card and chart overlay. It labels these
as experimental research results, shows timestamps/lead times only when the
data support them, and leaves existing charts, replay, map, and downloads
unchanged.

## Testing and operations

Deterministic Python tests cover onset persistence and thresholds, missing-hour
handling, UTC alignment, datum protection, lag-sign convention, and exclusion
of future observations. The Actions backfill workflow runs acquisition and
analysis; the deploy workflow validates the derived artifacts. Historical
recovery is reported from provenance metadata rather than inferred from row
counts.

## Explicit limits

No historical 00065 values are converted to NAVD88, no MCHL1/USACE records are
spliced, no interpolated values or causal/significance claims are introduced,
and overlapping windows are retained but marked as potentially dependent
episodes rather than counted as independent samples.
