# Directional wind forcing, duration, and hydrologic memory

**Status: Research / Shadow Evaluation / Not Operational**  
**Conclusion: inconclusive; physically plausible, not demonstrated as incremental predictive information.**

## Executive findings

1. Wind is not absent from the frozen model. Phase 5A and Phase 6 use NWCL1 current east/north vector components, 6-hour and 24-hour vector means, and 6-hour directional persistence. Phase 5B coastal-tidal/full retain those fields. They also use clock harmonics as calendar proxies, not an observed/predicted local tide model.
2. Features still absent from the models include cumulative wind stress/impulse, 3/12/48/72-hour wind summaries, persistent-direction run length, threshold duration, wind relaxation/reversal memory, lagged wind-by-water-level/river interactions, and a distributed-lag or decay-memory term. The archive includes some non-model diagnostic windows, but these do not enter the frozen model.
3. NWCL1 retrospective descriptors showed broad overlap across detected rises, missed rises, and nonresponse controls. False-alert clusters also often had strong and persistent wind descriptors. The current small descriptive analysis does not distinguish whether prolonged wind improves rise prediction or adds false alarms.
4. The newly attached presentation confirms that the original approximately 150-hour >15 mph estimate refers to **WeatherFlow Mid Lake Pontchartrain**, not NWCL1. Slides plot average wind and gust separately in mph, but only as a static image without raw records, exact station ID, averaging cadence, timezone, or 2024 sensor height/exposure. The earlier NWCL1 count cannot challenge the WeatherFlow estimate.
5. The corrected chronology treats June 29–30 as a separate, unattributed transition pulse. It is not assigned to Beryl. Beryl’s Gulf approach and Texas landfall are analyzed in a July 5–9 UTC window; the deck’s CO-OPS figure spans July 1–10. Neither time overlap nor wind/stage co-occurrence establishes causation.
6. Simple NWCL1 duration descriptors do not presently demonstrate incremental predictive skill. The original sustained directional-forcing hypothesis remains incompletely tested because the independent WeatherFlow Mid-Lake series could not be recovered. No prospective skill, independent out-of-sample improvement, physical propagation time, or causal wind attribution has been established; do not promote a challenger based on this analysis.

## Existing-model feature audit

The inventory below was checked against `scripts/phase5a.py`, `scripts/phase5b.py`, frozen `site/data/prospective/model-artifacts.json`, and the committed forecast feature definitions.

| Family | Already represented | Missing or under-validated |
|---|---|---|
| Wind magnitude and direction | NWCL1 current `wind_u`, `wind_v` in knots; these encode speed and direction. Current vector magnitude is derivable. | No other wind station in the frozen predictors. NWCL1 representativeness of lake-wide or open-water field is not validated. |
| Wind lags/averages | 6-hour and 24-hour mean U/V, based on completed hourly bins with at least 80% coverage. | 3-, 12-, 48-, and 72-hour summaries are not model inputs. Historical availability is valid-time only, without receipt timestamps. |
| Direction persistence | Six-hour vector resultant length, requiring at least five valid hourly vectors. | Longer persistence, run duration, directional reversal, and fetch-projected components are absent. The local archive does include additional exploratory vector means, not frozen model inputs. |
| Wind stress/cumulative forcing | None. | No U·speed/V·speed stress proxy, integrated directional forcing, nonlinear duration × intensity term, or calibrated physical stress. No wind-height/exposure history is retained for normalization. |
| Hydrologic memory | MAUL1 native stage and recent changes (1/3/6/12/24/72h as model family permits), six-hour slope and 24-hour variability; NWCL1 MLLW residual and changes; MDLL1 stage changes; DENL1 discharge and changes. | No explicit wind-to-stage distributed lag, wind-relaxation memory, lake-level anomaly interaction with accumulated wind, or calibrated response kernel. MCHL1 remains untrusted/shadow-only. |
| Other periodic terms | Phase 5B uses 24h, 12.42h, and 14.765d clock harmonics. | These are time/calendar harmonics, not observed astronomical tide predictions or a synoptic pressure field. |

