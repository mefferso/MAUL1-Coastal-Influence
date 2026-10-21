# Phase 4 detailed case studies

All classifications describe experimental supporting observations. Event-scale interpretations and named-case snapshots cover different intervals. Absolute native elevations are never compared across stations.

## August 2016 Louisiana flood

Case window: 2016-08-09T00:00:00Z to 2016-08-23T00:00:00Z (end exclusive for observations).

Case context is independent documentary information, not reference labels. Full-event interpretations may extend outside this named case; within-case snapshots are shown separately.

Event candidates are identified from MAUL1 native stage alone; timing associations are evaluated afterward. Unknown onset or missing coverage limits precursor interpretation. External storm context is not ground truth.

Independent documentary context (NCEI event 657049): NCEI narrative states two days of heavy rain drained into the Amite River, record river levels, and backwater flooding; it reports about 16,000 homes/businesses with varying damage.

Independent documentary context (NCEI event 657054): NCEI narrative links record Amite River levels to upstream flow/backwater flooding along the Blind River.

### maul1-response-0007 — River-supported

Onset 2016-08-14T00:00:00Z (censored/uncertain); peak 2016-08-17T17:00:00Z; native rise 3.25 ft; recovery ends 2016-08-22T14:00:00Z. Evidence-sufficient hours: 100.0%. Coexistence: 0 h.

Supporting: lake: persistent observational support; lake: persistent observational support (physical observation outside eligible coastal association window); residual: persistent observational support; river: persistent observational support.

Contradictory: No qualifying DENL1 discharge level/rise; this does not exclude downstream river inputs; Positive residual lacks lake support in the same six-hour interval; Positive residual lacks wind support in the same six-hour interval.

Missing/unreliable: pass_context: insufficient valid coverage, quality or datum continuity.

Uncertainty: Retrospective supporting evidence is not a causal label, forecast or demonstrated interaction.; Event selection and assessment windows use the full historical response catalogue.; DENL1 absence cannot exclude tributary/local runoff downstream.; Hourly means preserve native datums; same-hour residual pairing may differ from raw coincident residuals.; MAUL1 onset is censored; timing relative to true onset is unknown.

| Pathway | First support UTC | Last support UTC | First relative to MAUL1 onset (h) | Present / absent / unknown hours |
|---|---|---|---:|---|
| river | 2016-08-12T08:00:00Z | 2016-08-17T18:00:00Z | None | 131 / 32 / 0 |
| residual | 2016-08-15T02:00:00Z | 2016-08-17T16:00:00Z | None | 63 / 100 / 0 |
| lake | 2016-08-11T00:00:00Z | 2016-08-17T11:00:00Z | None | 78 / 85 / 0 |
| wind | None | None | None | 0 / 163 / 0 |
| coastal | None | None | None | 0 / 109 / 54 |
| pass_context | None | None | None | 0 / 0 / 163 |

#### First river witness — 2016-08-12T08:00:00Z

River-supported: river=present; coastal association excluded before the event's coastal antecedent window (physical coastal screen=absent). This exclusion is not missing observations.

```json
{
  "discharge": {
    "antecedent_median_cfs": 2302.5,
    "conservative_72h_rise_cfs": 2575.0,
    "conservative_ratio": 2.0684647302904566,
    "current_median_cfs": 6820.0,
    "elevated_discharge": true,
    "rise_rate_cfs_per_hour": 35.763888888888886,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": null,
      "conservative_rise_native_ft": null,
      "current_median_ft": null,
      "current_minimum_ft": null
    },
    "MDLL1:stage": {
      "baseline_median_ft": 0.2,
      "conservative_rise_native_ft": -0.845,
      "current_median_ft": -0.59,
      "current_minimum_ft": -0.645
    },
    "NWCL1:residual": {
      "baseline_median_ft": 0.18075,
      "conservative_rise_native_ft": -0.81075,
      "current_median_ft": -0.5774999999999999,
      "current_minimum_ft": -0.63
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.35525,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": -0.19774999999999998,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": null,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 221.8502922028908,
    "directional_persistence": 0.9712164515328875,
    "projected_minimum_knots": -4.429913,
    "speed_of_mean_vector_knots": 5.3333058285188795,
    "u_mean_knots": 3.55831,
    "v_mean_knots": 3.972729666666667
  }
}
```

#### First indeterminate witness — 2016-08-11T00:00:00Z

Indeterminate: river=absent; coastal association excluded before the event's coastal antecedent window (physical coastal screen=absent). This exclusion is not missing observations.

```json
{
  "discharge": {
    "antecedent_median_cfs": 1442.5,
    "conservative_72h_rise_cfs": 10.0,
    "conservative_ratio": 1.0066445182724253,
    "current_median_cfs": 1530.0,
    "elevated_discharge": false,
    "rise_rate_cfs_per_hour": 0.1388888888888889,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": null,
      "conservative_rise_native_ft": null,
      "current_median_ft": null,
      "current_minimum_ft": null
    },
    "MDLL1:stage": {
      "baseline_median_ft": -0.055,
      "conservative_rise_native_ft": 0.255,
      "current_median_ft": 0.37,
      "current_minimum_ft": 0.2
    },
    "NWCL1:residual": {
      "baseline_median_ft": 0.0165,
      "conservative_rise_native_ft": 0.097,
      "current_median_ft": 0.2005,
      "current_minimum_ft": 0.1135
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.5825,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": 0.79125,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": null,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 236.87453800423552,
    "directional_persistence": 0.9383260188814327,
    "projected_minimum_knots": -9.304599,
    "speed_of_mean_vector_knots": 5.564100885091261,
    "u_mean_knots": 4.6598006666666665,
    "v_mean_knots": 3.0406375
  }
}
```

### Historical issue-time snapshots

Six-hour fixed UTC clocks. Q is the trailing six-hour median cfs. Δlake is the minimum current MDLL1 stage minus its prior 48-hour median ending 24h earlier, in native feet. Wind is the minimum projection toward 270° in knots. These columns are observations/screens, not forecasts. Full flags, coverage, missing/contradictory evidence and metrics are in `cases.json` and the separate replay dataset.

