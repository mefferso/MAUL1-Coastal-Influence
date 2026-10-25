# Findings — directional wind and hydrologic response diagnostics

**Conclusion: the observed sequences are physically suggestive but inconclusive.** The hourly archive can support directional, cumulative and within-station response diagnostics, but it cannot establish lake-wide wind forcing, pressure-driven setup, rainfall attribution, or incremental forecast skill. No model was fit or rescored.

## What the event records show

Wind speeds below are NWCL1 scalar hourly means in knots; direction is meteorological **from** degrees. East and southeast duration uses non-overlapping sectors and the 10-knot exploratory speed bin. MAUL1 changes are native USGS 00065 gage-height feet; DENL1 changes are station-local cfs. These values are phase descriptions, not a cross-station elevation gradient.

| Fixed period | NWCL1 hourly wind | Directional duration | MAUL1 native stage change within period | DENL1 discharge change |
|---|---|---:|---:|---:|
| Alberto pre-named context, Jun 15 00–Jun 19 12 UTC | mean 5.44 kt; max 21.29 kt; mean vector direction 78.4° from | 8 easterly hours ≥10 kt; 0 southeasterly | +1.65 ft | +53 cfs |
| Alberto named chronology, Jun 19 12–Jun 20 09 UTC | mean 11.53 kt; max 24.28 kt; mean direction 77.5° | 8 easterly hours ≥10 kt; 0 southeasterly | +0.565 ft | +41 cfs |
| Alberto post-landfall recession, Jun 20 09–Jun 27 00 UTC | mean 5.16 kt; max 18.99 kt; mean direction 67.8° | 11 easterly hours ≥10 kt; 0 southeasterly | −2.43 ft | −205 cfs |
| **Unattributed transition**, Jun 27 00–Jul 1 00 UTC | mean 5.20 kt; max 10.42 kt; mean direction 220.7° | 0 easterly and 0 southeasterly hours ≥10 kt | −0.06 ft net across the full phase | −6 cfs |
| Beryl remote phase, Jul 1–5 UTC | mean 4.41 kt; max 11.80 kt; mean direction 199.7° | 1 easterly hour ≥10 kt; 0 southeasterly | +0.235 ft | +401 cfs |
| Beryl Gulf/landfall chronology, Jul 5–9 UTC | mean 3.96 kt; max 14.37 kt; mean direction 157.7° | 0 easterly and 0 southeasterly hours ≥10 kt | +0.265 ft | −237 cfs |
| May 2021 response buildup, May 8 16–May 22 02 UTC | mean 5.47 kt; max 17.11 kt; mean direction 91.6° | 9 easterly hours ≥10 kt; 0 southeasterly | +4.25 ft | +23,923 cfs |
| August 2016 catalog rise, Aug 14–17 17 UTC | mean 2.37 kt; max 5.85 kt; mean direction 136.7° | 0 easterly and 0 southeasterly hours ≥10 kt | +3.125 ft from valid phase endpoints | −184,750 cfs from valid phase endpoints |
| July 2021 quiet-low-variation control, Jul 9–16 | mean 3.60 kt; max 12.38 kt; mean direction 140.7° | 1 easterly hour ≥10 kt; 0 southeasterly | −0.07 ft | +723 cfs |

The detailed phase summaries include NWCL1 MLLW residuals, MDLL1 anomalies relative to their own preceding 72-hour medians, source completeness, 3/6/12/24/48/72-hour integrated east/north components, persistence, one-hour wind acceleration/relaxation and reversal counts. In the August 2016 antecedent phase, MAUL1 stage coverage is only **5.6%**; its endpoint change is therefore suppressed. The August response is left-censored in the Phase 3B catalog, and its exact catalog trough and peak bins are unavailable in the source archive. The reported +3.125 ft is only a change between the first and last valid observations inside the catalog rise interval, not a complete event reconstruction. DENL1 flow is very high in the period; because there is no rainfall series, this does not prove the source of the rise.

## Response timing and delayed behavior

The fixed Phase 3B response catalog reports MAUL1 native-stage rises of 2.20 ft for Alberto-period event `maul1-response-0147`, 1.475 ft for the June–July 2024 event `maul1-response-0148`, and 4.385 ft for May 2021 event `maul1-response-0094`; the last differs by 0.005 ft from the catalog's rounded 4.38 ft. The August 2016 catalog rise is 3.25 ft with uncertain onset and no paired exact trough/peak observation in this archive.