Phase 5A archives include extra exploratory 3/6/12/24-hour vectors; presence in an archive must not be mistaken for model use. Frozen Phase 6 was not changed or retrained.

## Fixed issue-time descriptor analysis

The script computes windows of 3, 6, 12, 24, 48, and 72 completed hours before each chosen issue time. It applies an 80% nonmissing rule for continuous summaries, never interpolates, and missing bins break directional runs. The issued hour is excluded. A count above 10, 15, or 20 mph is a sensitivity descriptor using archived hourly mean vector speed—not a proposed trigger. Since local lake fetch/orientation and sensor geometry were not validated, signed `-U` is reported as the westward component only; no direction is labeled “favorable”. `-U × speed` is a proxy in kt², not physical stress. Physical stress would require defensible sensor height/exposure and drag treatment.

The fixed cohort sample contains 28 detected Phase 6 rise groups, 81 missed groups, 48 false-alert clusters, and 63 eligible Phase 3B nonresponse control candidates. It is one descriptor time per group/cluster/control. The Phase 6 groups are target-defined, not verified physical storms; control candidates are not event-matched independent observations. Cohorts are serially dependent and can overlap in time. Quartiles below are descriptive, with no p-values or independence assumption.

| Descriptor at selected issue time | Detected rises (n=28) | Missed rises (n=81) | False-alert clusters (n=48) | Eligible controls (n=63) |
|---|---:|---:|---:|---:|
| Median hours with NWCL1 speed ≥15 mph in prior 72h (Q1–Q3) | 4.5 (0–15.5) | 1 (0–12.5) | 6 (1–21.5) | 0 (0–3) |
| Median westward impulse proxy, prior 72h, kt·h (Q1–Q3) | 32.1 (−106.7–170.2) | 14.0 (−115.9–164.0) | 117.4 (−27.4–266.1) | 99.5 (−16.5–176.2) |
| Median signed `-U × speed` proxy, prior 24h, kt² (Q1–Q3) | −2.2 (−18.1–18.8) | 3.5 (−10.4–15.6) | 31.8 (13.4–98.7) | 3.0 (−3.7–10.2) |
| Median 24h directional persistence (Q1–Q3) | 0.72 (0.54–0.94) | 0.84 (0.56–0.95) | 0.85 (0.58–0.96) | 0.76 (0.47–0.91) |

`15 mph` is shown only because it appeared in the exploratory hypothesis; it is not validated as an onset threshold. False alerts can have substantial wind forcing, and missed rises span both weak and sustained forcing descriptors. A static issue-time cohort comparison cannot establish incremental forecast value, latency, causal direction, or whether adding features would help detection without raising false alarms.

![Wind descriptors by outcome cohort](wind_memory_groups.svg)

## Review of the attached Alberto presentation

The attached `Alberto effects.pptx` has 21 slides. I extracted slide text and inspected rendered charts and maps. Slide 1 shows a storm-track map labeled June 17–20; those illustrated track times are not local wind-onset dates, and the NHC report dates Alberto’s tropical-storm formation to June 19 12Z. Slides 2–11 repeat one series labeled “Weatherflow Mid Lake Pontchartrain” across ten water locations. Its legend distinguishes average wind (mph) and gust (mph); the same `>15 mph (150 hrs or 6 days)` claim is reused for every site. This is a single common wind reference, not ten local wind records. Black directional arrows are drawn over the plot, but their direction convention/values are not identified.

The wind plot covers approximately June 15–27; paired water graphics span approximately June 12–27. The time labels do not identify timezone. The water plots label a “normal tide midpoint”, but the deck does not document water source, datum, normal reference interval, or exact crossing rule. The delay annotations are subjective visual estimates. The ten delay values (36, 12, 24, 18, 18, 12, 12, 18, 12, 12 h) reproduce the stated arithmetic mean 17.4 h, median 15 h, and mode 12 h; this does not validate a physical response lag.