| UTC decision time | Class | River / residual / lake / wind | Q cfs | Residual ft | Δlake ft | West wind kt | MAUL1 response screen |
|---|---|---|---:|---:|---:|---:|---|
| 2016-08-09T00:00:00Z | Indeterminate | absent / absent / absent / absent | 2545.000 | -0.021 | -0.505 | -3.894 | uncertain |
| 2016-08-09T06:00:00Z | Indeterminate | absent / absent / absent / absent | 2390.000 | -0.127 | -0.510 | -1.150 | uncertain |
| 2016-08-09T12:00:00Z | Indeterminate | absent / absent / absent / absent | 2140.000 | -0.077 | -0.450 | -1.759 | uncertain |
| 2016-08-09T18:00:00Z | Indeterminate | absent / absent / absent / absent | 1920.000 | 0.173 | -0.137 | -1.759 | uncertain |
| 2016-08-10T00:00:00Z | Indeterminate | absent / absent / absent / absent | 1690.000 | 0.270 | 0.052 | -2.191 | uncertain |
| 2016-08-10T06:00:00Z | Indeterminate | absent / absent / absent / absent | 1597.500 | 0.186 | 0.130 | -1.183 | uncertain |
| 2016-08-10T12:00:00Z | Indeterminate | absent / absent / absent / absent | 1610.000 | 0.179 | 0.175 | -5.200 | uncertain |
| 2016-08-10T18:00:00Z | Indeterminate | absent / absent / present / absent | 1592.500 | 0.270 | 0.265 | -2.435 | uncertain |
| 2016-08-11T00:00:00Z | Indeterminate | absent / absent / present / absent | 1530.000 | 0.201 | 0.255 | -9.305 | uncertain |
| 2016-08-11T06:00:00Z | Indeterminate | absent / absent / absent / absent | 3090.000 | 0.108 | -0.015 | -7.694 | uncertain |
| 2016-08-11T12:00:00Z | Indeterminate | absent / absent / absent / absent | 3330.000 | -0.139 | -0.383 | -6.881 | uncertain |
| 2016-08-11T18:00:00Z | Indeterminate | absent / absent / absent / absent | 2900.000 | -0.341 | -0.468 | -6.880 | uncertain |
| 2016-08-12T00:00:00Z | Indeterminate | absent / absent / absent / absent | 3120.000 | -0.466 | -0.535 | -7.454 | uncertain |
| 2016-08-12T06:00:00Z | Indeterminate | absent / absent / absent / absent | 5312.500 | -0.580 | -0.840 | -4.807 | uncertain |
| 2016-08-12T12:00:00Z | River-supported | present / absent / absent / absent | 9187.500 | -0.622 | -0.845 | -7.649 | uncertain |
| 2016-08-12T18:00:00Z | River-supported | present / absent / absent / absent | 16175.000 | -0.641 | -0.640 | -8.040 | uncertain |
| 2016-08-13T00:00:00Z | River-supported | present / absent / absent / absent | 33075.000 | -0.710 | -0.463 | -6.979 | uncertain |
| 2016-08-13T06:00:00Z | River-supported | present / absent / absent / absent | 51275.000 | -0.648 | -0.550 | -4.953 | uncertain |
| 2016-08-13T12:00:00Z | River-supported | present / absent / absent / absent | 76950.000 | -0.626 | -0.438 | -4.768 | uncertain |
| 2016-08-13T18:00:00Z | Indeterminate | unknown / absent / absent / absent | 119000.000 | -0.509 | -0.103 | -2.421 | uncertain |
| 2016-08-14T00:00:00Z | Indeterminate | unknown / absent / present / absent | 170000.000 | -0.181 | 0.345 | -1.931 | uncertain |
| 2016-08-14T06:00:00Z | Indeterminate | unknown / absent / absent / absent | 237500.000 | -0.158 | 0.180 | 0.074 | uncertain |
| 2016-08-14T12:00:00Z | River-supported | present / absent / present / absent | 263000.000 | -0.040 | 0.260 | -3.100 | uncertain |
| 2016-08-14T18:00:00Z | River-supported | present / absent / present / absent | 231500.000 | 0.270 | 0.610 | -1.065 | uncertain |
| 2016-08-15T00:00:00Z | River-supported | present / absent / present / absent | 177500.000 | 0.546 | 1.090 | -1.717 | uncertain |
| 2016-08-15T06:00:00Z | River-supported | present / present / present / absent | 143250.000 | 0.654 | 0.990 | 0.018 | uncertain |
| 2016-08-15T12:00:00Z | River-supported | present / present / present / absent | 117000.000 | 0.677 | 0.787 | 0.328 | uncertain |
| 2016-08-15T18:00:00Z | River-supported | present / present / present / absent | 100350.000 | 0.707 | 0.810 | 1.218 | uncertain |
| 2016-08-16T00:00:00Z | River-supported | present / present / present / absent | 88475.000 | 0.899 | 1.070 | 1.632 | uncertain |
| 2016-08-16T06:00:00Z | River-supported | present / present / present / absent | 77625.000 | 0.964 | 0.985 | 0.149 | uncertain |
| 2016-08-16T12:00:00Z | River-supported | present / present / present / absent | 65550.000 | 1.034 | 0.705 | 0.715 | detected |
| 2016-08-16T18:00:00Z | River-supported | present / present / present / absent | 52950.000 | 0.999 | 0.365 | 0.583 | detected |
| 2016-08-17T00:00:00Z | River-supported | present / present / present / absent | 44000.000 | 1.140 | 0.490 | -0.970 | detected |
| 2016-08-17T06:00:00Z | River-supported | present / present / present / absent | 36975.000 | 1.207 | 0.578 | 0.083 | detected |
| 2016-08-17T12:00:00Z | River-supported | present / present / absent / absent | 30600.000 | 1.200 | 0.222 | 0.157 | detected |
| 2016-08-17T18:00:00Z | River-supported | present / absent / absent / absent | 25000.000 | 1.030 | 0.093 | 0.214 | detected |
| 2016-08-18T00:00:00Z | River-supported | present / absent / absent / absent | 20225.000 | 1.093 | 0.160 | 1.595 | detected |
| 2016-08-18T06:00:00Z | River-supported | present / absent / present / absent | 16850.000 | 1.162 | 0.275 | 0.370 | detected |
| 2016-08-18T12:00:00Z | River-supported | present / absent / absent / absent | 14925.000 | 1.147 | -0.077 | 0.161 | detected |
| 2016-08-18T18:00:00Z | River-supported | present / absent / absent / absent | 13550.000 | 0.996 | -0.172 | -1.332 | detected |
| 2016-08-19T00:00:00Z | River-supported | present / absent / absent / absent | 12500.000 | 0.990 | -0.125 | -0.683 | not_detected |
| 2016-08-19T06:00:00Z | River-supported | present / absent / absent / absent | 11700.000 | 1.005 | -0.010 | -0.003 | not_detected |
| 2016-08-19T12:00:00Z | River-supported | present / absent / absent / absent | 10825.000 | 0.928 | -0.350 | 0.144 | not_detected |
| 2016-08-19T18:00:00Z | River-supported | present / absent / absent / absent | 9705.000 | 0.789 | -0.400 | -3.052 | not_detected |
| 2016-08-20T00:00:00Z | River-supported | present / absent / absent / absent | 8687.500 | 0.707 | -0.427 | -3.542 | not_detected |
| 2016-08-20T06:00:00Z | River-supported | present / absent / absent / absent | 7700.000 | 0.700 | -0.295 | -1.592 | not_detected |
| 2016-08-20T12:00:00Z | Indeterminate | absent / absent / absent / absent | 6600.000 | 0.598 | -0.525 | -2.177 | not_detected |
| 2016-08-20T18:00:00Z | Indeterminate | absent / absent / absent / absent | 5665.000 | 0.459 | -0.605 | -2.383 | not_detected |
| 2016-08-21T00:00:00Z | Indeterminate | absent / absent / absent / absent | 4987.500 | 0.330 | -0.602 | -4.080 | not_detected |
| 2016-08-21T06:00:00Z | Indeterminate | absent / absent / absent / absent | 4657.500 | 0.413 | -0.430 | -2.680 | not_detected |
| 2016-08-21T12:00:00Z | Indeterminate | absent / absent / absent / absent | 4390.000 | 0.315 | -0.572 | -2.057 | not_detected |
| 2016-08-21T18:00:00Z | Indeterminate | absent / absent / absent / absent | 4050.000 | 0.223 | -0.515 | -2.762 | not_detected |
| 2016-08-22T00:00:00Z | Indeterminate | absent / absent / absent / absent | 3805.000 | 0.161 | -0.605 | -0.127 | not_detected |
| 2016-08-22T06:00:00Z | Indeterminate | absent / absent / absent / absent | 4355.000 | 0.188 | -0.485 | 0.205 | not_detected |
| 2016-08-22T12:00:00Z | Indeterminate | absent / absent / absent / absent | 3920.000 | 0.099 | -0.465 | 0.152 | not_detected |
| 2016-08-22T18:00:00Z | Indeterminate | absent / absent / absent / absent | 3457.500 | 0.075 | -0.350 | -0.137 | not_detected |
| 2016-08-23T00:00:00Z | Indeterminate | absent / absent / absent / absent | 3255.000 | 0.088 | -0.397 | -3.938 | not_detected |

## Tropical Storm Beta

Case window: 2020-09-18T00:00:00Z to 2020-09-29T00:00:00Z (end exclusive for observations).

Case context is independent documentary information, not reference labels. Full-event interpretations may extend outside this named case; within-case snapshots are shown separately.

Event candidates are identified from MAUL1 native stage alone; timing associations are evaluated afterward. Unknown onset or missing coverage limits precursor interpretation. External storm context is not ground truth.

Independent documentary context (NCEI event 921987): NCEI narrative reports 4.04 ft NAVD88 at USGS MAUL1 and 5.47 ft NAVD88 at USACE TSPL1 at 19:00 CDT; its episode narrative describes persistent moderate/strong onshore east and northeast winds and impacts Sep 19–23.

Independent documentary context (NCEI event 921979): NCEI narrative reports 3.83 ft MHHW at NOS New Canal NWCL1 and a separate 4.66 ft NAVD88 at USACE PRSL1. The NWCL1 MHHW value is not directly interchangeable with NAVD88.

### maul1-response-0080 — Coastal-supported

Onset 2020-09-03T02:00:00Z (known); peak 2020-09-16T10:00:00Z; native rise 2.255 ft; recovery ends 2020-09-19T06:00:00Z. Evidence-sufficient hours: 100.0%. Coexistence: 0 h.

Supporting: lake: persistent observational support; residual: persistent observational support; wind: persistent observational support.

Contradictory: No qualifying DENL1 discharge level/rise; this does not exclude downstream river inputs; Positive residual lacks lake support in the same six-hour interval; Positive residual lacks wind support in the same six-hour interval.

