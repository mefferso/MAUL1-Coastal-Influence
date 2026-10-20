# Physical interpretation and scientific guardrails

Primary scientific reference: *Coastal-Flood Identification and Prediction at MAUL1: Deep-Research Technical Report* supplied by the project owner on 2026-10-19. Its proposals for model probabilities, Shell Beach, French Settlement and PETSS integration are future phases; the owner's five-station historical Phase 1 scope takes precedence.

## Two possible pathways

**River:** DENL1 discharge and its 3/6/12/24-hour changes may precede MAUL1 rises. Additional runoff enters between the stations, so lack of a Denham response cannot prove absence of river influence. August 2016 is a river-dominant *candidate*, pending event-level review.

**Coastal:** Regional setup may lift Lake Pontchartrain, propagate through Pass Manchac and Lake Maurepas, and create a backwater signature at MAUL1. New Canal observed minus its astronomical prediction (same station, same MLLW datum, matching UTC time) estimates the non-tidal lake anomaly. MDLL1 is an independent lake gauge. MCHL1 is a potential pathway gauge, but it is not guaranteed to measure only coastal forcing. Easterly/southerly persistence merits investigation; no wind threshold is preselected. A stage rise is not evidence of flow reversal.

**Compound:** Both branches may contribute. Event titles and tropical status are not reference classifications. Until an analyst reviews upstream discharge, both lake records, Pass Manchac, winds, datum compatibility and rainfall, the appropriate label is **indeterminate**.

## Datum and time rules

1. Keep native values and quality flags. MAUL1 00065 gage height and 63160 NAVD88 are distinct series. Only direct 63160 counts toward a 4.0-ft NAVD88 threshold test. The contemporary −1.38-ft relation is not a historical conversion authority.
2. All stored valid times are UTC. Do not fill a source outage. Plot gaps longer than 90 minutes visibly. Event replay excludes every record whose valid time exceeds the selected time; because receipt times are unavailable, it is a valid-time-limited exploration rather than an operational hindcast.
3. Do not calculate a water-surface gradient between gauges until datum compatibility is documented for their actual observation periods.
4. Compute wind vectors from each raw meteorological FROM angle: `u = −speed × sin(angle)` and `v = −speed × cos(angle)`. Aggregate vector components, never the raw angles.
5. Any future lag analysis must use event-specific changes or detrended levels, show lead-sign conventions, account for gaps, and separate peak coincidence from actionable lead time.

## Phase 2A experimental onset diagnostics

The archive derives UTC-hour products from observations that actually fall within each hour. Empty hours remain empty, coverage is recorded, and no interpolation is used. Water levels use a robust within-hour median; Denham discharge uses a within-hour mean; wind uses component-wise vector statistics. Trailing changes use only exact available hourly observations and never cross a datum boundary.

Event-onset results use the preceding 72 hours of exact one-hour changes, requiring at least 48 usable baseline hours. A signal is a positive change above the baseline median plus 1.5, 2.0 or 2.5 robust-sigma equivalents for three consecutive valid hours. Missing hours break persistence; near-zero MAD, insufficient baseline, gaps, and rises already underway at the archive start are explicit statuses. A predictor lead is a first-signal timestamp comparison, not a propagation time, forecast lead, causal attribution, or significance claim; paired results are labeled detected-but-not-validated rather than reliable prediction skill. The legacy optimized correlation remains visible only as a labeled exploratory diagnostic.

Wind products use trailing vector means of the hourly east/north components over 3, 6, 12 and 24 hours. Each window requires every hourly vector to have observations; direction is calculated from the mean components, and directional persistence is the resultant length of the hourly unit vectors, so compass wraparound is handled without averaging degrees.

## Phase 2B independent event verification

`site/data/verification.json` is a separate research artifact. MAUL1 target episodes are selected from MAUL1 native gage height alone with a fixed 72-hour antecedent baseline, at least 48 valid baseline changes, positive consecutive hourly changes, a minimum 0.25-ft rise, a minimum three-hour run, and a positive hourly rate. A six-hour falling/flat reset separates candidate responses. A missing hour breaks continuity; zero or near-zero robust MAD, unavailable baselines, uncertain short/magnitude-limited rises, and archive-start rises are emitted as explicit records rather than silently converted into detections.

DENL1 discharge, NWCL1 residual, and MDLL1 stage episodes are detected independently. Only qualifying detected predictor episodes are matched one-to-one to MAUL1 signal episodes in predeclared 0–72-hour (DENL1) or 0–18-hour (NWCL1/MDLL1) windows. A predictor after target onset is retained as an unmatched post-target record and cannot receive a negative lead. Matches are `detected_not_validated`: they demonstrate timestamp alignment only, not a useful precursor, forecast skill, causal attribution, or a universal lag. Unmatched predictors, target nonresponses, uncertain onsets, gaps, and quiet/no-signal records remain in the artifact.

