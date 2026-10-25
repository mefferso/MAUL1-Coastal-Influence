# Rainfall and tributary observation acquisition design

## Intent

Extend the existing prospective coastal-forcing receipt archive with the four USGS rainfall/stage candidates already identified in the feasibility study, and add a bounded MRMS proof of concept that converts one hourly gridded QPE file into upstream-basin precipitation receipts. The work supports shadow research into water-level rises; it does not feed forecasts or certify rainfall attribution.

## Goals and safeguards

- Preserve the current collector's raw-payload hash, actual retrieval timestamp, valid observation time, QC/provisional fields, append-only receipt behavior and run-health reporting.
- Archive USGS 00045 as a reported precipitation accumulation, with interval metadata only when the provider supplies it. Never infer a precipitation rate or convert 00065 stage to discharge.
- Capture 00065 stage for Dawson Creek, Bayou Fountain and Bayou Manchac in native site-specific gage references. Keep 63160 and datum differences separate.
- Compute MRMS 1-hour Pass 2 spatial averages over USGS NLDI upstream basins for MAUL1 and DENL1 and the intervening MAUL1-minus-DENL1 area, retaining coverage, valid interval, product, geometry, retrieval and source-hash provenance. Do not commit full GRIB files.
- Treat optional/local feeds as noncritical to the existing NWCL1/DENL1/MDLL1/MAUL1 hourly archive. Write explicit health status for empty, missing, invalid or failed candidate feeds.
- Keep all results research-only; leave Phase 6 issuance and verification, frozen models and dashboards unchanged.

## Approaches considered

1. **Add a second USGS collector.** Rejected because it duplicates transport, schema, raw hashing, receipt deduplication and health logic already implemented in PR #60.
2. **Extend the existing USGS source registry/parser and archive contract.** Selected for the four station series. It reuses the existing collector and preserves its existing sources, while marking new candidates noncritical so their temporary availability cannot break the established archive.
3. **Put full MRMS gridded downloads inside the existing collector.** Rejected for the first iteration because gridded decoding and basin geometry have distinct dependencies and failure modes. Use an isolated, optional MRMS aggregation module invoked by the existing workflow; store only derived basin aggregates and provenance. Keep failures visible in a separate health record.

## MRMS proof-of-concept method

Use NOAA MRMS `MultiSensor_QPE_01H_Pass2` (one-hour accumulation, mm) and the USGS NLDI basin boundaries for USGS 07380215 (MAUL1) and 07378500 (DENL1). Build the intervening area by subtracting the DENL1 basin from the MAUL1 basin only after verifying polygon nesting and nonempty positive area. Aggregate valid grid-cell centers inside each basin and weight by estimated cell area from grid spacing and latitude for a regular lat/lon grid. Reject unknown grid types, invalid interval metadata, negative/sentinel values, nonnested basins and inadequate cell coverage. This is a bounded proof of concept; center-in-polygon boundary handling and MRMS gauge blending remain limitations.

## Scope and remaining decisions

The known station identifiers and candidate parameter codes come from the merged local-forcing inventory. Hosted PR Actions will perform read-only live endpoint checks because this execution shell's direct USGS requests receive proxy 403 responses. If live responses do not establish the expected fields, units or timestamp semantics, the source will remain archived only as an explicit unavailable/invalid health result and the documentation will state that it is not currently verified.