Missing/unreliable: pass_context: insufficient valid coverage, quality or datum continuity.

Uncertainty: Retrospective supporting evidence is not a causal label, forecast or demonstrated interaction.; Event selection and assessment windows use the full historical response catalogue.; DENL1 absence cannot exclude tributary/local runoff downstream.; Hourly means preserve native datums; same-hour residual pairing may differ from raw coincident residuals.; Long response excursion: later forcing episodes may be unrelated to its original onset.

| Pathway | First support UTC | Last support UTC | First relative to MAUL1 onset (h) | Present / absent / unknown hours |
|---|---|---|---:|---|
| river | None | None | None | 0 / 394 / 0 |
| residual | 2020-09-07T23:00:00Z | 2020-09-16T11:00:00Z | 117.0 | 104 / 290 / 0 |
| lake | 2020-09-06T19:00:00Z | 2020-09-16T11:00:00Z | 89.0 | 124 / 270 / 0 |
| wind | 2020-09-06T10:00:00Z | 2020-09-15T13:00:00Z | 80.0 | 78 / 316 / 0 |
| coastal | 2020-09-07T23:00:00Z | 2020-09-15T13:00:00Z | 117.0 | 26 / 314 / 54 |
| pass_context | None | None | None | 0 / 0 / 394 |

#### First coastal witness — 2020-09-07T23:00:00Z

Coastal-supported: river=absent; coastal=present requires residual=present, independent lake=present, wind=present.

```json
{
  "discharge": {
    "antecedent_median_cfs": 545.75,
    "conservative_72h_rise_cfs": -79.25,
    "conservative_ratio": 0.8572072072072072,
    "current_median_cfs": 477.5,
    "elevated_discharge": false,
    "rise_rate_cfs_per_hour": -1.1006944444444444,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": null,
      "conservative_rise_native_ft": null,
      "current_median_ft": null,
      "current_minimum_ft": null
    },
    "MDLL1:stage": {
      "baseline_median_ft": 0.46,
      "conservative_rise_native_ft": 0.36999999999999994,
      "current_median_ft": 0.91,
      "current_minimum_ft": 0.83
    },
    "NWCL1:residual": {
      "baseline_median_ft": 0.20875,
      "conservative_rise_native_ft": 0.29374999999999996,
      "current_median_ft": 0.55175,
      "current_minimum_ft": 0.5025
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.75375,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": 1.29975,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": 0.4524999999999997,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 37.73812729395189,
    "directional_persistence": 0.994389023718433,
    "projected_minimum_knots": 5.2731590000000015,
    "speed_of_mean_vector_knots": 9.762778246557268,
    "u_mean_knots": -5.975341833333333,
    "v_mean_knots": -7.720565333333333
  }
}
```

#### First indeterminate witness — 2020-08-31T02:00:00Z

Indeterminate: river=absent; coastal association excluded before the event's coastal antecedent window (physical coastal screen=absent). This exclusion is not missing observations.

```json
{
  "discharge": {
    "antecedent_median_cfs": 2260.0,
    "conservative_72h_rise_cfs": -1388.0,
    "conservative_ratio": 0.393224043715847,
    "current_median_cfs": 920.375,
    "elevated_discharge": false,
    "rise_rate_cfs_per_hour": -19.27777777777778,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": null,
      "conservative_rise_native_ft": null,
      "current_median_ft": null,
      "current_minimum_ft": null
    },
    "MDLL1:stage": {
      "baseline_median_ft": 1.605,
      "conservative_rise_native_ft": -0.91,
      "current_median_ft": 0.79,
      "current_minimum_ft": 0.695
    },
    "NWCL1:residual": {
      "baseline_median_ft": 1.2645,
      "conservative_rise_native_ft": -1.0775,
      "current_median_ft": 0.31525000000000003,
      "current_minimum_ft": 0.187
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.8262499999999999,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": 1.15075,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": -1.1025,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 209.34662201604613,
    "directional_persistence": 0.9962588658447001,
    "projected_minimum_knots": -3.4253890000000013,
    "speed_of_mean_vector_knots": 5.934043197207639,
    "u_mean_knots": 2.9082265,
    "v_mean_knots": 5.172532
  }
}
```
### maul1-response-0081 — Coastal-supported

Onset 2020-09-19T06:00:00Z (known); peak 2020-09-22T23:00:00Z; native rise 2.425 ft; recovery ends 2020-09-26T13:00:00Z. Evidence-sufficient hours: 100.0%. Coexistence: 0 h.

Supporting: lake: persistent observational support; lake: persistent observational support (physical observation outside eligible coastal association window); residual: persistent observational support; residual: persistent observational support (physical observation outside eligible coastal association window); wind: persistent observational support.

Contradictory: No qualifying DENL1 discharge level/rise; this does not exclude downstream river inputs; Positive residual lacks lake support in the same six-hour interval; Positive residual lacks wind support in the same six-hour interval.

Missing/unreliable: pass_context: insufficient valid coverage, quality or datum continuity.

Uncertainty: Retrospective supporting evidence is not a causal label, forecast or demonstrated interaction.; Event selection and assessment windows use the full historical response catalogue.; DENL1 absence cannot exclude tributary/local runoff downstream.; Hourly means preserve native datums; same-hour residual pairing may differ from raw coincident residuals.

| Pathway | First support UTC | Last support UTC | First relative to MAUL1 onset (h) | Present / absent / unknown hours |
|---|---|---|---:|---|
| river | None | None | None | 0 / 163 / 0 |
| residual | 2020-09-16T06:00:00Z | 2020-09-22T22:00:00Z | -72.0 | 88 / 75 / 0 |
| lake | 2020-09-16T06:00:00Z | 2020-09-23T00:00:00Z | -72.0 | 88 / 75 / 0 |
| wind | 2020-09-18T13:00:00Z | 2020-09-22T21:00:00Z | -17.0 | 94 / 69 / 0 |
| coastal | 2020-09-19T21:00:00Z | 2020-09-22T21:00:00Z | 15.0 | 73 / 36 / 54 |
| pass_context | None | None | None | 0 / 0 / 163 |

#### First coastal witness — 2020-09-19T21:00:00Z

Coastal-supported: river=absent; coastal=present requires residual=present, independent lake=present, wind=present.

```json
{
  "discharge": {
    "antecedent_median_cfs": 457.625,
    "conservative_72h_rise_cfs": -11.5,
    "conservative_ratio": 0.9752821063944116,
    "current_median_cfs": 455.625,
    "elevated_discharge": false,
    "rise_rate_cfs_per_hour": -0.1597222222222222,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": null,
      "conservative_rise_native_ft": null,
      "current_median_ft": null,
      "current_minimum_ft": null
    },
    "MDLL1:stage": {
      "baseline_median_ft": 1.2025000000000001,
      "conservative_rise_native_ft": 0.25249999999999995,
      "current_median_ft": 1.54,
      "current_minimum_ft": 1.455
    },
    "NWCL1:residual": {
      "baseline_median_ft": 0.96075,
      "conservative_rise_native_ft": 0.25875000000000004,
      "current_median_ft": 1.29075,
      "current_minimum_ft": 1.2195
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.72725,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": 2.02175,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": -0.1200000000000001,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 60.16685612856702,
    "directional_persistence": 0.997554920644975,
    "projected_minimum_knots": 15.461339000000002,
    "speed_of_mean_vector_knots": 21.96771276828165,
    "u_mean_knots": -19.056503666666668,
    "v_mean_knots": -10.928406666666667
  }
}
```

#### First indeterminate witness — 2020-09-16T06:00:00Z

Indeterminate: river=absent; coastal association excluded before the event's coastal antecedent window (physical coastal screen=absent). This exclusion is not missing observations.

```json
{
  "discharge": {
    "antecedent_median_cfs": 505.625,
    "conservative_72h_rise_cfs": -35.0,
    "conservative_ratio": 0.931237721021611,
    "current_median_cfs": 476.75,
    "elevated_discharge": false,
    "rise_rate_cfs_per_hour": -0.4861111111111111,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": null,
      "conservative_rise_native_ft": null,
      "current_median_ft": null,
      "current_minimum_ft": null
    },
    "MDLL1:stage": {
      "baseline_median_ft": 1.5975000000000001,
      "conservative_rise_native_ft": 1.5825,
      "current_median_ft": 3.4675000000000002,
      "current_minimum_ft": 3.18
    },
    "NWCL1:residual": {
      "baseline_median_ft": 1.32025,
      "conservative_rise_native_ft": 1.84725,
      "current_median_ft": 3.2737499999999997,
      "current_minimum_ft": 3.1675
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.84325,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": 4.1377500000000005,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": 1.0125000000000002,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 6.417595050437001,
    "directional_persistence": 0.9989148368434754,
    "projected_minimum_knots": 0.5201880000000036,
    "speed_of_mean_vector_knots": 20.36088477751482,
    "u_mean_knots": -2.2758196666666666,
    "v_mean_knots": -20.233296166666666
  }
}
```