The August 2016, Beta 2020, November 2024, April 2025, Laura 2020, and October 2024 windows are reported explicitly. Sally and Beta 2020 share a dependent-window group because their archive windows overlap; they are not independent samples. MAUL1 00065 gage height remains separate from direct 63160 NAVD88 elevation, no pre-2026 NAVD88 threshold exceedance is inferred, and MCHL1 is not combined with USACE 85420/85420LA.

Historical windows overlap in time: `sally-2020` (September 12–21) overlaps `beta-2020` (September 18–28). Those named storms may be part of one hydrometeorological response episode and must not be counted as independent verification samples without an event-dependence review. Lake-rise examples with weak MAUL1 response remain in the archive as negative or ambiguous evidence.

## Phase 3B continuous historical validation

`scripts/validate_phase3b.py` runs from the complete hourly archive after archive integrity validation. It reuses the fixed Phase 2B detector settings (72-hour baseline, at least 48 valid one-hour changes, positive consecutive changes, three-hour persistence, fixed station-specific minimum rise, 2.0 robust-sigma primary setting, and six-hour reset) and reports 1.5/2.0/2.5-sigma sensitivity without selecting a preferred setting on the same data. Missing values are never filled.

For Phase 3B, detected, uncertain, gap, and archive-boundary-censored episodes are retained. The event table groups overlapping active intervals and intervals separated by no more than 72 hours across stations; 48- and 96-hour alternatives are reported. This transitive time-cluster rule reduces repeated counting but cannot establish that groups are independent storms. The event grouping is performed before the fixed 2023-01-01 calibration/holdout partition. A 72-hour seam embargo excludes boundary-crossing groups. This is a future data-partition proposal, not a trained model or holdout skill result.

For a known detected MAUL1 episode, the group’s first response onset is compared with the latest qualifying predictor onset strictly before it, within the predeclared DENL1 0–72-hour or NWCL1/MDLL1 0–18-hour window. Coincident and post-target signals are separate outcomes. Only positive differences appear in the advance timing table. Lead distributions are conditional on the detector and grouped archive sample; they are not actionable forecasts or propagation times. A 90% valid-hour window-coverage screen (with 80% and 100% alternatives) describes observation sufficiency, not signal validity. Wind context uses vector components from NWCL1 and NDBC over the preceding six hours with no favorable-wind threshold.

Quiet monthly controls require at least 90% valid hourly coverage for MAUL1 stage, DENL1 discharge, NWCL1 residual, and MDLL1 stage, with no target/core-predictor candidate overlapping the month under the same detector. Every other month is retained with explicit exclusion reasons. A quiet month is a detector-based control label, not proof of an absence of forcing; MCHL1 and NDBC availability remain visible separately.

The validation report leaves probability of detection, false-alarm ratio, and critical success index unavailable because the archive has no pre-issued forecast opportunities, independent causal response labels, or proven independent target-event samples. Target groups without a detected prior signal, predictor-only groups, post-target signals, coincident signals, and uncertain onsets are retained as descriptive counts. Lack of DENL1 response cannot rule out local runoff or other tributaries; NWCL1 residual alone cannot label coastal forcing.

The four priority case timelines include context from pinned NOAA NCEI Storm Events detail-file revisions. These reports document reported hazards and, for Beta, an external report of 4.04 ft NAVD88 at MAUL1. That report is kept distinct from the historical 63160 series pending its sensor/report provenance; it does not license conversion of the 00065 gage-height record. External event descriptions are contextual evidence, not causal ground truth. NCEI local timestamps are not relabeled as UTC observation times.

## Next scientific gates

* Resolve MCHL1's HADS/USACE instrument history and reference datum, and investigate its absent 2016–2021 archive, keeping PMPL1, USGS 073802302 and USACE 85420LA distinct.
* Resolve historical MAUL1 00065 datum effective dates, direct 63160 history, and NWPS display datum before marking pre-2026 threshold exceedances.
* Complete 2016–2026 multivariate coverage, include non-tropical setup and ordinary non-events, and document coverage and major gaps by variable.
* Derive event-specific Denham-to-MAUL1 and downstream-to-MAUL1 lag distributions from changes, with missing-input and source-QC sensitivity tests. Seek independently reviewed river, coastal, compound and uncertain reference labels.
* Only after these gates, evaluate possible future prediction work using event-separated validation. This Phase 1 project emits no forecast probabilities.

## Sources

* [USGS MAUL1](https://waterdata.usgs.gov/monitoring-location/USGS-07380215/), [DENL1](https://waterdata.usgs.gov/monitoring-location/USGS-07378500/), [MDLL1 Crossover 4](https://waterdata.usgs.gov/monitoring-location/USGS-301200090072400/)
* [NOAA CO-OPS Data API](https://api.tidesandcurrents.noaa.gov/api/dev/), [New Canal station](https://tidesandcurrents.noaa.gov/stationhome.html?id=8761927)
* [Iowa Environmental Mesonet HADS archive](https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py?help=), [NWS HADS LIX listing](https://hads.ncep.noaa.gov/hsas/LIX_dcps.shtml), [USACE Pass Manchac historic instrument](https://rivergages.mvr.usace.army.mil/WaterControl/stationinfo2.cfm?sid=85420)
