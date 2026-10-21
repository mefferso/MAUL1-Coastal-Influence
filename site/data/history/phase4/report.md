# Phase 4 — observation-based evidence evaluation

**Experimental retrospective evidence, not hydrodynamic attribution, forecast skill or operational guidance.**

## Scope and provenance

Evaluated the frozen 189 meaningful native-stage MAUL1 response events and 63 eligible seven-day nonresponse controls from Phase 3B. No observations were downloaded or earlier products replaced. Input SHA-256 hashes, thresholds and calibration distributions are in `provenance.json`. Base repository commit: `1217a498247a85f60c37c4b3a1e882338f53e12e`.

The five-station identities are preserved. DENL1 discharge supports the upstream pathway; NWCL1 same-hour/same-datum residual, independent MDLL1 native change and wind vector coherence support the coastal pathway. MCHL1 remains optional supporting context with explicit quality and datum uncertainty. No USACE substitution is made. Historical MAUL1 00065 is never converted to NAVD88; the established 4.0-ft NAVD88 threshold is not evaluated in Phase 4.

## Frozen physical screening hypotheses

See `methodology.md` for precise windows, units, logic and physical justifications. Thresholds are provisional evidence screens, not fitted event labels. A signal must persist through six completed hourly bins. Missing evidence and observed failure to meet a screen remain separate. A supported pathway can coexist with unavailable evidence for the other pathway; the class is never exclusive attribution.

```json
{
  "baseline_fraction": 0.8,
  "discharge_high_cfs": 4942.5,
  "discharge_ratio": 1.25,
  "discharge_rise_cfs": 5000.0,
  "lake_rise_ft": 0.25,
  "persistence_hours": 6,
  "residual_ft": 0.5,
  "residual_rise_ft": 0.25,
  "wind_axis_degrees": 270.0,
  "wind_projection_knots": 5.0
}
```

## Response events

| Evidence class | Count |
|---|---:|
| River-supported | 41 |
| Coastal-supported | 56 |
| Compound-supported | 7 |
| Indeterminate | 85 |

Indeterminate: 45.0%. Evidence coverage qualified for 176/189 events (all four core flags known for at least 90% of assessed hours). This is temporal evidence availability, not a confidence score. Coverage-qualified class counts:

| Evidence class | Count |
|---|---:|
| River-supported | 36 |
| Coastal-supported | 56 |
| Compound-supported | 7 |
| Indeterminate | 77 |

74 MAUL1 events lack either supported pathway. Both pathways appear in 18 events; 11 contain disjoint signals without simultaneous support and remain indeterminate. A compound label represents coexisting signals, not demonstrated nonlinear interaction. Long excursions can collect unrelated later forcing; their explicit flags must accompany interpretation.

## Independent nonresponse controls

| Evidence class | Count |
|---|---:|
| River-supported | 13 |
| Coastal-supported | 13 |
| Compound-supported | 1 |
| Indeterminate | 36 |

62/63 controls meet Phase 4 evidence coverage. 28 controls contain qualifying forcing support without a meaningful MAUL1 event under the frozen catalogue. These are observational nonresponses, not false forecast alarms. The selection excludes event buffers and uses >=90% coverage in four core water series; wind was not a Phase 3B control eligibility requirement.

Control category memberships overlap. The prior category called elevated_lake_without_qualifying_response was selected from MAUL1 median native stage, not direct lake setup; Phase 4 independently assesses actual lake signals instead of accepting that name as truth.

- elevated_lake_without_qualifying_response: River-supported 1, Coastal-supported 3, Compound-supported 0, Indeterminate 5
- no_qualifying_MAUL1_response_other: River-supported 4, Coastal-supported 5, Compound-supported 1, Indeterminate 10
- quiet_low_variation: River-supported 4, Coastal-supported 3, Compound-supported 0, Indeterminate 6
- routine_variability_without_qualifying_response: River-supported 5, Coastal-supported 5, Compound-supported 0, Indeterminate 20

The Phase 3B archive contains zero eligible controls meeting its >=50,000-cfs upstream-increase category. Phase 4 can find smaller discharge signals, but does not manufacture a robust large-flow nonresponse sample.

## Rule sensitivity

| Variant | River | Coastal | Compound | Indeterminate | Changed events |
|---|---:|---:|---:|---:|---:|
| primary | 41 | 56 | 7 | 85 | 0 |
| lower_magnitudes | 36 | 64 | 10 | 79 | 24 |
| higher_magnitudes | 45 | 47 | 5 | 92 | 14 |
| wind_toward_240 | 40 | 55 | 7 | 87 | 6 |
| wind_toward_300 | 40 | 45 | 5 | 99 | 36 |
| coastal_antecedent_6h | 41 | 56 | 7 | 85 | 0 |
| coastal_antecedent_36h | 41 | 56 | 7 | 85 | 0 |

Magnitudes change together by ±25%, wind transport axes span 240–300° toward the western lake, and coastal antecedent windows span 6–36 hours. These are fixed stress tests rather than optimization. They do not exhaust uncertainty in persistence, baseline, river travel times, thresholds or the Phase 3B event definition. Event-definition sensitivity remains in the preserved Phase 3B reports.

## Temporal split and independence

Fixed 2023-01-01 boundary and 72-hour embargo remain. Phase 4 checks full feature history (78h before the assessment start) and observed event recovery; 21 records change split status compared with the original assignment. 125 record pairs have overlapping feature histories and cannot be treated as independent statistical trials. All pair IDs are in `independence.json`.

Threshold hypotheses and historical cases were informed by prior exploratory work; the temporal holdout is descriptive frozen-rule evaluation, not pristine blind validation.

Per-subset evidence counts (these are descriptive classifications, not accuracy):