### Historical issue-time snapshots

Six-hour fixed UTC clocks. Q is the trailing six-hour median cfs. Δlake is the minimum current MDLL1 stage minus its prior 48-hour median ending 24h earlier, in native feet. Wind is the minimum projection toward 270° in knots. These columns are observations/screens, not forecasts. Full flags, coverage, missing/contradictory evidence and metrics are in `cases.json` and the separate replay dataset.

| UTC decision time | Class | River / residual / lake / wind | Q cfs | Residual ft | Δlake ft | West wind kt | MAUL1 response screen |
|---|---|---|---:|---:|---:|---:|---|
| 2020-09-18T00:00:00Z | Indeterminate | absent / absent / absent / absent | 441.875 | 0.952 | -1.495 | -4.522 | not_detected |
| 2020-09-18T06:00:00Z | Indeterminate | absent / absent / absent / absent | 444.875 | 0.984 | -1.510 | -3.066 | not_detected |
| 2020-09-18T12:00:00Z | Indeterminate | absent / absent / absent / absent | 447.500 | 0.879 | -1.680 | 2.255 | not_detected |
| 2020-09-18T18:00:00Z | Indeterminate | absent / absent / absent / absent | 445.250 | 0.743 | -1.200 | 2.289 | not_detected |
| 2020-09-19T00:00:00Z | Indeterminate | absent / absent / absent / absent | 440.750 | 0.788 | -0.685 | -0.226 | not_detected |
| 2020-09-19T06:00:00Z | Indeterminate | absent / absent / absent / present | 441.875 | 0.970 | -0.325 | 7.897 | not_detected |
| 2020-09-19T12:00:00Z | Indeterminate | absent / absent / absent / present | 445.375 | 0.939 | -0.320 | 13.261 | not_detected |
| 2020-09-19T18:00:00Z | Indeterminate | absent / absent / absent / present | 454.500 | 1.183 | -0.032 | 17.666 | not_detected |
| 2020-09-20T00:00:00Z | Coastal-supported | absent / present / present / present | 458.000 | 1.417 | 0.363 | 15.461 | not_detected |
| 2020-09-20T06:00:00Z | Coastal-supported | absent / present / present / present | 460.000 | 1.700 | 0.630 | 17.233 | not_detected |
| 2020-09-20T12:00:00Z | Coastal-supported | absent / present / present / present | 457.875 | 2.008 | 0.923 | 17.523 | detected |
| 2020-09-20T18:00:00Z | Coastal-supported | absent / present / present / present | 461.125 | 2.321 | 1.455 | 23.535 | detected |
| 2020-09-21T00:00:00Z | Coastal-supported | absent / present / present / present | 476.625 | 2.713 | 1.675 | 23.416 | detected |
| 2020-09-21T06:00:00Z | Coastal-supported | absent / present / present / present | 471.875 | 3.035 | 1.980 | 21.860 | detected |
| 2020-09-21T12:00:00Z | Coastal-supported | absent / present / present / present | 458.625 | 3.217 | 2.232 | 19.105 | detected |
| 2020-09-21T18:00:00Z | Coastal-supported | absent / present / present / present | 451.875 | 3.379 | 2.340 | 16.600 | detected |
| 2020-09-22T00:00:00Z | Coastal-supported | absent / present / present / present | 446.500 | 3.547 | 2.085 | 14.109 | detected |
| 2020-09-22T06:00:00Z | Coastal-supported | absent / present / present / present | 443.750 | 3.495 | 1.535 | 12.403 | detected |
| 2020-09-22T12:00:00Z | Coastal-supported | absent / present / present / present | 443.000 | 3.264 | 0.927 | 13.048 | detected |
| 2020-09-22T18:00:00Z | Coastal-supported | absent / present / present / present | 440.750 | 3.200 | 0.885 | 8.753 | detected |
| 2020-09-23T00:00:00Z | Indeterminate | absent / absent / present / absent | 441.500 | 3.083 | 0.295 | 4.907 | detected |
| 2020-09-23T06:00:00Z | Indeterminate | absent / absent / absent / present | 441.500 | 2.966 | -0.420 | 5.173 | detected |
| 2020-09-23T12:00:00Z | Indeterminate | absent / absent / absent / absent | 446.000 | 2.744 | -0.540 | 2.725 | detected |
| 2020-09-23T18:00:00Z | Indeterminate | absent / absent / absent / absent | 456.625 | 2.648 | -0.567 | 2.203 | detected |
| 2020-09-24T00:00:00Z | Indeterminate | absent / absent / absent / absent | 556.500 | 2.380 | -0.925 | 3.702 | not_detected |
| 2020-09-24T06:00:00Z | Indeterminate | absent / absent / absent / absent | 627.375 | 2.388 | -1.165 | -1.236 | not_detected |
| 2020-09-24T12:00:00Z | Indeterminate | absent / absent / absent / absent | 627.375 | 2.374 | -1.102 | -6.210 | not_detected |
| 2020-09-24T18:00:00Z | Indeterminate | absent / absent / absent / absent | 643.000 | 2.173 | -1.008 | -11.330 | not_detected |
| 2020-09-25T00:00:00Z | Indeterminate | absent / absent / absent / absent | 601.125 | 1.832 | -1.223 | -4.158 | not_detected |
| 2020-09-25T06:00:00Z | Indeterminate | absent / absent / absent / absent | 583.500 | 1.744 | -1.395 | -2.557 | not_detected |
| 2020-09-25T12:00:00Z | Indeterminate | absent / absent / absent / absent | 579.500 | 1.543 | -1.423 | -1.683 | not_detected |
| 2020-09-25T18:00:00Z | Indeterminate | absent / absent / absent / absent | 564.250 | 1.531 | -1.165 | 2.076 | not_detected |
| 2020-09-26T00:00:00Z | Indeterminate | absent / absent / absent / absent | 546.750 | 1.487 | -0.825 | 0.199 | not_detected |
| 2020-09-26T06:00:00Z | Indeterminate | absent / absent / absent / absent | 585.125 | 1.395 | -1.155 | 0.295 | not_detected |
| 2020-09-26T12:00:00Z | Indeterminate | absent / absent / absent / absent | 698.125 | 1.307 | -1.178 | 3.756 | not_detected |
| 2020-09-26T18:00:00Z | Indeterminate | absent / absent / absent / absent | 764.375 | 1.357 | -0.903 | 2.711 | not_detected |
| 2020-09-27T00:00:00Z | Indeterminate | absent / absent / absent / absent | 785.125 | 1.357 | -0.327 | 1.008 | not_detected |
| 2020-09-27T06:00:00Z | Indeterminate | absent / absent / absent / absent | 834.250 | 1.261 | -0.583 | 0.451 | not_detected |
| 2020-09-27T12:00:00Z | Indeterminate | absent / absent / absent / absent | 881.625 | 1.166 | -0.590 | -0.187 | not_detected |
| 2020-09-27T18:00:00Z | Indeterminate | absent / absent / absent / absent | 885.625 | 1.119 | -0.413 | -0.434 | not_detected |
| 2020-09-28T00:00:00Z | Indeterminate | absent / absent / absent / absent | 846.125 | 1.139 | -0.240 | 2.469 | not_detected |
| 2020-09-28T06:00:00Z | Indeterminate | absent / absent / absent / absent | 806.125 | 0.960 | -0.515 | 0.739 | not_detected |
| 2020-09-28T12:00:00Z | Indeterminate | absent / absent / absent / absent | 746.125 | 0.934 | -0.595 | -0.094 | not_detected |
| 2020-09-28T18:00:00Z | Indeterminate | absent / absent / absent / absent | 686.375 | 1.034 | -0.363 | -6.082 | not_detected |
| 2020-09-29T00:00:00Z | Indeterminate | absent / absent / absent / absent | 637.500 | 1.135 | -0.138 | -4.740 | not_detected |

## November 2024 coastal-advisory window

