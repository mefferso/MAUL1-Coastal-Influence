"""Rebuild fixed event-level wind and hydrologic response diagnostics."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import pathlib
import statistics
import sys

PACKAGE = pathlib.Path(__file__).resolve().parent
REPO = PACKAGE.parents[1]
sys.path.insert(0, str(PACKAGE))

from archive_adapter import combine_wind_records, load_hourly_records, phase_coverage
from feature_engine import build_response_features, build_wind_features

UTC = dt.timezone.utc
HOUR = dt.timedelta(hours=1)
LAGS_HOURS = (0, 6, 12, 24, 36, 48, 72)
WINDOWS_HOURS = (3, 6, 12, 24, 48, 72)
MIN_COVERAGE = 0.8


def _time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _finite_values(rows, key):
    return [float(row[key]) for row in rows if isinstance(row.get(key), (int, float)) and math.isfinite(row[key])]


def _median(rows, key):
    values = _finite_values(rows, key)
    return statistics.median(values) if values else None


def _min_max(rows, key):
    values = _finite_values(rows, key)
    return {"minimum": min(values), "maximum": max(values)} if values else {"minimum": None, "maximum": None}


def _phase_rows(rows, start, end):
    a, b = _time(start), _time(end)
    return [row for row in rows if a <= _time(row["time"]) < b]


def _usable_series(records, station, variable, start, end):
    rows = [row for row in records if row.get("station") == station and row.get("variable") == variable
            and row.get("valid") and _time(start) <= _time(row["time"]) < _time(end)]
    rows.sort(key=lambda row: row["time"])
    return rows


def _peak_time(rows, key):
    candidates = [row for row in rows if isinstance(row.get(key), (int, float)) and math.isfinite(row[key])]
    if not candidates:
        return {"time_utc": None, "value": None}
    peak = max(candidates, key=lambda row: row[key])
    return {"time_utc": peak["time"], "value": peak[key]}


def _stage_peak(records, station, variable, start, end):
    rows = _usable_series(records, station, variable, start, end)
    if not rows:
        return {"time_utc": None, "value": None, "unit": None, "datum": None}
    peak = max(rows, key=lambda row: row["value"])
    return {"time_utc": peak["time"], "value": peak["value"], "unit": peak.get("unit"), "datum": peak.get("datum")}


def _hours_between(later, earlier):
    if not later or not earlier:
        return None
    return (_time(later) - _time(earlier)).total_seconds() / 3600


def _observed_peak_timing(case, records, response):
    catalog = case.get("response_catalog") or {}
    start = catalog.get("onset_utc") or case["phases"][0]["start_utc"]
    end = catalog.get("recovery_end_utc") or case["phases"][-1]["end_utc"]
    response_rows = _phase_rows(response, start, end)
    nwcl = _peak_time(response_rows, "nwcl1_residual_mllw_ft")
    mdll = _stage_peak(records, "MDLL1", "stage", start, end)
    maul = _stage_peak(records, "MAUL1", "stage", start, end)
    den = _stage_peak(records, "DENL1", "discharge", start, end)
    return {"window_start_utc": start, "window_end_utc_exclusive": end,
            "window_basis": "Phase 3B MAUL1 response catalog onset through recovery (outcome-defined retrospective interval); control uses its fixed control window",
            "nwcl1_max_same_station_residual": nwcl,
            "mdll1_max_native_stage": mdll, "maul1_max_native_00065_stage": maul,
            "denl1_max_discharge": den,
            "observed_peak_time_offsets_hours": {
                "mdll1_peak_minus_nwcl1_residual_peak": _hours_between(mdll["time_utc"], nwcl["time_utc"]),
                "maul1_peak_minus_mdll1_peak": _hours_between(maul["time_utc"], mdll["time_utc"]),
                "maul1_peak_minus_denl1_discharge_peak": _hours_between(maul["time_utc"], den["time_utc"]),
            },
            "interpretation": "Differences between observed maxima are descriptive timing offsets only; they do not estimate physical propagation or usable forecast lead. Absolute levels remain station-specific."}


def _stage_change(rows, station, variable, label, expected_hours):
    selected = sorted([row for row in rows if row.get("station") == station and row.get("variable") == variable and row.get("valid")], key=lambda row: row["time"])
    if not selected:
        return {"valid_hours": 0, "expected_hours": expected_hours, "coverage_fraction": 0.0,
                "first_time_utc": None, "last_time_utc": None,
                "first_value": None, "last_value": None, "change": None, "unit": None, "datum": None,
                "reference": label}
    first, last = selected[0], selected[-1]
    compatible = all(row.get("unit") == first.get("unit") and row.get("datum") == first.get("datum") for row in selected)
    return {"valid_hours": len(selected), "first_time_utc": first["time"], "last_time_utc": last["time"],
            "first_value": first["value"], "last_value": last["value"],
            "change": float(last["value"]) - float(first["value"])
            if compatible and len(selected) / expected_hours >= MIN_COVERAGE else None,
            "expected_hours": expected_hours,
            "coverage_fraction": len(selected) / expected_hours if expected_hours else None,
            "unit": first.get("unit") if compatible else None, "datum": first.get("datum") if compatible else None,
            "reference": label}


def _phase_summary(phase, records, wind_features, response_features):
    start, end = phase["start_utc"], phase["end_utc"]
    expected = int((_time(end) - _time(start)).total_seconds() / 3600)
    raw_wind = _phase_rows(wind_features, start, end)
    good = [row for row in raw_wind if row.get("nwcl1_wind_valid")]
    valid_fraction = len(good) / expected if expected else None
    speeds = _finite_values(good, "wind_speed_knots")
    dirs = [row["wind_direction_from_deg"] for row in good if row.get("wind_direction_from_deg") is not None]
    mean_u = statistics.fmean(row["wind_u_east_knots"] for row in good) if good else None
    mean_v = statistics.fmean(row["wind_v_north_knots"] for row in good) if good else None
    mean_dir = math.degrees(math.atan2(-mean_u, -mean_v)) % 360 if good and (mean_u or mean_v) else None
    phase_response = _phase_rows(response_features, start, end)
    residuals = _finite_values(phase_response, "nwcl1_residual_mllw_ft")
    mdll_anoms = _finite_values(phase_response, "mdll1_stage_anomaly_72h_native_ft")
    phase_records = [row for row in records if start <= row["time"] < end]
    wind_values = [row for row in phase_records if row.get("station") == "NWCL1" and row.get("variable") == "wind" and row.get("valid")]
    easterly = {"5kt": 0, "10kt": 0, "15kt": 0}
    southeasterly = {"5kt": 0, "10kt": 0, "15kt": 0}
    longest_easterly = {"5kt": 0, "10kt": 0, "15kt": 0}
    longest_southeasterly = {"5kt": 0, "10kt": 0, "15kt": 0}
    for row in good:
        direction, speed = row["wind_direction_from_deg"], row["wind_speed_knots"]
        in_e = 67.5 <= direction < 112.5
        in_se = 112.5 <= direction < 157.5
        for cutoff in (5, 10, 15):
            if in_e and speed >= cutoff:
                easterly[f"{cutoff}kt"] += 1
            if in_se and speed >= cutoff:
                southeasterly[f"{cutoff}kt"] += 1
    for sector, target in (("e", longest_easterly), ("se", longest_southeasterly)):
        for cutoff in (5, 10, 15):
            run = longest = 0
            for item in raw_wind:
                qualifies = bool(item.get("nwcl1_wind_valid") and item["wind_speed_knots"] >= cutoff
                                 and ((67.5 <= item["wind_direction_from_deg"] < 112.5) if sector == "e"
                                      else (112.5 <= item["wind_direction_from_deg"] < 157.5)))
                run = run + 1 if qualifies else 0
                longest = max(longest, run)
            target[f"{cutoff}kt"] = longest if valid_fraction is not None and valid_fraction >= MIN_COVERAGE else None
    summaries = {}
    for window in WINDOWS_HOURS:
        rows = [item for item in raw_wind if item.get(f"integrated_stress_u_proxy_{window}h_kt2h") is not None]
        summaries[f"{window}h"] = {
            "valid_rolling_windows": len(rows),
            "eastward_component_integral_proxy_kt2h": _min_max(rows, f"integrated_stress_u_proxy_{window}h_kt2h"),
            "northward_component_integral_proxy_kt2h": _min_max(rows, f"integrated_stress_v_proxy_{window}h_kt2h"),
            "directional_persistence_median": _median(rows, f"directional_persistence_{window}h"),
        }
    speed_stress_u = [row["stress_u_proxy_kt2"] for row in good if row.get("stress_u_proxy_kt2") is not None]
    speed_stress_v = [row["stress_v_proxy_kt2"] for row in good if row.get("stress_v_proxy_kt2") is not None]
    return {
        "phase": phase,
        "expected_hourly_bins": expected,
        "nwcl1_wind": {
            "valid_hourly_bins": len(good), "coverage_fraction": valid_fraction,
            "hourly_scalar_mean_speed_knots": statistics.fmean(speeds) if speeds else None,
            "hourly_scalar_max_speed_knots": max(speeds) if speeds else None,
            "mean_meteorological_direction_from_deg": mean_dir,
            "mean_direction_components_east_north_knots": {"east": mean_u, "north": mean_v},
            "easterly_duration_hours_ge_threshold_knots": easterly,
            "southeasterly_duration_hours_ge_threshold_knots": southeasterly,
            "longest_contiguous_easterly_run_hours_ge_threshold_knots": longest_easterly,
            "longest_contiguous_southeasterly_run_hours_ge_threshold_knots": longest_southeasterly,
            "sum_of_hourly_directional_stress_proxies_kt2h": {
                "east": sum(speed_stress_u) if valid_fraction is not None and valid_fraction >= MIN_COVERAGE else None,
                "north": sum(speed_stress_v) if valid_fraction is not None and valid_fraction >= MIN_COVERAGE else None,
            },
            "rolling_cumulative_forcing": summaries,
            "directional_persistence_6h_median": _median(good, "directional_persistence_6h"),
            "directional_persistence_24h_median": _median(good, "directional_persistence_24h"),
            "hourly_direction_reversals": sum(row.get("direction_reversal_1h") is True for row in good),
            "hourly_relaxations_at_least_2_knots": sum((row.get("wind_relaxation_knots_1h") or 0) >= 2 for row in good),
            "sensor_exposure": "NWCL1 / NOAA CO-OPS New Canal shoreline site; not open-water lake-wide wind.",
        },
        "within_station_peak_timing": {
            "nwcl1_max_residual": _peak_time(phase_response, "nwcl1_residual_mllw_ft"),
            "mdll1_max_72h_own_baseline_anomaly": _peak_time(phase_response, "mdll1_stage_anomaly_72h_native_ft"),
            "maul1_max_24h_native_stage_change": _peak_time(phase_response, "maul1_stage_change_24h_native_ft"),
        },
        "same_station_water_and_river": {
            "archive_source_coverage": phase_coverage(records, start, end),
            "nwcl1_residual_mllw_ft": {"valid_hours": len(residuals), "median": statistics.median(residuals) if residuals else None,
                                         "minimum": min(residuals) if residuals else None, "maximum": max(residuals) if residuals else None},
            "mdll1_stage_anomaly_relative_to_preceding_72h_native_ft": {"valid_hours": len(mdll_anoms),
                                                                           "median": statistics.median(mdll_anoms) if mdll_anoms else None,
                                                                           "minimum": min(mdll_anoms) if mdll_anoms else None,
                                                                           "maximum": max(mdll_anoms) if mdll_anoms else None},
            "mdll1_stage_change_native": _stage_change(phase_records, "MDLL1", "stage", "within-station native gage height", expected),
            "maul1_stage_change_native_00065": _stage_change(phase_records, "MAUL1", "stage", "within-station USGS 00065 native gage height", expected),
            "denl1_discharge_change": _stage_change(phase_records, "DENL1", "discharge", "within-station discharge; not rainfall", expected),
            "direct_rainfall_observation_available": False,
            "cross_station_absolute_level_difference_computed": False,
        },
    }


def _pearson(left, right):
    if len(left) < 6 or len(left) != len(right):
        return None
    mean_left, mean_right = statistics.fmean(left), statistics.fmean(right)
    dx, dy = [x - mean_left for x in left], [y - mean_right for y in right]
    denominator = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    return sum(x * y for x, y in zip(dx, dy)) / denominator if denominator else None


def _catalog_response(case, records):
    catalog = case.get("response_catalog") or {}
    if not catalog.get("trough_utc") or not catalog.get("peak_utc"):
        return None
    trough = _usable_series(records, "MAUL1", "stage", catalog["trough_utc"], (_time(catalog["trough_utc"]) + HOUR).isoformat())
    peak = _usable_series(records, "MAUL1", "stage", catalog["peak_utc"], (_time(catalog["peak_utc"]) + HOUR).isoformat())
    paired = bool(trough and peak and trough[0].get("unit") == peak[0].get("unit")
                  and trough[0].get("datum") == peak[0].get("datum"))
    return {"catalog_event_id": catalog.get("event_id"), "catalog_onset_utc": catalog.get("onset_utc"),
            "catalog_peak_utc": catalog.get("peak_utc"), "catalog_recovery_end_utc": catalog.get("recovery_end_utc"),
            "catalog_onset_known": catalog.get("onset_known"), "catalog_status": catalog.get("status"),
            "observed_trough_native_gage_height_ft": trough[0]["value"] if paired else None,
            "observed_peak_native_gage_height_ft": peak[0]["value"] if paired else None,
            "paired_trough_to_peak_native_stage_change_ft": float(peak[0]["value"]) - float(trough[0]["value"]) if paired else None,
            "catalog_reported_rise_native_gage_height_ft": catalog.get("rise_native_gage_height_ft"),
            "comparison_basis": "within-station MAUL1 USGS parameter 00065; exact catalog trough/peak bins, matching unit/datum; not NAVD88"}


def _lag_profiles(case, wind_features, response_features):
    wind = {_time(row["time"]): row for row in wind_features}
    response = {_time(row["time"]): row for row in response_features}
    profiles = []
    targets = {
        "nwcl1_residual_change_6h_ft": "NWCL1 same-station residual change, MLLW",
        "mdll1_stage_change_6h_ft": "MDLL1 same-station native stage change",
        "maul1_stage_change_6h_native_ft": "MAUL1 00065 same-station native stage change",
        "denl1_discharge_change_6h_cfs": "DENL1 same-station discharge change; rainfall proxy limitation",
    }
    phase_by_id = {phase["id"]: phase for phase in case.get("phases", [])}
    for phase_id in case.get("lag_source_phase_ids", []):
        phase = phase_by_id[phase_id]
        begin, finish = _time(phase["start_utc"]), _time(phase["end_utc"])
        phase_record = {"source_phase_id": phase_id, "role": phase["role"],
                        "attribution": phase["attribution"],
                        "definition": "Trailing 24h integrated NWCL1 directional stress proxy at t paired with same-station change over the 6h interval starting at t + lag; samples anchored every 6h.",
                        "lag_hours": []}
        for lag in LAGS_HOURS:
            component_pairs = {"eastward_integral_proxy": [], "northward_integral_proxy": []}
            target_pairs = {target: {component: ([], []) for component in component_pairs} for target in targets}
            stamp = begin
            # Only forcing hours inside the predeclared source phase can be x values.
            # Future response bins may extend beyond phase end up to the stated lag.
            while stamp < finish:
                wrow = wind.get(stamp)
                trow = response.get(stamp + dt.timedelta(hours=lag + 6))
                if wrow and trow:
                    for component, key in (("eastward_integral_proxy", "integrated_stress_u_proxy_24h_kt2h"),
                                           ("northward_integral_proxy", "integrated_stress_v_proxy_24h_kt2h")):
                        forcing = wrow.get(key)
                        if isinstance(forcing, (int, float)):
                            component_pairs[component].append(forcing)
                            for target in targets:
                                outcome = trow.get(target)
                                if isinstance(outcome, (int, float)):
                                    target_pairs[target][component][0].append(forcing)
                                    target_pairs[target][component][1].append(outcome)
                stamp += dt.timedelta(hours=6)
            row = {"lag_hours": lag, "targets": {}}
            for target, description in targets.items():
                row["targets"][target] = {"description": description, "eastward": {}, "northward": {}}
                for component, axis in (("eastward_integral_proxy", "eastward"), ("northward_integral_proxy", "northward")):
                    xvalues, yvalues = target_pairs[target][component]
                    row["targets"][target][axis] = {"paired_6h_blocks": len(xvalues),
                                                      "pearson_r_descriptive": _pearson(xvalues, yvalues)}
            phase_record["lag_hours"].append(row)
        profiles.append(phase_record)
    return profiles


def _make_plot(case, wind_features, response_features, path):
    import os
    import tempfile
    os.environ.setdefault("MPLCONFIGDIR", str(pathlib.Path(tempfile.gettempdir()) / "maul1-mpl-cache"))
    os.environ.setdefault("XDG_CACHE_HOME", str(pathlib.Path(tempfile.gettempdir()) / "maul1-xdg-cache"))
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["svg.hashsalt"] = "maul1-coastal-response-diagnostics-v1"
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    begin = _time(case["phases"][0]["start_utc"])
    finish = _time(case["phases"][-1]["end_utc"])
    winds = [row for row in wind_features if begin <= _time(row["time"]) < finish]
    responses = [row for row in response_features if begin <= _time(row["time"]) < finish]
    xwind = [_time(row["time"]) for row in winds]
    xresp = [_time(row["time"]) for row in responses]
    nan = float("nan")
    fig, axes = plt.subplots(4, 1, figsize=(14, 11), sharex=True, constrained_layout=True)
    fig.suptitle(f"{case['label']} — NWCL1 shoreline forcing and within-station responses", fontsize=14)

    axes[0].plot(xwind, [row.get("wind_speed_knots") if row.get("wind_speed_knots") is not None else nan for row in winds], color="#1f77b4", lw=1.1, label="NWCL1 hourly mean speed (knots)")
    axes[0].set_ylabel("Wind speed\n(knots)")
    axes[0].grid(alpha=.25)
    direction = axes[0].twinx()
    direction.plot(xwind, [row.get("wind_direction_from_deg") if row.get("wind_direction_from_deg") is not None else nan for row in winds], color="#8c564b", alpha=.48, lw=.8, label="Meteorological direction from (°)")
    direction.set_ylim(0, 360)
    direction.set_yticks([0, 90, 180, 270, 360], ["N", "E", "S", "W", "N"])
    direction.set_ylabel("Direction from")
    lines, labels = axes[0].get_legend_handles_labels()
    lines2, labels2 = direction.get_legend_handles_labels()
    axes[0].legend(lines + lines2, labels + labels2, loc="upper left", fontsize=8, ncol=2)

    for window, style in ((24, "-"), (72, "--")):
        east_key, north_key = f"integrated_stress_u_proxy_{window}h_kt2h", f"integrated_stress_v_proxy_{window}h_kt2h"
        axes[1].plot(xwind, [row.get(east_key) if row.get(east_key) is not None else nan for row in winds], linestyle=style, color="#2ca02c", lw=1.0, label=f"Eastward component, trailing {window}h")
        axes[1].plot(xwind, [row.get(north_key) if row.get(north_key) is not None else nan for row in winds], linestyle=style, color="#d62728", lw=1.0, label=f"Northward component, trailing {window}h")
    axes[1].axhline(0, color="black", lw=.6)
    axes[1].set_ylabel("Directional proxy\n(kt²·h)")
    axes[1].legend(loc="upper left", fontsize=8, ncol=2)
    axes[1].grid(alpha=.25)

    for key, label, color in (
        ("nwcl1_residual_mllw_ft", "NWCL1 observed − predicted residual (MLLW)", "#1f77b4"),
        ("mdll1_stage_anomaly_72h_native_ft", "MDLL1 anomaly vs own preceding 72h median", "#ff7f0e"),
    ):
        axes[2].plot(xresp, [row.get(key) if row.get(key) is not None else nan for row in responses], color=color, lw=1.0, label=label)
    axes[2].axhline(0, color="black", lw=.6)
    axes[2].set_ylabel("Within-station\nanomaly (ft)")
    axes[2].legend(loc="upper left", fontsize=8)
    axes[2].grid(alpha=.25)

    axes[3].plot(xresp, [row.get("maul1_stage_change_24h_native_ft") if row.get("maul1_stage_change_24h_native_ft") is not None else nan for row in responses], color="#9467bd", lw=1.0, label="MAUL1 00065 native stage Δ24h (ft)")
    axes[3].axhline(0, color="black", lw=.6)
    axes[3].set_ylabel("MAUL1 Δ24h\n(native ft)")
    axes[3].grid(alpha=.25)
    river = axes[3].twinx()
    river.plot(xresp, [row.get("denl1_discharge_change_24h_cfs") if row.get("denl1_discharge_change_24h_cfs") is not None else nan for row in responses], color="#17becf", lw=.9, alpha=.8, label="DENL1 discharge Δ24h (cfs)")
    river.set_ylabel("DENL1 discharge Δ24h (cfs)")
    lines, labels = axes[3].get_legend_handles_labels()
    lines2, labels2 = river.get_legend_handles_labels()
    axes[3].legend(lines + lines2, labels + labels2, loc="upper left", fontsize=8)
    axes[3].set_xlabel("UTC (hourly valid-time archive; no receipt-time information)")
    axes[3].xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
    axes[3].xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M"))

    for ax in axes:
        for phase in case["phases"]:
            x = _time(phase["start_utc"])
            if begin < x < finish:
                ax.axvline(x, color="#555555", lw=.7, alpha=.35)
    axes[0].text(.995, .98, "NWCL1 is a shoreline site, not an open-water wind field", transform=axes[0].transAxes,
                  ha="right", va="top", fontsize=8, color="#555555")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)


def run(archive_dir=None, output_dir=None):
    archive_dir = pathlib.Path(archive_dir or REPO / "site/data/history/hourly")
    output_dir = pathlib.Path(output_dir or PACKAGE)
    cases = json.loads((PACKAGE / "event_windows.json").read_text(encoding="utf-8"))
    out_cases, phase_rows, lag_rows = [], [], []
    all_hashes = {}
    for case in cases:
        phase_start = min(_time(phase["start_utc"]) for phase in case["phases"])
        phase_end = max(_time(phase["end_utc"]) for phase in case["phases"])
        load_start, load_end = phase_start - HOUR * 72, phase_end + HOUR * 78
        records, hashes = load_hourly_records(archive_dir, load_start.isoformat(), load_end.isoformat())
        all_hashes.update(hashes)
        wind_records = combine_wind_records(records)
        wind = build_wind_features(wind_records, windows=WINDOWS_HOURS, min_coverage=MIN_COVERAGE)
        response = build_response_features(records, change_windows=(1, 3, 6, 12, 24, 48, 72),
                                           baseline_hours=72, min_coverage=MIN_COVERAGE)
        phases = [_phase_summary(phase, records, wind, response) for phase in case["phases"]]
        for summary in phases:
            phase_rows.append({"case_id": case["id"], **summary})
        lag_profiles = _lag_profiles(case, wind, response)
        for profile in lag_profiles:
            for lag in profile["lag_hours"]:
                for target, components in lag["targets"].items():
                    for axis in ("eastward", "northward"):
                        lag_rows.append({"case_id": case["id"], "source_phase_id": profile["source_phase_id"],
                                         "lag_hours": lag["lag_hours"], "target": target, "component": axis,
                                         **components[axis]})
        case_output = {"id": case["id"], "label": case["label"],
                       "response_catalog": case.get("response_catalog"),
                       "observed_catalog_response": _catalog_response(case, records),
                       "observed_peak_timing": _observed_peak_timing(case, records, response),
                       "wind_site": case.get("wind_site"),
                       "presentation_reference": case.get("presentation_reference"),
                       "lag_source_phase_ids": case.get("lag_source_phase_ids", []),
                       "phase_summaries": phases,
                       "lag_profiles": lag_profiles,
                       "interpretation": "Descriptive, retrospectively selected event and control windows; temporal pairs overlap in forcing history and are not independent validation samples.",
                       "figure": f"figures/{case['id']}.svg"}
        out_cases.append(case_output)
        _make_plot(case, wind, response, output_dir / "figures" / f"{case['id']}.svg")
    result = {
        "schema": "maul1.coastal-response-diagnostics.v1",
        "status": "historical diagnostic / shadow research / not operational",
        "source_archive": (pathlib.Path(archive_dir).resolve().relative_to(REPO).as_posix()
                           if pathlib.Path(archive_dir).resolve().is_relative_to(REPO)
                           else "external archive supplied with --archive-dir"),
        "input_files_sha256": dict(sorted(all_hashes.items())),
        "calculation": {"time_basis": "UTC hourly valid-time archive; valid bins label hour start",
                        "minimum_rolling_window_coverage": MIN_COVERAGE,
                        "wind_windows_hours": list(WINDOWS_HOURS),
                        "source_coverage": "For each monthly file and station-variable, expected sub-hourly samples per hourly aggregate are set to the modal positive, nonmissing archived coverage; values below 80% of that month-specific mode are unusable. This accommodates documented historical cadence changes without imposing one modern cadence on the full record.",
                        "wind_stress_proxy_units": "kt²; integrated kt²·h; not physical air-sea stress",
                        "wind_source": "NWCL1 NOAA CO-OPS 8761927, New Canal shoreline; not lake-wide open-water truth",
                        "NWCL1_residual": "water minus prediction only exact matched hour/unit/datum",
                        "stage_changes": "within-station endpoints only; MAUL1 stage parameter 00065 native gage height; direct 63160 NAVD88 is excluded",
                        "directional_sector_duration": "total valid hourly bins by wind-from sector and threshold, separate from resultant duration; thresholds are exploratory descriptors",
                        "lag_profile": "24h trailing integrated directional proxy at t vs same-station 6h change beginning at t + lag; 6h-spaced samples; Pearson r reported only for >=6 pairs; no p values",
                        "missingness": "no interpolation; invalid bins fail source QC or break rolling coverage and directional runs. The archive has limited provider QC metadata; statistical outliers remain for review, not automatically removed.",
                        "rainfall": "no direct rainfall series in the selected hourly archive; DENL1 discharge is contextual, not a complete rainfall or runoff measure",
                        "receipt_timestamps": "not present in the historical hourly archive; historical issue-time availability cannot be asserted"},
        "cases": out_cases,
        "scientific_limits": [
            "NWCL1 shoreline winds do not establish the over-water lake wind field or fetch-aligned force.",
            "Averaged wind speed and direction support directional proxies only; actual stress needs sensor height, exposure, drag treatment, and higher-frequency observations.",
            "The maximum lag coefficient is not selected or promoted; profiles are serially dependent descriptions, not lead-time validation.",
            "Phase 3B rise/control windows are outcome-defined and retrospective; no predictive skill or causal attribution is claimed.",
            "June 27–July 1, 2024 is an unattributed transition response; not assigned to Beryl without independent evidence.",
            "MCHL1 is excluded from quantitative comparisons and remains shadow-only; stations' absolute water levels are not subtracted across datums."
        ]
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "diagnostics.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    _write_csv(output_dir / "phase_summary.csv", phase_rows)
    _write_csv(output_dir / "lag_profiles.csv", lag_rows)
    return result


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            flattened = {key: json.dumps(value, separators=(",", ":")) if isinstance(value, (dict, list)) else value for key, value in row.items()}
            writer.writerow(flattened)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", type=pathlib.Path, default=REPO / "site/data/history/hourly")
    parser.add_argument("--output-dir", type=pathlib.Path, default=PACKAGE)
    args = parser.parse_args()
    result = run(args.archive_dir, args.output_dir)
    print(f"Wrote {len(result['cases'])} fixed case/control diagnostics using {len(result['input_files_sha256'])} monthly archives")
    print(f"Output: {pathlib.Path(args.output_dir).resolve()}")


if __name__ == "__main__":
    main()
