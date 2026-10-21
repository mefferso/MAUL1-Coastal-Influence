# Phase 4 methodology — provisional observational evidence

This phase asks whether existing observations support physically consistent river, coastal or compound signals around MAUL1 responses. It does not estimate causal fractions, predict MAUL1 levels, calculate exceedance probabilities or recommend advisories. The local 4.0-ft NAVD88 threshold remains a future forecasting objective. No historical native-stage threshold conversions are made.

## Inputs and quality

Use the unchanged Phase 3A monthly hourly archive and the revised Phase 3B catalogue: 189 meaningful MAUL1 excursions (179 known onsets) and 63 eligible seven-day controls in the current input version. Re-read these counts from source products on every run; hashes identify all inputs. Preserve earlier outputs and station identities. No new downloads or source substitutions.

DENL1 is USGS 07378500 discharge (cfs); NWCL1 is CO-OPS 8761927 water and astronomical predictions (same station datum, feet) and winds; MDLL1 is USGS 301200090072400 native stage; MCHL1 is HADS CE678A12 native stage; MAUL1 is USGS 07380215 native 00065 stage. MDLL1, MCHL1 and MAUL1 elevations are not equated. Historical 00065 and direct 63160 remain separate. No USACE 85420/85420LA substitution occurs.

An hourly bin is eligible only after its end. At 06:00 UTC the latest eligible bin starts at 05:00 UTC. A valid value is finite, has at least one raw observation contributing, is not explicitly missing, uses the expected unit and has a documented native datum identifier. A current six-hour persistence interval must have six valid bins. Baselines require at least 80% of their bins. Native-change comparisons require the current/baseline union to contain one datum. No interpolation or centered smoothing is used by the evidence engine.

Archive quality findings are candidate flags, not verified sensor errors. For retrospective interpretation conservatively exclude each flagged endpoint hour; propagate wind/direction flags to vector components. The archived flags chiefly concern MCHL1 jumps and gusts. This conservative screen cannot certify sensors or identify unflagged problems. Hourly aggregates do not retain all raw quality codes, within-hour timing or within-hour datum transitions. These are limitations, not clean-data certification. Original raw source quality handling remains as implemented by the acquisition layer. Replay ignores the archived adaptive full-month findings, which could depend on future observations. Instead it applies fixed causal hourly jump screens: 5 ft for stage/water/prediction, 10,000 cfs for discharge and 50 knots for each wind component. Compare only adjacent completed bins with the same unit and datum; flag only the newly completed endpoint and never its preceding bin. These coarse quality screens are not instrument certification and differ from the retrospective raw-data quality review.

NWCL1 residual is observed hourly water minus predicted hourly water only for the same UTC hour, matching nonempty datum and feet. The archive aggregates water/prediction with its established hourly medians; the resulting difference is an hourly residual and is not claimed to equal the median of exact-time raw residuals. A positive residual alone is insufficient.

## Hourly evidence rules frozen before outcome inspection

All pathways are evaluated at a completed-hour decision time `t`. Current means the six completed bins `[t−6h,t)`. A preceding reference baseline means `[t−72h,t−24h)`, which leaves a 24-hour separation from the decision time. This is a comparative antecedent reference, not an astronomical or datum reference.

### River

River evidence is present if all six current discharge bins are at or above the calibration-era 90th percentile, **or** the minimum current discharge exceeds the maximum discharge in `[t−78h,t−72h)` by at least 5,000 cfs and a factor of at least 1.25. This conservative comparison requires a sustained, material 72-hour increase rather than an isolated spike. Rate in cfs/hour is the conservative increase divided by 72, reported descriptively. The high-flow branch captures coastal setup during already elevated river flow without requiring a fresh rise. Percentiles use only valid 2016 through 2022-12-28 23:00 UTC observations, excluding the 72-hour split seam. No response labels or post-2022 discharge enter calibration.

The 5,000-cfs/25% rise and upper-decile level are deliberately simple screening hypotheses. They are not calibrated travel-time or MAUL1-impact thresholds. River is unknown when required bins or same-datum antecedents are missing (a fully observed elevated-flow condition can establish support without the antecedent comparison). Observed absence means only that DENL1 did not meet these screens. It cannot establish absence of river influence: tributary and local runoff enter downstream of DENL1. There is no universal DENL1-to-MAUL1 travel lag.

### Coastal

Require **all** of the following in the same six-hour interval:

1. Minimum NWCL1 residual >=0.50 ft and at least 0.25 ft above the median preceding reference baseline.
2. Minimum current MDLL1 stage at least 0.25 native foot above its own median preceding reference baseline, with a consistent native datum.
3. Every hourly wind transport vector has at least 5 knots projected toward 270° (westward). Components are meteorological wind converted to transport vectors by the archive before averaging. East/NE/SE winds can contribute westward transport; a scalar averaged compass direction is never used.

This tests a coherent lake-setup mechanism: non-tidal New Canal rise plus independent midlake rise and persistent wind transporting water toward the western lake. The direction is a physical hypothesis, not a validated optimal axis for all lake circulation. Directional stress tests toward 240° and 300° reveal dependence on orientation. Independent lake response helps distinguish broad setup from an isolated station residual; local wind and two lake stations still cannot reconstruct the full pressure gradient or circulation. Requiring fresh rise can miss sustained lake setup after the baseline rises; the missing-detection cost is acknowledged.