Case window: 2024-11-14T00:00:00Z to 2024-11-25T00:00:00Z (end exclusive for observations).

Case context is independent documentary information, not reference labels. Full-event interpretations may extend outside this named case; within-case snapshots are shown separately.

Event candidates are identified from MAUL1 native stage alone; timing associations are evaluated afterward. Unknown onset or missing coverage limits precursor interpretation. External storm context is not ground truth.

Independent documentary context (NCEI event 1224701): NCEI narrative reports Gause Boulevard was impassable due to heavy rainfall.

Independent documentary context (NCEI event 1224686): NCEI narrative reports flooded roads and stalled vehicles in Mandeville.

Independent documentary context (NCEI event 1224687): NCEI narrative reports street flooding in New Orleans.

### maul1-response-0154 — Indeterminate

Onset 2024-10-24T16:00:00Z (known); peak 2024-11-13T15:00:00Z; native rise 2.14 ft; recovery ends 2024-11-21T17:00:00Z. Evidence-sufficient hours: 100.0%. Coexistence: 0 h.

Supporting: lake: persistent observational support; pass_context: persistent observational support; residual: persistent observational support; river: persistent observational support; wind: persistent observational support; wind: persistent observational support (physical observation outside eligible coastal association window).

Contradictory: No qualifying DENL1 discharge level/rise; this does not exclude downstream river inputs; Positive residual lacks lake support in the same six-hour interval; Positive residual lacks wind support in the same six-hour interval.

Missing/unreliable: pass_context: insufficient valid coverage, quality or datum continuity.

Uncertainty: Retrospective supporting evidence is not a causal label, forecast or demonstrated interaction.; Event selection and assessment windows use the full historical response catalogue.; DENL1 absence cannot exclude tributary/local runoff downstream.; Hourly means preserve native datums; same-hour residual pairing may differ from raw coincident residuals.; Long response excursion: later forcing episodes may be unrelated to its original onset.

| Pathway | First support UTC | Last support UTC | First relative to MAUL1 onset (h) | Present / absent / unknown hours |
|---|---|---|---:|---|
| river | 2024-11-02T11:00:00Z | 2024-11-13T16:00:00Z | 211.0 | 28 / 525 / 0 |
| residual | 2024-10-29T13:00:00Z | 2024-11-13T12:00:00Z | 117.0 | 143 / 410 / 0 |
| lake | 2024-10-29T11:00:00Z | 2024-11-13T15:00:00Z | 115.0 | 141 / 412 / 0 |
| wind | 2024-10-21T16:00:00Z | 2024-11-13T03:00:00Z | -72.0 | 96 / 457 / 0 |
| coastal | 2024-11-10T00:00:00Z | 2024-11-11T03:00:00Z | 392.0 | 11 / 488 / 54 |
| pass_context | 2024-10-29T08:00:00Z | 2024-11-13T16:00:00Z | 112.0 | 130 / 379 / 44 |

#### First river witness — 2024-11-02T11:00:00Z

River-supported: river=present; coastal=absent requires residual=absent, independent lake=absent, wind=absent.

```json
{
  "discharge": {
    "antecedent_median_cfs": 328.0,
    "conservative_72h_rise_cfs": 4788.75,
    "conservative_ratio": 15.566539923954373,
    "current_median_cfs": 5545.0,
    "elevated_discharge": true,
    "rise_rate_cfs_per_hour": 66.51041666666667,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": 1.7625,
      "conservative_rise_native_ft": -0.047499999999999876,
      "current_median_ft": 1.765,
      "current_minimum_ft": 1.715
    },
    "MDLL1:stage": {
      "baseline_median_ft": 1.485,
      "conservative_rise_native_ft": -0.07500000000000018,
      "current_median_ft": 1.5375,
      "current_minimum_ft": 1.41
    },
    "NWCL1:residual": {
      "baseline_median_ft": 1.228,
      "conservative_rise_native_ft": -0.011500000000000066,
      "current_median_ft": 1.2502499999999999,
      "current_minimum_ft": 1.2165
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.619,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": 1.8695,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": -0.03249999999999975,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 73.99080022567398,
    "directional_persistence": 0.9510891961529222,
    "projected_minimum_knots": 0.49771699999999996,
    "speed_of_mean_vector_knots": 5.268775338972872,
    "u_mean_knots": -5.064438666666667,
    "v_mean_knots": -1.4530845
  }
}
```

#### First coastal witness — 2024-11-10T00:00:00Z

Coastal-supported: river=absent; coastal=present requires residual=present, independent lake=present, wind=present.

```json
{
  "discharge": {
    "antecedent_median_cfs": 633.5,
    "conservative_72h_rise_cfs": -88.25,
    "conservative_ratio": 0.8640215716486903,
    "current_median_cfs": 563.5,
    "elevated_discharge": false,
    "rise_rate_cfs_per_hour": -1.2256944444444444,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": 1.89,
      "conservative_rise_native_ft": null,
      "current_median_ft": 2.33,
      "current_minimum_ft": 2.315
    },
    "MDLL1:stage": {
      "baseline_median_ft": 1.5925,
      "conservative_rise_native_ft": 0.6475000000000002,
      "current_median_ft": 2.275,
      "current_minimum_ft": 2.24
    },
    "NWCL1:residual": {
      "baseline_median_ft": 1.43925,
      "conservative_rise_native_ft": 0.52525,
      "current_median_ft": 1.9735,
      "current_minimum_ft": 1.9645
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.6637500000000001,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": 2.637,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": 0.4700000000000002,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 82.00289984608798,
    "directional_persistence": 0.998836728227073,
    "projected_minimum_knots": 5.274139,
    "speed_of_mean_vector_knots": 7.47613003260059,
    "u_mean_knots": -7.4034255,
    "v_mean_knots": -1.0401015
  }
}
```

#### First indeterminate witness — 2024-10-21T16:00:00Z

Indeterminate: river=absent; coastal association excluded before the event's coastal antecedent window (physical coastal screen=absent). This exclusion is not missing observations.

```json
{
  "discharge": {
    "antecedent_median_cfs": 334.0,
    "conservative_72h_rise_cfs": -0.5,
    "conservative_ratio": 0.9985052316890882,
    "current_median_cfs": 335.5,
    "elevated_discharge": false,
    "rise_rate_cfs_per_hour": -0.006944444444444444,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": 1.395,
      "conservative_rise_native_ft": -0.13000000000000012,
      "current_median_ft": 1.3625,
      "current_minimum_ft": 1.265
    },
    "MDLL1:stage": {
      "baseline_median_ft": 1.1099999999999999,
      "conservative_rise_native_ft": 0.03500000000000014,
      "current_median_ft": 1.2575,
      "current_minimum_ft": 1.145
    },
    "NWCL1:residual": {
      "baseline_median_ft": 0.88025,
      "conservative_rise_native_ft": -0.11524999999999996,
      "current_median_ft": 0.78125,
      "current_minimum_ft": 0.765
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.8807499999999999,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": 1.66425,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": -0.13750000000000018,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 67.54383295704582,
    "directional_persistence": 0.996404067926251,
    "projected_minimum_knots": 7.300463000000001,
    "speed_of_mean_vector_knots": 10.956439435717874,
    "u_mean_knots": -10.125634833333333,
    "v_mean_knots": -4.185102666666666
  }
}
```
### maul1-response-0155 — River-supported

Onset 2024-11-23T14:00:00Z (known); peak 2024-11-30T19:00:00Z; native rise 1.23 ft; recovery ends None. Evidence-sufficient hours: 100.0%. Coexistence: 0 h.

Supporting: lake: persistent observational support; pass_context: persistent observational support; residual: persistent observational support; river: persistent observational support; wind: persistent observational support.

Contradictory: No qualifying DENL1 discharge level/rise; this does not exclude downstream river inputs; Positive residual lacks lake support in the same six-hour interval; Positive residual lacks wind support in the same six-hour interval.

Missing/unreliable: pass_context: insufficient valid coverage, quality or datum continuity.

Uncertainty: Retrospective supporting evidence is not a causal label, forecast or demonstrated interaction.; Event selection and assessment windows use the full historical response catalogue.; DENL1 absence cannot exclude tributary/local runoff downstream.; Hourly means preserve native datums; same-hour residual pairing may differ from raw coincident residuals.; Long response excursion: later forcing episodes may be unrelated to its original onset.