```json
{
  "calibration_2016_2022": {
    "events": {
      "River-supported": 27,
      "Coastal-supported": 34,
      "Compound-supported": 5,
      "Indeterminate": 53
    },
    "controls": {
      "River-supported": 8,
      "Coastal-supported": 9,
      "Compound-supported": 0,
      "Indeterminate": 25
    }
  },
  "holdout_2023_onward": {
    "events": {
      "River-supported": 13,
      "Coastal-supported": 22,
      "Compound-supported": 2,
      "Indeterminate": 32
    },
    "controls": {
      "River-supported": 5,
      "Coastal-supported": 4,
      "Compound-supported": 1,
      "Indeterminate": 11
    }
  },
  "excluded_split_seam": {
    "events": {
      "River-supported": 1,
      "Coastal-supported": 0,
      "Compound-supported": 0,
      "Indeterminate": 0
    },
    "controls": {
      "River-supported": 0,
      "Coastal-supported": 0,
      "Compound-supported": 0,
      "Indeterminate": 0
    }
  }
}
```

## Retrospective versus issue-time assessment

The separate replay contains 1011 issue assessments: event offsets -24, 0, +12, +24h, control endpoints and fixed six-hour case clocks. 384/756 event snapshots differ from the eventual retrospective category. These differences measure evolving evidence, not errors or warning lead time.

Completed hourly-bin valid-time-only replay; receipt timestamps unavailable. Event snapshot selection uses retrospective onsets; assessments do not.

Each assessment excludes unfinished bins, uses only trailing features and never reads event peaks, subsequent observations or centered event smoothing. The preserved Phase 3B retrospective catalogue itself uses centered smoothing and full recovery information; its event-conditioned replay sampling is not a real-time event detector. Replay recalculates the discharge upper decile from calibration-era bins completed before each issue and freezes it at the pre-2023 seam; a fixed 20,000-cfs screen applies before 1,000 prior valid hours. Replay ignores future-dependent archived adaptive QC and uses fixed causal hourly jump screens on newly completed endpoints. Parameter sample size and cutoff are recorded per assessment. This remains a research reconstruction, not a model that existed at those dates.

## Priority case findings

### August 2016 Louisiana flood
maul1-response-0007: River-supported (onset 2016-08-14T00:00:00Z, peak 2016-08-17T17:00:00Z)

Event candidates are identified from MAUL1 native stage alone; timing associations are evaluated afterward. Unknown onset or missing coverage limits precursor interpretation. External storm context is not ground truth.

Within-case six-hour snapshots: {'River-supported': 29, 'Coastal-supported': 0, 'Compound-supported': 0, 'Indeterminate': 28}. See `case-studies.md` for values, contradictory observations, missingness and every issue snapshot.

### Tropical Storm Beta
maul1-response-0080: Coastal-supported (onset 2020-09-03T02:00:00Z, peak 2020-09-16T10:00:00Z); maul1-response-0081: Coastal-supported (onset 2020-09-19T06:00:00Z, peak 2020-09-22T23:00:00Z)

Event candidates are identified from MAUL1 native stage alone; timing associations are evaluated afterward. Unknown onset or missing coverage limits precursor interpretation. External storm context is not ground truth.

Within-case six-hour snapshots: {'River-supported': 0, 'Coastal-supported': 12, 'Compound-supported': 0, 'Indeterminate': 33}. See `case-studies.md` for values, contradictory observations, missingness and every issue snapshot.

### November 2024 coastal-advisory window
maul1-response-0154: Indeterminate (onset 2024-10-24T16:00:00Z, peak 2024-11-13T15:00:00Z); maul1-response-0155: River-supported (onset 2024-11-23T14:00:00Z, peak 2024-11-30T19:00:00Z)

Event candidates are identified from MAUL1 native stage alone; timing associations are evaluated afterward. Unknown onset or missing coverage limits precursor interpretation. External storm context is not ground truth.

Within-case six-hour snapshots: {'River-supported': 5, 'Coastal-supported': 0, 'Compound-supported': 0, 'Indeterminate': 40}. See `case-studies.md` for values, contradictory observations, missingness and every issue snapshot.

### April 2025 southeast-wind window
maul1-response-0167: River-supported (onset 2025-03-21T06:00:00Z, peak 2025-04-05T13:00:00Z)

Event candidates are identified from MAUL1 native stage alone; timing associations are evaluated afterward. Unknown onset or missing coverage limits precursor interpretation. External storm context is not ground truth.

Within-case six-hour snapshots: {'River-supported': 17, 'Coastal-supported': 0, 'Compound-supported': 0, 'Indeterminate': 28}. See `case-studies.md` for values, contradictory observations, missingness and every issue snapshot.

## Scientific conclusion and Phase 5 gate

Observation-based evidence screens distinguish some consistent forcing patterns. Unknowns, contradictory signals, long event windows, rule sensitivity and local runoff limit attribution and predictive interpretation.

Not yet stable enough to justify operational forecasts. Supports continued experimental feature research only; no independent reference labels or out-of-sample forecast evaluation.

No classification accuracy is reported: documentary flood/storm reports are independent context but do not supply reference forcing labels. No probability, contribution percentage, flood forecast or advisory recommendation is produced. Before experimental forecasting, independently review event-level labels, broaden nonresponse/large-flow controls, investigate local rainfall and downstream tributaries, assess wind and lag alternatives, and validate prospective receipt-time availability. Phase 5 has not begun.

## Reproduction

Run `python scripts/phase4.py`, then `python scripts/phase4.py --output work/phase4-repeat` and compare output bytes. The dedicated free GitHub Actions job runs these same steps with the full archive. `historical.json` holds witness observations and uncertainty; `replay.json.gz` holds separate issue assessments; CSV is a compact index.