There are internal duration inconsistencies. 150 hours is 6.25 days, not six. Some water duration annotations also conflict: 225 hours is 9.375 days, but slides label it 9 days and, for Blind River, 10.5 days. The stated residence-time summary cannot be independently reproduced from static chart screenshots. Slide 14 pairs a NOAA CO-OPS New Canal (8761927) verified-water chart, labeled NAVD and dated Aug 27–Sep 7, 2012 local time, with average/gust wind labeled “Mandeville”; the WeatherFlow identity and exact series behind that wind plot are not specified. Slide 15 is a pattern-recognition divider. Slides 16, 18, and 20 show NOAA CO-OPS New Canal plots for Alberto (Jun 12–27), May 2021 (May 12–27), and Beryl (Jul 1–10), explicitly labeled MHHW and GMT. Slides 17, 19, and 21 each show one WPC surface analysis overlaid on satellite imagery (Alberto 00Z Jun 20, May 2021 12Z May 21, Beryl 15Z Jul 6). These are useful synoptic snapshots, not time-resolved pressure-gradient analyses.

The slide annotations and arithmetic are transcribed to `presentation_claims.json`; `test_presentation_claims.py` checks their arithmetic and flags inconsistent hour/day labels. The JSON preserves values as presentation claims rather than observations newly recovered from WeatherFlow.

## WeatherFlow Mid-Lake identity, exposure, and recovery attempt

The deck map arrow places the wind reference near the mid-lake Causeway. The NHC Sally Tropical Cyclone Report independently documents WeatherFlow site XPTN, Pontchartrain Causeway–Midlake, at 30.20°N, 90.12°W, with a 12.5 m sensor and one-minute wind averaging in that 2020 event. This supports the likely geographic crosswalk, but does not prove the sensor, height, or averaging method was unchanged in June 2024. The deck itself does not give XPTN. WindAlert/SailFlow currently labels spot 36469 “MDLL1 - Mid-Lake Pontchartrain on Causeway”; name and location suggest the same setting, but provider metadata are needed to certify the platform-ID-to-XPTN crosswalk. These IDs must not be confused with USGS/NWPS water-level station MDLL1.

The June 2024 WeatherFlow time series was **not recovered**. The PPTX contains static screenshots, not an editable chart/workbook or numerical observations. WeatherFlow documents access restrictions for observations from stations not owned by the requester; its support guidance directs raw historical downloads to professional services for pricing/API access. WindAlert/SailFlow exposes archive graphs/download controls, but no unauthenticated raw export was accessible here. The deck does not specify averaging period, timezone, exact 150-hour endpoints, sensor history, QC, missingness, or receipt time. The 150-hour value is retained as the user’s exploratory estimate: unresolved, neither confirmed nor contradicted by NWCL1.

## Corrected Alberto/Beryl chronology

The previous broad June 27–July 20 “Beryl window” is withdrawn: it combined Alberto recession, a June 29–30 transition rise, Beryl’s distant Caribbean phase, Gulf approach, landfall, and long recovery. The new half-open UTC windows and reproducible calculations are in `event_period_diagnostics.json`; exact boundaries are declared in `event_periods.py`. NHC named-storm chronology is separated from local forcing onset. NWCL1 is retained solely as a local archive comparison and is not treated as the WeatherFlow source.