If any requirement is observed absent, the coastal pathway fails its screen; missing component flags remain separately unknown. If no requirement is absent and a component is unavailable, coastal is unknown. Opposing winds or absent independent confirmation alongside a residual are recorded as contradictory observations. A failed screen does not prove coastal influence absent.

MCHL1 native change uses the same lake rise diagnostic but is optional propagation context only. No propagation lag, station identity conversion, or datum certainty is inferred from it. Sparse and suspect observations cannot make or break the core coastal classification.

### Response and categories

An auxiliary causal response screen compares MAUL1 current six-hour median with its own preceding baseline; >=0.25 native foot is marked detected, otherwise not detected, and missing/datum-inconsistent comparisons are uncertain. It is a separate screen and does not recreate the >=1-ft retrospective event detector or control selection.

River-supported: river present without simultaneous coastal support. Coastal-supported: coastal present without simultaneous river support. Compound-supported: both independent pathways present at the same issue time. Indeterminate: neither pathway supported, or (at event scale) both appear but never coexist. Missing opposite-path evidence remains explicit; one supported pathway is not exclusive attribution. Persistent river and coastal conditions are both positive evidence, not mutually contradictory by definition. Compound means overlapping support, not a proven interaction or percentage contribution.

## Retrospective aggregation and timing

Use frozen Phase 3B events; they retain centered three-hour smoothing, native rise >=1 ft, observed recovery and censored onsets. Phase 4 does not change that retrospective selection. Assess hourly from provisional MAUL1 onset minus 72 hours through the completion of its peak bin. River evidence can precede onset by up to 72 hours; coastal evidence earlier than onset minus 18 hours is ineligible for association with that event. Signals later in the rising limb are retained as concurrent response context, not advance warning. These are association-window hypotheses, not measured universal propagation times. Report first/last support and relative times only when onset is known.

At least one persistent hourly screen establishes an event-scale pathway; at least one common interval is required for compound. River and coastal support only in disjoint intervals is explicitly sequential and indeterminate. A first/last range does not imply uninterrupted evidence; present/absent/unknown counts and hourly classifications preserve intermittency. Witness assessments contain actual values, units, baseline and coverage. Missing and contradictory observations are unioned across the full window and may describe different hours. Long excursions (>168-hour rising limb) are flagged because later forcing can be unrelated to the original onset.

Coverage qualified means all four core flags (river, residual, lake and wind) are known during >=90% of assessment hours; it does not imply every pathway was supported, that onset was observed, or that quality is certified. MCHL1 and the auxiliary MAUL1 screen are reported separately and do not enter this evidence-sufficiency definition.

Controls retain the exact 63 frozen Phase 3B seven-day windows; assess their completed hours and preserve original coverage, event-buffer exclusions and categories. The old category called elevated lake was actually selected by elevated MAUL1 median stage: it is not independent lake ground truth. Report actual independent lake forcing from Phase 4. River/coastal support in controls is forcing without a qualifying target event, not a false alarm or forecast failure. Zero large-flow controls under the earlier >=50,000-cfs criterion is a sample gap.

## Issue-time replay

Store issue assessments separately from retrospective aggregate labels. Features use causal trailing bins only; current/future bins and future event peaks cannot enter decisions. Sample four times per historical response (-24, 0, +12 and +24h relative to the retrospective onset), at control endpoints, and fixed six-hour clocks throughout each priority case. The event-conditioned sampling schedule uses future catalogue knowledge; it is not a real-time issue schedule or target detector. For each replay issue, the discharge upper-decile parameter uses only calibration-era bins completed before that issue, freezing at the pre-2023 seam. Before 1,000 prior valid discharge hours exist, use a fixed 20,000-cfs high-flow screen; record the sample size and training cutoff in every assessment. No future observations enter replay parameter estimation. These are research hypotheses, not models that actually existed at those historical times.

The archive lacks original receipt timestamps and revision history. This is **valid-time-only replay**, not verified operational data availability. NOAA predictions are restricted to completed valid-time bins even though forecasts could have existed earlier. No operational readiness follows from this exercise.

## Evaluation and independence

Physical thresholds and sensitivity settings are frozen before inspecting class distributions. Report ±25% magnitude screens, 240°/300° wind axes, and 6-/36-hour coastal antecedent windows; never choose a winner for agreement with named cases. Existing Phase 3B event-threshold/recovery sensitivity is preserved. The stress tests do not span all possible baselines, persistence or travel times.

Maintain fixed 2023-01-01 split and 72-hour embargo, assigning whole retrospective responses through observed recovery. Extend split checks over the assessment's antecedent and 78-hour feature history. Identify overlapping feature windows explicitly; do not claim independent binomial trials or compute confidence intervals from them. Cases and past exploratory work already inform scientific understanding of the holdout; describe per-subset distributions without claiming pristine blind validation or tuning against them.

Compare independent NCEI documentary context with observations for August 2016, Beta 2020, November 2024 and April 2025. Retain 2016 censored onset, Beta's 4.04-ft NAVD88 report as external context, November's recovery-versus-November-23-onset distinction, and April's earlier March onset. Named disasters cannot assign labels. No classification accuracy is calculated without independent reference forcing labels. Output counts and sensitivity establish evidence behavior, not predictive skill. Do not begin Phase 5 automatically.