| Pathway | First support UTC | Last support UTC | First relative to MAUL1 onset (h) | Present / absent / unknown hours |
|---|---|---|---:|---|
| river | 2024-11-20T14:00:00Z | 2024-11-21T23:00:00Z | -72.0 | 34 / 213 / 0 |
| residual | 2024-11-29T17:00:00Z | 2024-11-30T20:00:00Z | 147.0 | 11 / 236 / 0 |
| lake | 2024-11-24T14:00:00Z | 2024-11-30T20:00:00Z | 24.0 | 38 / 209 / 0 |
| wind | 2024-11-23T12:00:00Z | 2024-11-30T17:00:00Z | -2.0 | 38 / 209 / 0 |
| coastal | None | None | None | 0 / 193 / 54 |
| pass_context | 2024-11-25T01:00:00Z | 2024-11-30T20:00:00Z | 35.0 | 25 / 201 / 21 |

#### First river witness — 2024-11-20T14:00:00Z

River-supported: river=present; coastal association excluded before the event's coastal antecedent window (physical coastal screen=absent). This exclusion is not missing observations.

```json
{
  "discharge": {
    "antecedent_median_cfs": 1412.5,
    "conservative_72h_rise_cfs": 3840.0,
    "conservative_ratio": 3.621160409556314,
    "current_median_cfs": 5875.0,
    "elevated_discharge": true,
    "rise_rate_cfs_per_hour": 53.333333333333336,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": 1.85,
      "conservative_rise_native_ft": -0.07500000000000018,
      "current_median_ft": 1.83,
      "current_minimum_ft": 1.775
    },
    "MDLL1:stage": {
      "baseline_median_ft": 1.435,
      "conservative_rise_native_ft": 0.004999999999999893,
      "current_median_ft": 1.6124999999999998,
      "current_minimum_ft": 1.44
    },
    "NWCL1:residual": {
      "baseline_median_ft": 1.3912499999999999,
      "conservative_rise_native_ft": 0.2027500000000002,
      "current_median_ft": 1.6235,
      "current_minimum_ft": 1.594
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.37224999999999997,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": 1.9957500000000001,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": -0.09999999999999964,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 345.1619203895461,
    "directional_persistence": 0.9987962677210132,
    "projected_minimum_knots": -1.9726579999999985,
    "speed_of_mean_vector_knots": 7.258869605862618,
    "u_mean_knots": 1.8589113333333334,
    "v_mean_knots": -7.016811000000001
  }
}
```

#### First indeterminate witness — 2024-11-22T00:00:00Z

Indeterminate: river=absent; coastal association excluded before the event's coastal antecedent window (physical coastal screen=absent). This exclusion is not missing observations.

```json
{
  "discharge": {
    "antecedent_median_cfs": 1010.0,
    "conservative_72h_rise_cfs": 3880.0,
    "conservative_ratio": 4.776155717761557,
    "current_median_cfs": 5185.0,
    "elevated_discharge": false,
    "rise_rate_cfs_per_hour": 53.888888888888886,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": 1.845,
      "conservative_rise_native_ft": -1.0699999999999998,
      "current_median_ft": 0.86,
      "current_minimum_ft": 0.775
    },
    "MDLL1:stage": {
      "baseline_median_ft": 1.545,
      "conservative_rise_native_ft": -1.325,
      "current_median_ft": 0.39,
      "current_minimum_ft": 0.22
    },
    "NWCL1:residual": {
      "baseline_median_ft": 1.6252499999999999,
      "conservative_rise_native_ft": -1.29225,
      "current_median_ft": 0.3845,
      "current_minimum_ft": 0.333
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.46375,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": 0.84175,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": -0.8925000000000001,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 300.61128575479756,
    "directional_persistence": 0.9716931222032528,
    "projected_minimum_knots": -5.487195999999999,
    "speed_of_mean_vector_knots": 4.462113726607956,
    "u_mean_knots": 3.8402813333333334,
    "v_mean_knots": -2.2721571666666667
  }
}
```

### Historical issue-time snapshots

Six-hour fixed UTC clocks. Q is the trailing six-hour median cfs. Δlake is the minimum current MDLL1 stage minus its prior 48-hour median ending 24h earlier, in native feet. Wind is the minimum projection toward 270° in knots. These columns are observations/screens, not forecasts. Full flags, coverage, missing/contradictory evidence and metrics are in `cases.json` and the separate replay dataset.

| UTC decision time | Class | River / residual / lake / wind | Q cfs | Residual ft | Δlake ft | West wind kt | MAUL1 response screen |
|---|---|---|---:|---:|---:|---:|---|
| 2024-11-14T00:00:00Z | Indeterminate | absent / absent / absent / absent | 5171.250 | 1.978 | -0.027 | -0.582 | detected |
| 2024-11-14T06:00:00Z | Indeterminate | absent / absent / absent / absent | 4367.500 | 2.179 | 0.045 | -4.773 | not_detected |
| 2024-11-14T12:00:00Z | Indeterminate | absent / absent / absent / absent | 3318.750 | 2.232 | 0.135 | -4.714 | not_detected |
| 2024-11-14T18:00:00Z | Indeterminate | absent / absent / absent / absent | 2997.500 | 1.992 | -0.355 | -1.647 | not_detected |
| 2024-11-15T00:00:00Z | Indeterminate | absent / absent / absent / absent | 3066.250 | 1.778 | -0.775 | -2.509 | not_detected |
| 2024-11-15T06:00:00Z | Indeterminate | absent / absent / absent / absent | 3138.750 | 1.564 | -0.885 | 2.032 | not_detected |
| 2024-11-15T12:00:00Z | Indeterminate | absent / absent / absent / present | 3111.250 | 1.563 | -0.830 | 9.809 | not_detected |
| 2024-11-15T18:00:00Z | Indeterminate | absent / absent / absent / absent | 3160.000 | 1.498 | -0.825 | 2.797 | not_detected |
| 2024-11-16T00:00:00Z | Indeterminate | absent / absent / absent / absent | 3210.000 | 1.391 | -1.060 | -1.133 | not_detected |
| 2024-11-16T06:00:00Z | Indeterminate | absent / absent / absent / absent | 3021.250 | 1.327 | -0.958 | 4.408 | not_detected |
| 2024-11-16T12:00:00Z | Indeterminate | absent / absent / absent / absent | 2537.500 | 1.367 | -0.662 | 1.939 | not_detected |
| 2024-11-16T18:00:00Z | Indeterminate | absent / absent / absent / present | 2101.250 | 1.460 | -0.280 | 6.483 | not_detected |
| 2024-11-17T00:00:00Z | Indeterminate | absent / absent / absent / absent | 1803.750 | 1.417 | -0.403 | 1.942 | not_detected |
| 2024-11-17T06:00:00Z | Indeterminate | absent / absent / absent / absent | 1605.000 | 1.426 | -0.363 | 0.537 | not_detected |
| 2024-11-17T12:00:00Z | Indeterminate | absent / absent / absent / absent | 1452.500 | 1.465 | 0.050 | 0.307 | not_detected |
| 2024-11-17T18:00:00Z | Indeterminate | absent / absent / absent / absent | 1335.000 | 1.437 | 0.065 | 0.972 | not_detected |
| 2024-11-18T00:00:00Z | Indeterminate | absent / absent / absent / absent | 1236.250 | 1.397 | -0.300 | 1.692 | not_detected |
| 2024-11-18T06:00:00Z | Indeterminate | absent / absent / absent / absent | 1168.750 | 1.328 | -0.423 | 0.442 | not_detected |
| 2024-11-18T12:00:00Z | Indeterminate | absent / absent / absent / absent | 1110.000 | 1.336 | -0.153 | 0.541 | not_detected |
| 2024-11-18T18:00:00Z | Indeterminate | absent / absent / absent / absent | 1058.750 | 1.388 | 0.182 | 1.623 | not_detected |
| 2024-11-19T00:00:00Z | Indeterminate | absent / absent / absent / absent | 1010.000 | 1.394 | -0.212 | 2.129 | not_detected |
| 2024-11-19T06:00:00Z | Indeterminate | absent / absent / absent / absent | 1000.000 | 1.400 | -0.328 | 1.159 | not_detected |
| 2024-11-19T12:00:00Z | Indeterminate | absent / absent / absent / absent | 1020.000 | 1.470 | -0.058 | 0.415 | not_detected |
| 2024-11-19T18:00:00Z | Indeterminate | absent / present / present / absent | 1391.250 | 1.957 | 0.663 | -2.984 | not_detected |
| 2024-11-20T00:00:00Z | Indeterminate | absent / present / absent / absent | 3056.250 | 1.850 | 0.225 | -4.727 | not_detected |
| 2024-11-20T06:00:00Z | Indeterminate | absent / present / absent / absent | 4275.000 | 1.833 | -0.145 | -4.895 | not_detected |
| 2024-11-20T12:00:00Z | Indeterminate | absent / absent / absent / absent | 5422.500 | 1.629 | -0.070 | -1.973 | not_detected |
| 2024-11-20T18:00:00Z | River-supported | present / absent / absent / absent | 6617.500 | 1.597 | 0.030 | -3.599 | not_detected |
| 2024-11-21T00:00:00Z | River-supported | present / absent / absent / absent | 6870.000 | 1.479 | -0.505 | -3.396 | not_detected |
| 2024-11-21T06:00:00Z | River-supported | present / absent / absent / absent | 6723.750 | 1.329 | -0.863 | -1.422 | not_detected |
| 2024-11-21T12:00:00Z | River-supported | present / absent / absent / absent | 6285.000 | 1.038 | -1.030 | -1.647 | not_detected |
| 2024-11-21T18:00:00Z | River-supported | present / absent / absent / absent | 5757.500 | 0.681 | -1.010 | -1.733 | not_detected |
| 2024-11-22T00:00:00Z | Indeterminate | absent / absent / absent / absent | 5185.000 | 0.385 | -1.325 | -5.487 | not_detected |
| 2024-11-22T06:00:00Z | Indeterminate | absent / absent / absent / absent | 4462.500 | 0.285 | -1.660 | -8.018 | not_detected |
| 2024-11-22T12:00:00Z | Indeterminate | absent / absent / absent / absent | 3640.000 | 0.035 | -1.828 | -7.162 | not_detected |
| 2024-11-22T18:00:00Z | Indeterminate | absent / absent / absent / absent | 2902.500 | -0.439 | -1.823 | -1.562 | not_detected |
| 2024-11-23T00:00:00Z | Indeterminate | absent / absent / absent / absent | 2367.500 | -0.568 | -1.595 | -3.677 | not_detected |
| 2024-11-23T06:00:00Z | Indeterminate | absent / absent / absent / absent | 2012.500 | -0.462 | -1.535 | -3.400 | not_detected |
| 2024-11-23T12:00:00Z | Indeterminate | absent / absent / absent / present | 1768.750 | -0.412 | -1.377 | 5.732 | not_detected |
| 2024-11-23T18:00:00Z | Indeterminate | absent / absent / absent / absent | 1597.500 | -0.340 | -0.985 | 0.095 | not_detected |
| 2024-11-24T00:00:00Z | Indeterminate | absent / absent / absent / absent | 1463.750 | -0.162 | -0.302 | 1.572 | not_detected |
| 2024-11-24T06:00:00Z | Indeterminate | absent / absent / absent / absent | 1361.250 | -0.197 | -0.182 | 0.363 | not_detected |
| 2024-11-24T12:00:00Z | Indeterminate | absent / absent / absent / absent | 1275.000 | -0.095 | 0.135 | 0.100 | not_detected |
| 2024-11-24T18:00:00Z | Indeterminate | absent / absent / present / absent | 1207.500 | -0.051 | 0.355 | -1.194 | not_detected |
| 2024-11-25T00:00:00Z | Indeterminate | absent / absent / present / absent | 1138.750 | -0.051 | 0.345 | -3.000 | detected |

