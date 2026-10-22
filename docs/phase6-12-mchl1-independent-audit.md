# Phase 6.12 — Independent MCHL1 station and datum audit

**Decision: KEEP SHADOW-ONLY.** Live 6h, 24h and 72h native-stage changes are calculable, but provider datum and quality are still unverified. Forecast eligibility stays false.

## Distinct stations and independent evidence

- **MCHL1 / CE678A12**: NOAA HADS identifies PASS MANCHAC NEAR HWY 51 at 30°17′00″N, 90°23′46″W. CEMVN1-operated HG at 15-minute data intervals. This establishes station identity and reporting cadence, **not datum, stable gauge zero, or provider QC interpretation**. https://hads.ncep.noaa.gov/states/LA_dcps.shtml
- **USGS 073802302**: Pass Manchac nr Lake Maurepas, parameter 00065 native gage height, available beginning 2022-05-13 and last displayed through September 2026. Candidate historic shape/change cross-check; do not assume same gauge or datum. https://waterdata.usgs.gov/nwis/uv?site_no=073802302
- **USACE 85420LA**: Separate hardened gage west of US 51 has zero 0 ft NAVD88 (2009.55). Not a proven MCHL1 datum or conversion. https://rivergages.mvr.usace.army.mil/WaterControl/stationinfo2.cfm?sid=85420LA
- **USACE 85420 and PMPL1** are distinct identifiers, not interchangeable with MCHL1.

## Required acceptance evidence

1. Obtain original MCHL1 operator documentation: gauge reference datum and epoch, zero and survey history, sensor swaps, SHEF qualifier QC semantics, timestamps, and corrections.
2. Retrieve time-aligned MCHL1 HG and independent USGS 073802302 and Corps water level *without splicing*, retaining raw provenance and source-specific datum information.
3. Compare native stage changes and cross-correlation with exact valid-time overlap, missing rates, instrument discontinuities and confidence intervals. Matching trends are not proof of equal zero.
4. Inspect multiple live completed-hour shadow features across 6/24/72-hour lookbacks, latency, flagged and missing measurements. Never backfill forecasts using later information.
5. Audit frozen model training completeness: if the historical MCHL1 feature was mostly missing/imputed, availability alone does not mean the model learned a predictive MCHL1 signal.
6. Require separate evidence-based approval before admitting MCHL1 to model inference. Keep quality unverified and forecast eligibility false until then.

## Authentic Phase 6.11 baseline

Post-merge issuance d95bcc9b4aebd673 at 2026-10-22T20:19:44Z: 381 MCHL1 candidate observations spanning 95h; 15-minute maximum gap, 49.73-minute latest age, expected hourly bin present. Shadow changes: 6h -0.03917ft; 24h -0.13417ft; 72h -0.42667ft. All three live model features remain missing and excluded. This verifies calculation, **not scientific eligibility**.