Within those outcome-defined response intervals, maxima occurred in this order:

- **Alberto-period rise:** the MDLL1 native-stage maximum preceded the NWCL1 residual maximum by 10 hours; the MAUL1 stage maximum followed the MDLL1 maximum by 30 hours. But the catalog rise began June 10, before the June 15 pre-named context and before Alberto formed as a named tropical storm. This sequence cannot establish wind-caused propagation.
- **June–July 2024 rise:** MDLL1's maximum preceded the NWCL1 residual maximum by 3 hours, and the MAUL1 maximum followed the MDLL1 maximum by 4 hours. The target response began June 28, while the selected Gulf-approach chronology starts July 5. The June 27–July 1 net phase change conceals a lower-stage trough and partial recovery within that interval; it remains unattributed and is not assigned to Beryl.
- **May 2021:** the NWCL1 residual and MDLL1 maxima were in the same hour; the MAUL1 maximum followed by 1 hour. The DENL1 discharge maximum occurred 12 hours after the MAUL1 maximum, while discharge rose by about 23,923 cfs across the buildup phase. Wind, lake response and a strong river-flow change overlap; this archive cannot partition their contributions.
- **August 2016:** the NWCL1 residual and MDLL1 maxima were in the same hour; the valid MAUL1 maximum followed the MDLL1 maximum by 23 hours. DENL1's maximum occurred earlier than the MAUL1 maximum, but the event onset is left-censored and rainfall is unavailable.

These are timestamp differences among observed maxima inside a response window selected from MAUL1 outcomes. They are not onset-to-onset lags, calibrated response times, or forecast lead. The 3/6/12/24/48/72-hour profiles are likewise descriptive. For example, the Alberto pre-named phase's eastward 24-hour directional proxy versus subsequent 6-hour MAUL1 changes has descriptive Pearson `r` values of −0.36, −0.35, −0.35, −0.15, +0.32, +0.52, and +0.57 at the fixed lag sequence. It is a single event whose MAUL1 rise was already underway, with strongly overlapping forcing histories; the correlation cannot support a delayed-response constant. Beryl Gulf-phase coefficients remain small to moderate (−0.22 to +0.28 across the same lags), with 16 six-hour blocks per lag. The May antecedent coefficients are small at 0–24 hours (−0.07 to +0.09) and negative at 36–48 hours (−0.27/−0.21). The August antecedent coefficients vary from −0.33 to +0.63 with only 0–12 six-hour blocks across lags and an uncertain onset. The control's eastward-proxy correlations range from −0.06 to +0.10. None has an independent sampling basis for significance or skill.

## What this supports for future work

1. **Improve the wind observation before refining the proxy.** NWCL1 is a shoreline site; it cannot validate winds over the central or western lake. The merged network inventory identifies LKPL1 as a historical open-water candidate, but its 2004–2012 record does not prove a continuous or currently reporting source. The independent WeatherFlow Mid-Lake record in the Alberto presentation remains unrecovered. Begin receipt-timestamped archival only when an accessible source, station identity, averaging interval, exposure, QC and sensor history are verified.
2. **Retain a small process-focused feature shortlist for a future challenger:** 12/24/48/72-hour integrated directional U/V proxies with rolling coverage; non-overlapping E/SE sector duration and run length; wind relaxation/reversal; NWCL1 same-datum residual and MDLL1 own-station anomaly/tendency; and predeclared interactions with DENL1 discharge. These are candidates for testing, not recommended predictors or validated improvements. A fetch projection requires an independently reviewed lake/channel orientation.
3. **Acquire precipitation and synoptic context.** There is no direct rainfall or pressure-gradient series in the selected archive. DENL1 discharge does not stand in for local rainfall, smaller tributaries, or all Amite forcing. A future archive should pair precipitation fields, upstream discharge, wind height/exposure, source receipt times and sensor metadata.
4. **Use a new challenger only after pre-registering a compact feature set and evaluation design.** Development must be chronological and event-blocked with purging; the reused 2023+ historical holdout is not independent evidence. Keep Phase 6 frozen and require prospective shadow records before any operational discussion.
5. **Physical-process follow-up is justified, but the present conclusion is inconclusive.** The cases show delayed, persistent and sometimes nearly coincident lake/river responses under different wind and discharge regimes. They do not establish that cumulative wind forcing explains MAUL1 rises or adds information beyond the current network.

No operational forecast guidance is introduced.