## April 2025 southeast-wind window

Case window: 2025-04-01T00:00:00Z to 2025-04-12T00:00:00Z (end exclusive for observations).

Case context is independent documentary information, not reference labels. Full-event interpretations may extend outside this named case; within-case snapshots are shown separately.

Event candidates are identified from MAUL1 native stage alone; timing associations are evaluated afterward. Unknown onset or missing coverage limits precursor interpretation. External storm context is not ground truth.

No corresponding local NCEI row in the inherited documentary review. This does not establish absence of a hazard.

### maul1-response-0167 — River-supported

Onset 2025-03-21T06:00:00Z (known); peak 2025-04-05T13:00:00Z; native rise 3.065 ft; recovery ends 2025-04-09T12:00:00Z. Evidence-sufficient hours: 100.0%. Coexistence: 0 h.

Supporting: lake: persistent observational support; lake: persistent observational support (physical observation outside eligible coastal association window); residual: persistent observational support; river: persistent observational support.

Contradictory: No qualifying DENL1 discharge level/rise; this does not exclude downstream river inputs; Positive residual lacks lake support in the same six-hour interval; Positive residual lacks wind support in the same six-hour interval.

Missing/unreliable: pass_context: insufficient valid coverage, quality or datum continuity.

Uncertainty: Retrospective supporting evidence is not a causal label, forecast or demonstrated interaction.; Event selection and assessment windows use the full historical response catalogue.; DENL1 absence cannot exclude tributary/local runoff downstream.; Hourly means preserve native datums; same-hour residual pairing may differ from raw coincident residuals.; Long response excursion: later forcing episodes may be unrelated to its original onset.

| Pathway | First support UTC | Last support UTC | First relative to MAUL1 onset (h) | Present / absent / unknown hours |
|---|---|---|---:|---|
| river | 2025-04-01T08:00:00Z | 2025-04-02T20:00:00Z | 266.0 | 37 / 404 / 0 |
| residual | 2025-03-29T02:00:00Z | 2025-04-05T05:00:00Z | 188.0 | 83 / 358 / 0 |
| lake | 2025-03-20T04:00:00Z | 2025-04-05T13:00:00Z | -26.0 | 164 / 277 / 0 |
| wind | None | None | None | 0 / 441 / 0 |
| coastal | None | None | None | 0 / 387 / 54 |
| pass_context | None | None | None | 0 / 0 / 441 |

#### First river witness — 2025-04-01T08:00:00Z

River-supported: river=present; coastal=absent requires residual=absent, independent lake=absent, wind=absent.

```json
{
  "discharge": {
    "antecedent_median_cfs": 1575.0,
    "conservative_72h_rise_cfs": 3450.0,
    "conservative_ratio": 3.132921174652241,
    "current_median_cfs": 5386.25,
    "elevated_discharge": true,
    "rise_rate_cfs_per_hour": 47.916666666666664,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": null,
      "conservative_rise_native_ft": null,
      "current_median_ft": null,
      "current_minimum_ft": null
    },
    "MDLL1:stage": {
      "baseline_median_ft": 1.105,
      "conservative_rise_native_ft": -0.655,
      "current_median_ft": 0.6675,
      "current_minimum_ft": 0.45
    },
    "NWCL1:residual": {
      "baseline_median_ft": 1.19675,
      "conservative_rise_native_ft": -0.67825,
      "current_median_ft": 0.56975,
      "current_minimum_ft": 0.5185
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.38925,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": 0.93425,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": -0.3050000000000006,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 130.61826355413518,
    "directional_persistence": 0.8334445553661953,
    "projected_minimum_knots": 0.6032409999999998,
    "speed_of_mean_vector_knots": 1.6578214980632129,
    "u_mean_knots": -1.2583923333333333,
    "v_mean_knots": 1.0792686666666667
  }
}
```

#### First indeterminate witness — 2025-03-18T06:00:00Z

Indeterminate: river=absent; coastal association excluded before the event's coastal antecedent window (physical coastal screen=absent). This exclusion is not missing observations.

```json
{
  "discharge": {
    "antecedent_median_cfs": 1086.25,
    "conservative_72h_rise_cfs": 2417.5,
    "conservative_ratio": 3.202733485193622,
    "current_median_cfs": 3880.0,
    "elevated_discharge": false,
    "rise_rate_cfs_per_hour": 33.576388888888886,
    "rising_discharge": false
  },
  "lake_changes": {
    "MCHL1:stage": {
      "baseline_median_ft": null,
      "conservative_rise_native_ft": null,
      "current_median_ft": null,
      "current_minimum_ft": null
    },
    "MDLL1:stage": {
      "baseline_median_ft": 0.73,
      "conservative_rise_native_ft": -1.19,
      "current_median_ft": -0.3325,
      "current_minimum_ft": -0.46
    },
    "NWCL1:residual": {
      "baseline_median_ft": 0.76725,
      "conservative_rise_native_ft": -1.1997499999999999,
      "current_median_ft": -0.40225,
      "current_minimum_ft": -0.4325
    }
  },
  "observed_water_and_prediction": {
    "NWCL1:prediction": {
      "current_median_ft": 0.2865,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    },
    "NWCL1:water": {
      "current_median_ft": -0.109,
      "current_valid_fraction": 1.0,
      "datum": [
        "MLLW"
      ]
    }
  },
  "target_change_native_ft": -1.1425,
  "wind": {
    "axis_toward_degrees": 270.0,
    "direction_from_degrees": 201.38257670082393,
    "directional_persistence": 0.9885186891135028,
    "projected_minimum_knots": -2.792346000000001,
    "speed_of_mean_vector_knots": 5.030954018150735,
    "u_mean_knots": 1.8342538333333334,
    "v_mean_knots": 4.684657
  }
}
```