| Window (UTC, end exclusive) | Interpretation | NWCL1 hourly vector wind (archive only) | Hydrologic/river context |
|---|---|---|---|
| Jun 12 00–Jun 15 00 | 72-hour antecedent to first date shown in Alberto deck | 2/72 bins >15 mph | NWCL1 MLLW residual median 0.622 ft; MAUL1 00065 start-to-end −0.035 ft; DENL1 discharge −123 cfs. NWCL1 residual was already elevated before the deck’s wind plot begins. |
| Jun 15 00–Jun 19 12 | Deck’s pre-named disturbed-weather buildup context | 10/108 bins >15 mph; max 24.27 mph | NWCL1 residual median 0.935 ft, max 2.785 ft; max 24-hour residual rise +1.251 ft at Jun 19 08Z. MDLL1 native-stage max 24-hour change +1.225 ft at Jun 19 06Z; MAUL1 native 00065 max +0.685 ft at Jun 19 11Z. DENL1 max +212 cfs/24h at Jun 17 11Z. |
| Jun 19 12–Jun 20 09 | NHC Alberto formation through reported landfall near Tampico | 8/21 bins >15 mph; max 27.90 mph | NWCL1 residual median 2.861 ft; MDLL1 native stage max +1.335 ft/24h; MAUL1 native 00065 max +0.725 ft/24h. Strong response coincides with this short named interval after earlier buildup. |
| Jun 20 09–Jun 27 00 | Post-landfall local recession shown on deck charts | 6/159 bins >15 mph | NWCL1 residual stayed positive (median 1.312 ft; minimum 0.091 ft) while receding. MAUL1 native stage changed −2.43 ft start-to-end. |
| Jun 27 00–Jul 1 00 | **Unattributed transition pulse; not assigned to Beryl** | 0/96 bins >15 mph; max 11.95 mph | NWCL1 residual median −0.115 ft, but max 24-hour residual rise +0.623 ft at Jun 29 19Z; MDLL1 native-stage max +0.680 ft/24h at Jun 29 19Z; MAUL1 native 00065 max +0.735 ft/24h at Jun 30 01Z. This pulse follows recession of Alberto-period levels; cause remains unresolved. |
| Jul 1 00–Jul 5 00 | Beryl remote Caribbean/Yucatan phase; antecedent to Gulf entry | 0/96 bins >15 mph | NWCL1 residual median 0.270 ft; MAUL1 native 00065 max +0.395 ft/24h; DENL1 max increase +409 cfs/24h by Jul 4 23Z, a competing river context before Gulf approach. |
| Jul 5 00–Jul 9 00 | Beryl Gulf transit through Texas landfall at Jul 8 08:40Z | 1/96 bins >15 mph; max 15.23 mph | NWCL1 residual median 0.434 ft, max 0.645 ft; MAUL1 native max +0.295 ft/24h at Jul 8 14Z, below the significant-rise threshold; DENL1 max +595 cfs/24h at Jul 5 02Z. |
| Jul 9 00–Jul 12 00 | 72-hour post-landfall follow-up | 0/72 bins >15 mph | NWCL1 residual median 0.067 ft; MAUL1 native stage changed −0.62 ft start-to-end. |

The deck’s Beryl CO-OPS chart covers July 1 00 through July 10 23:59 UTC. The Phase 3B MAUL1 response group begins June 28 08Z, before Beryl entered the Gulf, and peaks July 9 06Z. This response spans the transition pulse, Beryl’s distant phase, Gulf approach/landfall, and discharge changes; it must not be labeled Beryl-caused. June 29–30 is deliberately kept separate from the Beryl Gulf/landfall window.

All station-level water changes are within-station only. NWCL1 residual uses its own MLLW observed-minus-prediction pairs; MDLL1 is native stage; MAUL1 is native USGS 00065 gage height. No absolute levels are subtracted across stations. NWCL1 figures do not reproduce or validate WeatherFlow duration: location, hourly vector aggregation, exposure, averaging period, and missingness differ or are unknown relative to the deck’s over-water chart.

The May 2021 case remains exploratory: the archive shows 48/744 NWCL1 hours above 15 mph (maximum 21.36 mph), lake/MAUL1 rises, and a large DENL1 discharge increase (up to 13,100 cfs/24h). It does not isolate WeatherFlow forcing or the pressure mechanism. Isaac’s 2012 graphic cannot be independently reconstructed because it predates the archive and lacks raw source metadata.

NHC documents Alberto formation at 1200 UTC June 19 and landfall near Tampico around 0900 UTC June 20; WPC notes the mid-June disturbed-weather low over the Yucatan/Bay of Campeche. Beryl formed June 28, crossed the Yucatan July 5, and made Texas landfall at 0840 UTC July 8. These dates define meteorological chronology, not local forcing onset. The deck’s pressure-pattern images are not numeric evidence of pressure gradients. No NARR analysis was completed.


