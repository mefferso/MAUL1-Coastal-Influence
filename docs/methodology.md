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