### Historical issue-time snapshots

Six-hour fixed UTC clocks. Q is the trailing six-hour median cfs. Δlake is the minimum current MDLL1 stage minus its prior 48-hour median ending 24h earlier, in native feet. Wind is the minimum projection toward 270° in knots. These columns are observations/screens, not forecasts. Full flags, coverage, missing/contradictory evidence and metrics are in `cases.json` and the separate replay dataset.

| UTC decision time | Class | River / residual / lake / wind | Q cfs | Residual ft | Δlake ft | West wind kt | MAUL1 response screen |
|---|---|---|---:|---:|---:|---:|---|
| 2025-04-01T00:00:00Z | Indeterminate | absent / absent / absent / absent | 4481.250 | 0.844 | -0.300 | -4.942 | not_detected |
| 2025-04-01T06:00:00Z | Indeterminate | absent / absent / absent / absent | 5128.750 | 0.570 | -0.460 | 0.920 | not_detected |
| 2025-04-01T12:00:00Z | River-supported | present / absent / absent / absent | 5976.250 | 0.632 | -0.792 | 0.603 | not_detected |
| 2025-04-01T18:00:00Z | River-supported | present / absent / absent / absent | 6831.250 | 0.587 | -0.848 | 2.590 | not_detected |
| 2025-04-02T00:00:00Z | River-supported | present / absent / absent / absent | 7115.000 | 0.719 | -0.570 | 1.638 | not_detected |
| 2025-04-02T06:00:00Z | River-supported | present / absent / absent / absent | 6932.500 | 0.803 | 0.030 | 0.926 | not_detected |
| 2025-04-02T12:00:00Z | River-supported | present / absent / absent / absent | 6511.250 | 0.858 | -0.097 | 1.019 | not_detected |
| 2025-04-02T18:00:00Z | River-supported | present / absent / absent / absent | 5791.250 | 0.691 | -0.118 | 0.125 | not_detected |
| 2025-04-03T00:00:00Z | Indeterminate | absent / absent / absent / absent | 4860.000 | 0.786 | 0.245 | -0.682 | not_detected |
| 2025-04-03T06:00:00Z | Indeterminate | absent / absent / present / absent | 3948.750 | 0.942 | 0.540 | 1.040 | detected |
| 2025-04-03T12:00:00Z | Indeterminate | absent / present / present / absent | 3292.500 | 1.130 | 0.393 | 1.175 | detected |
| 2025-04-03T18:00:00Z | Indeterminate | absent / present / absent / absent | 2838.750 | 1.064 | 0.175 | -0.061 | detected |
| 2025-04-04T00:00:00Z | Indeterminate | absent / present / present / absent | 2482.500 | 1.115 | 0.280 | -1.143 | detected |
| 2025-04-04T06:00:00Z | Indeterminate | absent / present / present / absent | 2225.000 | 1.198 | 0.525 | 1.110 | not_detected |
| 2025-04-04T12:00:00Z | Indeterminate | absent / present / absent / absent | 2027.500 | 1.135 | 0.218 | 2.438 | detected |
| 2025-04-04T18:00:00Z | Indeterminate | absent / present / absent / absent | 1872.500 | 1.122 | -0.060 | 2.726 | detected |
| 2025-04-05T00:00:00Z | Indeterminate | absent / absent / absent / absent | 1740.000 | 1.198 | -0.050 | 2.657 | not_detected |
| 2025-04-05T06:00:00Z | Indeterminate | absent / absent / absent / absent | 1641.250 | 1.254 | 0.225 | 2.892 | not_detected |
| 2025-04-05T12:00:00Z | Indeterminate | absent / absent / present / absent | 1556.250 | 1.347 | 0.300 | 2.321 | detected |
| 2025-04-05T18:00:00Z | Indeterminate | absent / absent / absent / absent | 1477.500 | 1.245 | 0.055 | 0.407 | detected |
| 2025-04-06T00:00:00Z | Indeterminate | absent / absent / absent / absent | 1401.250 | 1.129 | 0.093 | -1.548 | not_detected |
| 2025-04-06T06:00:00Z | Indeterminate | absent / absent / present / absent | 1355.000 | 1.226 | 0.288 | -2.337 | not_detected |
| 2025-04-06T12:00:00Z | Indeterminate | absent / absent / present / absent | 1311.250 | 1.315 | 0.302 | -4.673 | not_detected |
| 2025-04-06T18:00:00Z | Indeterminate | absent / absent / absent / absent | 1586.250 | 1.500 | -0.048 | -4.188 | not_detected |
| 2025-04-07T00:00:00Z | Indeterminate | absent / absent / absent / absent | 3435.000 | 1.390 | -0.355 | -3.894 | not_detected |
| 2025-04-07T06:00:00Z | Indeterminate | absent / absent / absent / absent | 3897.500 | 1.203 | -0.460 | -3.654 | not_detected |
| 2025-04-07T12:00:00Z | Indeterminate | absent / absent / absent / absent | 4677.500 | 0.884 | -0.770 | -4.094 | not_detected |
| 2025-04-07T18:00:00Z | River-supported | present / absent / absent / absent | 5586.250 | 0.679 | -1.107 | -4.385 | not_detected |
| 2025-04-08T00:00:00Z | River-supported | present / absent / absent / absent | 6313.750 | 0.541 | -1.397 | -4.131 | not_detected |
| 2025-04-08T06:00:00Z | River-supported | present / absent / absent / absent | 6892.500 | 0.201 | -1.387 | -2.415 | not_detected |
| 2025-04-08T12:00:00Z | River-supported | present / absent / absent / absent | 7416.250 | 0.044 | -1.295 | -0.573 | not_detected |
| 2025-04-08T18:00:00Z | River-supported | present / absent / absent / absent | 7800.000 | -0.035 | -1.375 | -0.396 | not_detected |
| 2025-04-09T00:00:00Z | River-supported | present / absent / absent / absent | 7898.750 | -0.062 | -1.212 | -6.068 | not_detected |
| 2025-04-09T06:00:00Z | River-supported | present / absent / absent / absent | 7838.750 | 0.036 | -1.002 | -5.059 | not_detected |
| 2025-04-09T12:00:00Z | River-supported | present / absent / absent / absent | 7565.000 | -0.080 | -0.772 | 1.939 | not_detected |
| 2025-04-09T18:00:00Z | River-supported | present / absent / absent / absent | 7111.250 | -0.160 | -0.438 | 0.015 | not_detected |
| 2025-04-10T00:00:00Z | River-supported | present / absent / absent / absent | 6475.000 | -0.059 | -0.237 | -0.953 | not_detected |
| 2025-04-10T06:00:00Z | River-supported | present / absent / absent / absent | 5663.750 | -0.163 | -0.337 | -3.871 | not_detected |
| 2025-04-10T12:00:00Z | Indeterminate | absent / absent / absent / absent | 4708.750 | -0.369 | -0.393 | -2.532 | not_detected |
| 2025-04-10T18:00:00Z | Indeterminate | absent / absent / absent / absent | 3716.250 | -0.515 | -0.507 | -3.599 | not_detected |
| 2025-04-11T00:00:00Z | Indeterminate | absent / absent / absent / absent | 2961.250 | -0.623 | -0.562 | -0.025 | not_detected |
| 2025-04-11T06:00:00Z | Indeterminate | absent / absent / absent / absent | 2505.000 | -0.645 | -0.560 | -6.513 | not_detected |
| 2025-04-11T12:00:00Z | Indeterminate | absent / absent / absent / absent | 2225.000 | -0.725 | -0.795 | -8.711 | not_detected |
| 2025-04-11T18:00:00Z | Indeterminate | absent / absent / absent / absent | 2036.250 | -0.911 | -0.988 | -5.009 | not_detected |
| 2025-04-12T00:00:00Z | Indeterminate | absent / absent / absent / absent | 1888.750 | -1.007 | -0.970 | -2.747 | not_detected |