## Failure and false-alert interpretation

The existing rise-failure audit reproduces 109 grouped rises: 28 detected, 81 missed; 79 missed groups never reached the required forecast-rise threshold on a qualifying target, and two crossed only after their first qualifying target. There are 48 false-alert clusters (305 overlapping false-positive target windows). These are not 109 independent physical events.

At selected first issue times, median 72-hour >15 mph hours are 1 for missed groups, 4.5 for detected groups, and 6 for false alerts. This does not suggest a clean missed-rise wind-memory signature; strong winds also occur in false alerts. The false alert catalog’s archived median instantaneous wind speed is 15.78 kt for false clusters and 16.17 kt for hit-containing clusters, likewise a weak separator. Missed events span 57 large subthreshold predictions and 22 near-threshold underforecasts; without rainfall archive and without a matched design, forcing attribution is unresolved. DENL1 and MDLL1 context already appears in the existing model/audit. A wind-by-river interaction remains a hypothesis only.

No model was fitted, retuned, rescored, or compared for forecast skill. Repeated search against 2023+ would reuse the historical evaluation period and cannot serve as independent validation. Any challenger requires a pre-registered small feature set and chronological/event-blocked evaluation with purging, paired errors, event-level uncertainty and prospective archival proof.

## Spatial propagation, pressure, and datum safeguards

This committed archive does not contain a validated hourly record for PLAL1, LRLL1, RGTL1/RFPL1, West End/WEGL1, WeatherFlow XPTN, or a confirmed DNAL1 sensor identity. The station inventory in PR #58 is not a historical time series. No station-to-station absolute gradient or propagation sequence was calculated here.

Within-station changes and NWCL1 water-minus-prediction residual remain in their own datum. MAUL1 USGS parameter 00065 is native gage height; it is not NAVD88 parameter 63160. MDLL1 and MCHL1 native values are not subtracted from MAUL1 or NWCL1. MCHL1 remains shadow-only due unresolved sensor/datum lineage. NOAA predictions are retrospective valid-time records, not proven issue-time data availability. Spatial precursor claims must wait for audited timestamps, instrument metadata, datum history, and independent sensor identity.

## Recommendation

- **Historical acquisition:** Yes, focused on raw hourly NOAA/USGS/CO-OPS station observations and metadata around the selected events; prioritize verifiable wind height/exposure, station identity, sensor transitions, and timestamps. Seek the WeatherFlow XPTN / Mid-Lake raw archive through a permitted owner or provider access path. Retrieve pressure/wind reanalysis for synoptic context, but do not treat it as local lake wind.
- **Prospective archival:** Yes. Preserve timestamped NWCL1 raw vectors, an independent over-water wind series if a freely accessible and stable feed can be verified, the same-datum NWCL1 water/prediction series, MDLL1 and DENL1, and per-observation provider receipt/QC/provisional fields. Archive actual station metadata versions and uptime. This is useful before deciding whether stations or features earn model inclusion.
- **Focused challenger:** Not yet. A later challenger may test a small predeclared set (e.g. 12/24/48/72h directional vector/stress proxy and relaxation terms) against the existing feature set, with fixed thresholds/windows, blocked development and an untouched future prospective period. Do not use tuning over reused 2023+ to claim independent improvement.
- **Physical-process work:** Yes. Couple independently observed lake wind and water level with pressure gradients and a hydrodynamic interpretation of the Pontchartrain–Rigolets–Pass Manchac–Maurepas/Amite boundaries. Separate coastal setup, local runoff, tidal anomaly, and discharge regimes.
- **Present conclusion:** Inconclusive. Simple NWCL1 duration metrics do not demonstrate incremental skill, but they do not test the original sustained directional forcing at mid-lake. That hypothesis remains unresolved until independent WeatherFlow observations (or an equivalent over-water wind record) are available with verified station identity, averaging period, timestamps, exposure, QC and historical coverage. A 12–36h lag is not validated. False alerts also exhibit substantial NWCL1 wind forcing. Prospective, provenance-rich wind archival is justified; operational changes are not.
