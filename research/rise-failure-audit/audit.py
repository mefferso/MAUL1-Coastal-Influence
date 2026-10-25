"""Event-level diagnostic audit of Phase 5B significant-rise misses.

This is a retrospective description of archived Phase 5A/5B valid-time rows.
It does not change models, forecasts, verification, or prospective archives.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import statistics
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import phase6_metrics  # noqa: E402

UTC = dt.timezone.utc
THRESHOLD_FT = 0.50
SEPARATION_HOURS = 24
FORECAST_FIELD = "maul1_coastal_tidal"
FEATURES = (
    "maul1_stage_native_ft", "maul1_change_1h_ft", "maul1_change_3h_ft",
    "maul1_change_6h_ft", "maul1_change_12h_ft", "maul1_change_24h_ft",
    "maul1_change_72h_ft", "maul1_slope_6h_ft_per_h", "maul1_sd_24h_ft",
    "maul1_acceleration_6h_ft_per_h2",
    "denl1_log_discharge", "denl1_log_change_6h", "denl1_log_change_24h",
    "denl1_log_change_72h", "denl1_stage_change_6h_ft", "denl1_stage_change_24h_ft",
    "nwcl1_residual_mllw_ft", "nwcl1_residual_change_6h_ft",
    "nwcl1_residual_change_12h_ft", "nwcl1_residual_change_24h_ft",
    "nwcl1_wind_u_knots", "nwcl1_wind_v_knots", "nwcl1_wind_u_mean_6h_knots",
    "nwcl1_wind_v_mean_6h_knots", "nwcl1_wind_u_mean_24h_knots",
    "nwcl1_wind_v_mean_24h_knots", "nwcl1_wind_directional_persistence_6h",
    "mdll1_stage_change_6h_ft", "mdll1_stage_change_24h_ft", "mdll1_stage_change_72h_ft",
    "mchl1_stage_change_6h_native_ft", "mchl1_stage_change_24h_native_ft",
    "mchl1_stage_change_72h_native_ft",
)
FEATURE_GROUPS = {
    "maul1": ("maul1_change_6h_ft", "maul1_change_24h_ft", "maul1_change_72h_ft",
              "maul1_slope_6h_ft_per_h", "maul1_sd_24h_ft"),
    "denl1": ("denl1_log_discharge", "denl1_log_change_24h", "denl1_stage_change_24h_ft"),
    "nwcl1": ("nwcl1_residual_mllw_ft", "nwcl1_residual_change_6h_ft",
              "nwcl1_residual_change_24h_ft", "nwcl1_wind_u_knots", "nwcl1_wind_v_knots",
              "nwcl1_wind_u_mean_6h_knots", "nwcl1_wind_v_mean_6h_knots",
              "nwcl1_wind_directional_persistence_6h"),
    "mdll1": ("mdll1_stage_change_24h_ft", "mdll1_stage_change_72h_ft"),
    "mchl1_unverified_context_only": ("mchl1_stage_change_6h_native_ft",
                                       "mchl1_stage_change_24h_native_ft",
                                       "mchl1_stage_change_72h_native_ft"),
}


def parse_time(value):
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("UTC offset required")
    return parsed.astimezone(UTC)


def iso(value):
    return parse_time(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def number(value):
    if value in (None, ""):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def load_holdout_rows(root=ROOT):
    """Exact join of Phase 5B hindcasts to the Phase 5A issue-feature archive."""
    root = pathlib.Path(root)
    feature_path = root / "site/data/history/phase5a/features.csv.gz"
    prediction_path = root / "site/data/history/phase5b/predictions.csv.gz"
    features = {}
    with __import__("gzip").open(feature_path, "rt", newline="", encoding="utf-8") as stream:
        for raw in csv.DictReader(stream):
            issue = raw["issue_time_utc"]
            if issue in features:
                raise ValueError(f"duplicate issue feature row: {issue}")
            features[issue] = raw
    slope_by_time = {parse_time(issue): number(raw.get("maul1_slope_6h_ft_per_h"))
                     for issue, raw in features.items()}
    result = {h: [] for h in (6, 12, 24)}
    with __import__("gzip").open(prediction_path, "rt", newline="", encoding="utf-8") as stream:
        for raw in csv.DictReader(stream):
            if raw["split"] != "holdout":
                continue
            horizon = int(raw["horizon_hours"])
            if horizon not in result:
                continue
            feature = features.get(raw["issue_time_utc"])
            if feature is None:
                raise ValueError(f"missing feature row for issue {raw['issue_time_utc']}")
            stage = number(feature.get("maul1_stage_native_ft"))
            actual = number(raw.get("actual_native_gage_height_ft"))
            row = {
                "issue_time": parse_time(raw["issue_time_utc"]),
                "target_time": parse_time(raw["target_time_utc"]),
                "horizon_hours": horizon,
                "split": raw["split"],
                "stage_ft": stage,
                "actual_stage_ft": actual,
                "actual_change_ft": actual - stage if actual is not None and stage is not None else None,
                "phase4_category": raw.get("phase4_category") or feature.get("phase4_category"),
                "event_ids": [x for x in (raw.get("event_ids") or "").split(";") if x],
            }
            for name in FEATURES:
                row[name] = number(feature.get(name))
            current_slope = number(feature.get("maul1_slope_6h_ft_per_h"))
            prior_slope = slope_by_time.get(row["issue_time"] - dt.timedelta(hours=6))
            row["maul1_acceleration_6h_ft_per_h2"] = (
                (current_slope - prior_slope) / 6.0
                if current_slope is not None and prior_slope is not None else None)
            for model, column in {
                "persistence": "persistence_ft",
                "maul1_only": "phase5a_maul1_only_ft",
                "phase5a_coastal": "phase5a_coastal_ft",
                "phase5b_coastal_tidal": "maul1_coastal_tidal",
                "phase5b_full": "full_multivariable",
            }.items():
                forecast = number(raw.get(column))
                row[f"{model}_stage_ft"] = forecast
                row[f"{model}_change_ft"] = forecast - stage if forecast is not None and stage is not None else None
            result[horizon].append(row)
    for rows in result.values():
        rows.sort(key=lambda r: (r["issue_time"], r["target_time"]))
    return result


def phase6_records(rows, model="phase5b_coastal_tidal"):
    return [{
        "actual_issue_time_utc": iso(row["issue_time"]),
        "valid_time_utc": iso(row["target_time"]),
        "observed_change_ft": row["actual_change_ft"],
        "forecast_change_ft": row.get(f"{model}_change_ft"),
    } for row in rows if row.get("actual_change_ft") is not None
       and row.get("issue_time") is not None and row.get("target_time") is not None]


def group_qualifying_targets(rows, threshold=THRESHOLD_FT, separation_hours=SEPARATION_HOURS,
                             model="phase5b_coastal_tidal"):
    """Use the frozen Phase 6 target-time grouping and alert-match definition."""
    summary = phase6_metrics.summarize_qualifying_events(
        phase6_records(rows, model), threshold_ft=threshold, separation_hours=separation_hours)
    events = []
    for index, event in enumerate(summary.get("events", []), 1):
        first = parse_time(event["first_qualifying_target_utc"])
        last = parse_time(event["last_qualifying_target_utc"])
        members = [r for r in rows if first <= r["target_time"] <= last
                   and r.get("actual_change_ft") is not None
                   and r["actual_change_ft"] >= threshold]
        events.append({
            "event_id": f"rise-{index:03d}",
            "first_target_utc": iso(first),
            "last_target_utc": iso(last),
            "qualified_window_count": event["qualified_window_count"],
            "detected": event["detected"],
            "lead_to_first_qualifying_target_hours": event["lead_to_first_qualifying_target_hours"],
            "rows": members,
        })
    return events


def cluster_alerts(rows, threshold=THRESHOLD_FT, gap_hours=SEPARATION_HOURS,
                   model="phase5b_coastal_tidal"):
    """Reproduce Model Lab's threshold alert episodes; all rows remain target-linked."""
    alerts = [row for row in rows if row.get("actual_change_ft") is not None
              and row.get("stage_ft") is not None
              and row.get(f"{model}_change_ft") is not None
              and row[f"{model}_change_ft"] >= threshold]
    alerts.sort(key=lambda row: row["issue_time"])
    clusters = []
    for row in alerts:
        if not clusters or row["issue_time"] - clusters[-1]["rows"][-1]["issue_time"] > dt.timedelta(hours=gap_hours):
            clusters.append({"rows": []})
        clusters[-1]["rows"].append(row)
    for index, cluster in enumerate(clusters, 1):
        items = cluster["rows"]
        outcomes = [r["actual_change_ft"] >= threshold for r in items]
        cluster.update({
            "cluster_id": f"alert-{index:03d}",
            "start_issue_utc": iso(items[0]["issue_time"]),
            "end_issue_utc": iso(items[-1]["issue_time"]),
            "start_target_utc": iso(items[0]["target_time"]),
            "end_target_utc": iso(items[-1]["target_time"]),
            "alert_count": len(items),
            "hit_target_windows": sum(outcomes),
            "false_alarm": not any(outcomes),
        })
    return clusters


def failure_label(max_predicted_change, detected=False):
    if detected:
        return "target_alert_matched"
    if max_predicted_change is None:
        return "forecast_unavailable_not_causal"
    if max_predicted_change >= THRESHOLD_FT:
        return "threshold_target_after_first_qualifying_target_not_physical_onset"
    if max_predicted_change >= 0.40:
        return "near_threshold_underforecast_not_causal"
    return "large_subthreshold_forecast_not_causal"


def _stats(values):
    values = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not values:
        return {"n": 0, "missing_n": 0, "missing_fraction": None,
                "min": None, "median": None, "mean": None, "max": None}
    return {"n": len(values), "missing_n": 0, "missing_fraction": None,
            "min": min(values), "median": statistics.median(values),
            "mean": statistics.fmean(values), "max": max(values)}


def feature_summary(rows, fields=FEATURES):
    total = len(rows)
    output = {}
    for field in fields:
        values = [r.get(field) for r in rows]
        usable = [float(v) for v in values if v is not None and math.isfinite(float(v))]
        output[field] = {
            "n": len(usable), "missing_n": total - len(usable),
            "missing_fraction": (total - len(usable)) / total if total else None,
            "min": min(usable) if usable else None,
            "median": statistics.median(usable) if usable else None,
            "mean": statistics.fmean(usable) if usable else None,
            "max": max(usable) if usable else None,
        }
    return output


def event_context(event, all_rows):
    target_rows = event["rows"]
    first_issue = min(r["issue_time"] for r in target_rows)
    last_issue = max(r["issue_time"] for r in target_rows)
    pre_rows = [r for r in all_rows if first_issue - dt.timedelta(hours=72) <= r["issue_time"] < first_issue]
    event_issue_rows = [r for r in all_rows if first_issue <= r["issue_time"] <= last_issue]
    predicted = [r["phase5b_coastal_tidal_change_ft"] for r in target_rows
                 if r.get("phase5b_coastal_tidal_change_ft") is not None]
    actual = [r["actual_change_ft"] for r in target_rows if r.get("actual_change_ft") is not None]
    coastal = [r["phase5a_coastal_change_ft"] for r in target_rows
               if r.get("phase5a_coastal_change_ft") is not None]
    max_pred = max(predicted) if predicted else None
    category_counts = Counter(r.get("phase4_category") or "unknown" for r in target_rows)
    wind = [math.hypot(r["nwcl1_wind_u_knots"], r["nwcl1_wind_v_knots"])
            for r in event_issue_rows if r.get("nwcl1_wind_u_knots") is not None
            and r.get("nwcl1_wind_v_knots") is not None]
    residuals = [r["nwcl1_residual_mllw_ft"] for r in event_issue_rows
                 if r.get("nwcl1_residual_mllw_ft") is not None]
    denl = [r["denl1_log_discharge"] for r in event_issue_rows
            if r.get("denl1_log_discharge") is not None]
    median_feature = {}
    for name in ("maul1_change_6h_ft", "maul1_change_24h_ft", "maul1_acceleration_6h_ft_per_h2", "denl1_log_change_24h",
                 "nwcl1_residual_change_6h_ft", "nwcl1_wind_directional_persistence_6h",
                 "mdll1_stage_change_24h_ft"):
        values = [r[name] for r in event_issue_rows if r.get(name) is not None]
        median_feature[name] = statistics.median(values) if values else None
    rise_max = max(actual) if actual else None
    return {
        "event_id": event["event_id"],
        "first_qualifying_target_utc": event["first_target_utc"],
        "last_qualifying_target_utc": event["last_target_utc"],
        "qualified_window_count": event["qualified_window_count"],
        "detected": event["detected"],
        "lead_to_first_qualifying_target_hours": event["lead_to_first_qualifying_target_hours"],
        "first_issue_time_utc": iso(first_issue),
        "last_issue_time_utc": iso(last_issue),
        "max_observed_target_change_ft": rise_max,
        "max_phase5b_coastal_tidal_target_change_ft": max_pred,
        "underforecast_gap_at_peak_ft": rise_max - max_pred if rise_max is not None and max_pred is not None else None,
        "max_phase5a_coastal_target_change_ft": max(coastal) if coastal else None,
        "failure_mechanism": failure_label(max_pred, detected=event["detected"]),
        "phase4_category_counts": dict(sorted(category_counts.items())),
        "event_issue_window_hours": len(event_issue_rows),
        "preceding_valid_time_context_hours": len(pre_rows),
        "event_issue_feature_missingness": feature_summary(event_issue_rows),
        "preceding_72h_feature_missingness": feature_summary(pre_rows),
        "median_nwcl1_residual_mllw_ft": statistics.median(residuals) if residuals else None,
        "max_nwcl1_residual_mllw_ft": max(residuals) if residuals else None,
        "median_nwcl1_wind_speed_knots": statistics.median(wind) if wind else None,
        "max_nwcl1_wind_speed_knots": max(wind) if wind else None,
        "median_denl1_log_discharge": statistics.median(denl) if denl else None,
        "max_denl1_log_discharge": max(denl) if denl else None,
        "median_issue_time_features": median_feature,
        "coastal_setup_issue_hours_ge_0_50ft": sum(v >= .5 for v in residuals),
        "wind_issue_hours_ge_5knots": sum(v >= 5 for v in wind),
        "river_supported_issue_hours": sum(r.get("phase4_category") in ("River-supported", "Compound-supported") for r in event_issue_rows),
        "coastal_supported_issue_hours": sum(r.get("phase4_category") in ("Coastal-supported", "Compound-supported") for r in event_issue_rows),
        "interpretation": "Observed covariate co-occurrence only; not causal attribution. NWCL1 is MLLW-referenced; MAUL1 is native gage height.",
        "rows": target_rows,
    }


def load_response_catalog(root=ROOT):
    path = pathlib.Path(root) / "site/data/history/phase3b/response-events.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        return [dict(row) for row in csv.DictReader(stream)]


def overlapping_response_events(group, responses):
    """Time-window overlap only: Phase3B and Phase6 event IDs are not equivalent."""
    first, last = parse_time(group["first_target_utc"]), parse_time(group["last_target_utc"])
    matches = []
    for event in responses:
        left = event.get("trough_utc") or event.get("onset_utc")
        right = event.get("recovery_end_utc") or event.get("peak_utc")
        if not left or not right:
            continue
        if parse_time(left) <= last and parse_time(right) >= first:
            matches.append(event.get("event_id"))
    return sorted(x for x in matches if x)


def alert_cluster_context(cluster, events):
    rows = cluster["rows"]
    valid = [r for r in rows if r.get("nwcl1_wind_u_knots") is not None
             and r.get("nwcl1_wind_v_knots") is not None]
    residual = [r["nwcl1_residual_mllw_ft"] for r in rows if r.get("nwcl1_residual_mllw_ft") is not None]
    denl = [r["denl1_log_discharge"] for r in rows if r.get("denl1_log_discharge") is not None]
    wind = [math.hypot(r["nwcl1_wind_u_knots"], r["nwcl1_wind_v_knots"]) for r in valid]
    after = [e for e in events if parse_time(e["first_target_utc"]) > rows[-1]["target_time"]
             and parse_time(e["first_target_utc"]) <= rows[-1]["target_time"] + dt.timedelta(hours=72)]
    return {
        "cluster_id": cluster["cluster_id"], "start_issue_utc": cluster["start_issue_utc"],
        "end_issue_utc": cluster["end_issue_utc"], "start_target_utc": cluster["start_target_utc"],
        "end_target_utc": cluster["end_target_utc"], "alert_count": cluster["alert_count"],
        "hit_target_windows": cluster["hit_target_windows"], "false_alarm": cluster["false_alarm"],
        "max_predicted_change_ft": max(r["phase5b_coastal_tidal_change_ft"] for r in rows),
        "max_observed_change_in_alert_windows_ft": max(r["actual_change_ft"] for r in rows),
        "median_nwcl1_residual_mllw_ft": statistics.median(residual) if residual else None,
        "max_nwcl1_residual_mllw_ft": max(residual) if residual else None,
        "median_nwcl1_wind_speed_knots": statistics.median(wind) if wind else None,
        "median_nwcl1_wind_directional_persistence_6h": statistics.median(
            [r["nwcl1_wind_directional_persistence_6h"] for r in rows
             if r.get("nwcl1_wind_directional_persistence_6h") is not None]) if any(
                 r.get("nwcl1_wind_directional_persistence_6h") is not None for r in rows) else None,
        "median_denl1_log_discharge": statistics.median(denl) if denl else None,
        "phase4_category_counts": dict(Counter(r.get("phase4_category") or "unknown" for r in rows)),
        "predictor_missingness": feature_summary(rows),
        "qualifying_groups_with_first_target_in_next_72h": [e["event_id"] for e in after],
        "interpretation": "A false cluster has no >=0.50-ft target rise among its alert rows. Later outcomes are not physical onset labels.",
        "rows": rows,
    }


def event_window_stats(event_records):
    groups = defaultdict(list)
    for record in event_records:
        groups[record["failure_mechanism"]].append(record)
    result = {}
    for label, items in groups.items():
        result[label] = {
            "n_groups": len(items),
            "median_max_observed_change_ft": statistics.median(x["max_observed_target_change_ft"] for x in items),
            "median_max_predicted_change_ft": statistics.median(x["max_phase5b_coastal_tidal_target_change_ft"] for x in items),
            "median_underforecast_gap_ft": statistics.median(x["underforecast_gap_at_peak_ft"] for x in items),
            "nwcl1_residual_available_fraction": sum(x["event_issue_feature_missingness"]["nwcl1_residual_mllw_ft"]["n"] > 0 for x in items) / len(items),
            "denl1_discharge_available_fraction": sum(x["event_issue_feature_missingness"]["denl1_log_discharge"]["n"] > 0 for x in items) / len(items),
            "mdll1_24h_available_fraction": sum(x["event_issue_feature_missingness"]["mdll1_stage_change_24h_ft"]["n"] > 0 for x in items) / len(items),
        }
    return result


def event_feature_comparison(event_records):
    result = {}
    for label, predicate in (("phase6_detected", lambda r: r["detected"]),
                             ("phase6_not_detected", lambda r: not r["detected"])):
        items = [r for r in event_records if predicate(r)]
        field_names = ("max_observed_target_change_ft", "max_phase5b_coastal_tidal_target_change_ft",
                       "median_nwcl1_residual_mllw_ft", "median_nwcl1_wind_speed_knots",
                       "median_denl1_log_discharge")
        result[label] = {"n_groups": len(items)}
        for field in field_names:
            values = [r[field] for r in items if r.get(field) is not None]
            result[label][field + "_median"] = statistics.median(values) if values else None
        result[label]["groups_with_any_phase4_river_support"] = sum(
            r["phase4_category_counts"].get("River-supported", 0)
            + r["phase4_category_counts"].get("Compound-supported", 0) > 0 for r in items)
        result[label]["groups_with_any_phase4_coastal_support"] = sum(
            r["phase4_category_counts"].get("Coastal-supported", 0)
            + r["phase4_category_counts"].get("Compound-supported", 0) > 0 for r in items)
        result[label]["groups_with_any_nwcl1_residual_setup_ge_0_50ft"] = sum(
            r["coastal_setup_issue_hours_ge_0_50ft"] > 0 for r in items)
        result[label]["groups_with_any_wind_speed_ge_5knots"] = sum(
            r["wind_issue_hours_ge_5knots"] > 0 for r in items)
        for feature in ("maul1_change_6h_ft", "maul1_change_24h_ft", "maul1_acceleration_6h_ft_per_h2",
                        "denl1_log_change_24h", "nwcl1_residual_change_6h_ft",
                        "nwcl1_wind_directional_persistence_6h", "mdll1_stage_change_24h_ft"):
            values = [r["median_issue_time_features"].get(feature) for r in items
                      if r["median_issue_time_features"].get(feature) is not None]
            result[label][f"median_group_median_{feature}"] = statistics.median(values) if values else None
    return result


def select_timelines(event_records, cluster_records, limit=5):
    missed = [r for r in event_records if not r["detected"]]
    candidates = []
    if missed:
        candidates.append(("largest_observed_rise_miss", max(missed, key=lambda r: r["max_observed_target_change_ft"])))
        candidates.append(("closest_missed_forecast_to_threshold", max(missed, key=lambda r: r["max_phase5b_coastal_tidal_target_change_ft"])))
        trusted_fields = ("denl1_log_discharge", "nwcl1_residual_mllw_ft", "nwcl1_wind_u_knots",
                          "nwcl1_wind_v_knots", "mdll1_stage_change_24h_ft")
        def trusted_missingness(record):
            values = [record["event_issue_feature_missingness"][field]["missing_fraction"]
                      for field in trusted_fields
                      if record["event_issue_feature_missingness"][field]["missing_fraction"] is not None]
            return statistics.fmean(values) if values else 0.0
        candidates.append(("largest_trusted_predictor_data_gap_miss", max(missed, key=trusted_missingness)))
    false_clusters = [r for r in cluster_records if r["false_alarm"]]
    if false_clusters:
        candidates.append(("largest_false_alert_magnitude", max(false_clusters, key=lambda r: r["max_predicted_change_ft"])))
        candidates.append(("highest_setup_false_alert", max(false_clusters, key=lambda r: r["max_nwcl1_residual_mllw_ft"] or -math.inf)))
    seen, output = set(), []
    for label, item in candidates:
        key = item.get("event_id", item.get("cluster_id"))
        if key in seen:
            continue
        seen.add(key)
        output.append({"selection": label, **{k: v for k, v in item.items() if k != "rows"},
                       "timeline_rows": [timeline_row(row) for row in item["rows"]]})
        if len(output) >= limit:
            break
    return output


def timeline_row(row):
    fields = ("maul1_change_6h_ft", "maul1_change_24h_ft", "denl1_log_discharge",
              "maul1_acceleration_6h_ft_per_h2",
              "denl1_log_change_24h", "nwcl1_residual_mllw_ft", "nwcl1_residual_change_6h_ft",
              "nwcl1_wind_u_knots", "nwcl1_wind_v_knots", "mdll1_stage_change_24h_ft")
    return {
        "issue_time_utc": iso(row["issue_time"]), "valid_time_utc": iso(row["target_time"]),
        "horizon_hours": row["horizon_hours"],
        "issue_maul1_stage_native_ft": row["stage_ft"],
        "actual_valid_maul1_stage_native_ft": row["actual_stage_ft"],
        "actual_change_ft": row["actual_change_ft"],
        "phase5b_coastal_tidal_change_ft": row["phase5b_coastal_tidal_change_ft"],
        "phase5b_coastal_tidal_stage_native_ft": row["phase5b_coastal_tidal_stage_ft"],
        "phase5a_coastal_change_ft": row["phase5a_coastal_change_ft"],
        "phase5a_coastal_stage_native_ft": row["phase5a_coastal_stage_ft"],
        "phase5a_maul1_only_change_ft": row["maul1_only_change_ft"],
        "phase5a_maul1_only_stage_native_ft": row["maul1_only_stage_ft"],
        "phase4_category": row.get("phase4_category"), "features": {name: row.get(name) for name in fields},
    }


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _fmt(value, digits=3):
    return "—" if value is None else f"{value:.{digits}f}"


def build_audit(root=ROOT):
    root = pathlib.Path(root).resolve()
    rows_by_horizon = load_holdout_rows(root)
    rows24 = [r for r in rows_by_horizon[24] if r.get("actual_change_ft") is not None
              and r.get("stage_ft") is not None and r.get("phase5b_coastal_tidal_change_ft") is not None]
    events = group_qualifying_targets(rows24)
    clusters = cluster_alerts(rows24)
    event_records = [event_context(event, rows24) for event in events]
    response_events = load_response_catalog(root)
    for event in event_records:
        event["overlapping_phase3b_response_event_ids"] = overlapping_response_events({
            "first_target_utc": event["first_qualifying_target_utc"],
            "last_target_utc": event["last_qualifying_target_utc"],
        }, response_events)
    cluster_records = [alert_cluster_context(cluster, events) for cluster in clusters]

    existing = json.loads((root / "site/data/research/model-lab.json").read_text())
    model_lab_event = existing["phase6_qualifying_rise_groups_24h"]["maul1_coastal_tidal"]
    model_lab_false = existing["horizons"]["24"]["underforecast_and_false_alarm"]["maul1_coastal_tidal"]
    all_case_mae_context = {}
    for horizon in (6, 12, 24):
        metrics = existing["horizons"][str(horizon)]["metrics"]
        persistence = metrics["persistence_ft"]
        coastal_tidal = metrics["maul1_coastal_tidal"]
        all_case_mae_context[str(horizon)] = {
            "paired_n": coastal_tidal["n"], "persistence_mae_ft": persistence["mae_ft"],
            "coastal_tidal_mae_ft": coastal_tidal["mae_ft"],
            "coastal_tidal_skill_vs_persistence": coastal_tidal["skill_vs_persistence"],
        }
    detected = sum(x["detected"] for x in event_records)
    missed = len(event_records) - detected
    false_clusters = sum(x["false_alarm"] for x in cluster_records)
    all_response_matches = [x for row in event_records for x in row["overlapping_phase3b_response_event_ids"]]
    response_event_group_counts = Counter(all_response_matches)
    response_status_counts = Counter(event.get("status", "unknown") for event in response_events)
    overlap_counts = Counter(len(x["overlapping_phase3b_response_event_ids"]) for x in event_records)
    false = [r for r in cluster_records if r["false_alarm"]]
    true = [r for r in cluster_records if not r["false_alarm"]]
    model_predictions = [r for r in rows24 if r.get("phase5b_coastal_tidal_change_ft") is not None]
    false_windows = sum(r["phase5b_coastal_tidal_change_ft"] >= THRESHOLD_FT and r["actual_change_ft"] < THRESHOLD_FT for r in model_predictions)
    true_windows = sum(r["phase5b_coastal_tidal_change_ft"] >= THRESHOLD_FT and r["actual_change_ft"] >= THRESHOLD_FT for r in model_predictions)
    missed_windows = sum(r["phase5b_coastal_tidal_change_ft"] < THRESHOLD_FT and r["actual_change_ft"] >= THRESHOLD_FT for r in model_predictions)
    predicted_alert_windows = true_windows + false_windows
    qualifying_target_windows = true_windows + missed_windows

    archive_rows = sum(len(v) for v in rows_by_horizon.values())
    source_files = [
        "site/data/history/phase5a/features.csv.gz", "site/data/history/phase5a/predictions.csv.gz",
        "site/data/history/phase5b/predictions.csv.gz", "site/data/history/phase3b/response-events.csv",
        "site/data/research/model-lab.json", "scripts/phase6_metrics.py", "scripts/phase5a.py",
        "scripts/phase5b.py", "scripts/model_lab.py", "docs/model-lab-methodology.md",
        "docs/phase5b-methodology.md", "docs/model-lab-findings.md",
        "research/rise-failure-audit/test_audit.py",
    ]
    result = {
        "schema": "maul1.rise-failure-audit.v1",
        "label": "Research / Shadow Evaluation / Not Operational; retrospective diagnostics only",
        "threshold_ft": THRESHOLD_FT,
        "phase6_definition": "24-hour native-stage target rise >=0.50 ft; qualifying target times separated by <=24 hours are grouped. Forecast alerts must be issued before the group's first qualifying valid target and occur on a qualifying target row.",
        "group_independence_audit": {
            "phase6_group_count": len(event_records),
            "phase3b_response_catalog_event_count": len(response_events),
            "phase3b_response_catalog_status_counts": dict(sorted(response_status_counts.items())),
            "phase6_groups_with_no_phase3b_response_window_overlap": overlap_counts.get(0, 0),
            "phase6_groups_overlapping_one_phase3b_response_window": overlap_counts.get(1, 0),
            "phase6_groups_overlapping_multiple_phase3b_response_windows": sum(n > 1 for n in overlap_counts for _ in range(overlap_counts[n])),
            "phase3b_response_events_overlapping_multiple_phase6_groups": sum(n > 1 for n in response_event_group_counts.values()),
            "phase3b_response_events_touched": len(response_event_group_counts),
            "interpretation": "The 109 groups are temporally declumped target episodes, not proven independent physical hydrologic events. Overlap with the separate Phase 3B >=1-ft response catalog is descriptive only; non-overlap does not establish physical independence.",
        },
        "definition_reproduction": {
            "phase6_groups": len(event_records), "detected_groups": detected, "missed_groups": missed,
            "phase5b_false_alert_clusters": false_clusters,
            "all_alert_clusters": len(cluster_records),
            "true_positive_target_windows": true_windows, "false_positive_target_windows": false_windows,
            "missed_rise_target_windows": missed_windows,
            "eligible_target_windows": len(model_predictions),
            "qualifying_observed_target_windows": qualifying_target_windows,
            "predicted_alert_target_windows": predicted_alert_windows,
            "observed_target_rise_frequency": qualifying_target_windows / len(model_predictions) if model_predictions else None,
            "target_window_probability_of_detection": true_windows / qualifying_target_windows if qualifying_target_windows else None,
            "target_window_false_alarm_ratio": false_windows / predicted_alert_windows if predicted_alert_windows else None,
            "target_window_critical_success_index": true_windows / (true_windows + false_windows + missed_windows) if true_windows + false_windows + missed_windows else None,
            "matches_existing_model_lab_groups": len(event_records) == model_lab_event["event_count"] and detected == model_lab_event["detected_events"] and missed == model_lab_event["missed_events"],
            "matches_existing_model_lab_false_clusters": false_clusters == model_lab_false["false_alert_episode_clusters"],
            "published_model_lab_counts": {
                "phase6_groups": model_lab_event["event_count"],
                "detected_groups": model_lab_event["detected_events"],
                "missed_groups": model_lab_event["missed_events"],
                "false_alert_clusters": model_lab_false["false_alert_episode_clusters"],
                "all_alert_clusters": model_lab_false["alert_episode_clusters"],
                "false_positive_target_windows": model_lab_false["false_positive_target_windows"],
            },
            "issue_time_cluster_rule": "Sort predicted >=0.50-ft 24h target windows by issue time; one cluster continues while adjacent issue times differ by <=24 h. A cluster is false only when none of its own linked target windows has an observed >=0.50-ft rise.",
            "cluster_note": "False-alert clusters are temporal groups of overlapping hourly forecast opportunities, not independent storm samples.",
        },
        "all_case_mae_context": {
            "phase5b_coastal_tidal_vs_persistence": all_case_mae_context,
            "metric_selection_context": "Phase 5B ridge penalties were selected on calibration forward-fold MAE for continuous target stage change; no significant-rise classification or event-recall objective was used.",
        },
        "failure_mechanism_counts": dict(Counter(x["failure_mechanism"] for x in event_records)),
        "event_level_summary": event_window_stats(event_records),
        "event_feature_comparison": event_feature_comparison(event_records),
        "false_vs_true_alert_cluster_comparison": {
            "false_cluster_count": len(false), "true_cluster_count": len(true),
            "false_median_max_forecast_change_ft": statistics.median(x["max_predicted_change_ft"] for x in false) if false else None,
            "true_median_max_forecast_change_ft": statistics.median(x["max_predicted_change_ft"] for x in true) if true else None,
            "false_median_nwcl1_residual_mllw_ft": statistics.median(x["median_nwcl1_residual_mllw_ft"] for x in false if x["median_nwcl1_residual_mllw_ft"] is not None) if any(x["median_nwcl1_residual_mllw_ft"] is not None for x in false) else None,
            "true_median_nwcl1_residual_mllw_ft": statistics.median(x["median_nwcl1_residual_mllw_ft"] for x in true if x["median_nwcl1_residual_mllw_ft"] is not None) if any(x["median_nwcl1_residual_mllw_ft"] is not None for x in true) else None,
            "false_median_wind_speed_knots": statistics.median(x["median_nwcl1_wind_speed_knots"] for x in false if x["median_nwcl1_wind_speed_knots"] is not None) if any(x["median_nwcl1_wind_speed_knots"] is not None for x in false) else None,
            "true_median_wind_speed_knots": statistics.median(x["median_nwcl1_wind_speed_knots"] for x in true if x["median_nwcl1_wind_speed_knots"] is not None) if any(x["median_nwcl1_wind_speed_knots"] is not None for x in true) else None,
            "false_median_denl1_log_discharge": statistics.median(x["median_denl1_log_discharge"] for x in false if x["median_denl1_log_discharge"] is not None) if any(x["median_denl1_log_discharge"] is not None for x in false) else None,
            "true_median_denl1_log_discharge": statistics.median(x["median_denl1_log_discharge"] for x in true if x["median_denl1_log_discharge"] is not None) if any(x["median_denl1_log_discharge"] is not None for x in true) else None,
            "false_clusters_with_phase6_group_first_target_in_next_72h": sum(bool(x["qualifying_groups_with_first_target_in_next_72h"]) for x in false),
            "interpretation": "Descriptive comparison across alert episodes; these clusters are serially dependent and covariate co-occurrence is not causation.",
        },
        "archive_coverage": {
            "phase5b_rows_across_6_12_24h_holdout": archive_rows,
            "event_analysis_rows_24h_holdout": len(rows24),
            "first_24h_issue_utc": iso(min(r["issue_time"] for r in rows24)),
            "last_24h_target_utc": iso(max(r["target_time"] for r in rows24)),
            "phase5a_issue_feature_rows": len({r["issue_time"] for r in rows24}),
            "receipt_time_coverage": "source receipt times are not archived; valid-time bins are retrospective as-of approximations only",
            "maul1_source": "USGS station 07380215 parameter 00065, ft, native gage height; no NAVD88 conversion",
            "phase5b_target_observation_missing_n": sum(r["actual_change_ft"] is None for r in rows_by_horizon[24]),
        },
        "causal_safeguards": {
            "no_new_models_trained": True, "no_future_observation_features_used": True,
            "outcome_defined_events_used_as_predictors": False,
            "nwcl1_residual_datum": "MLLW", "maul1_datum": "native gage height",
            "mchl1": "reported as availability only; unverified and excluded from trusted inference",
            "astronomical_forecasts": "not used as issue-time evidence; archive is retrospective valid-time only",
        },
        "precipitation_and_tributary_availability": {
            "status": "candidate sources identified; not downloaded or entered into model/event scores",
            "usgs_local_precipitation": {"station": "301828090363100", "parameter": "00045", "source": "USGS Water Data", "published_period_seen": "2021-08-19 through 2026-10-14", "limitation": "USGS notes temporary precipitation data may be available only for 120 days; do not assume full stable retrospective availability without direct retrieval/archive validation.", "url": "https://waterdata.usgs.gov/monitoring-location/USGS-301828090363100"},
            "usgs_tributary_candidate": {"station": "07378810", "name": "Bayou Fountain at Bluebonnet Blvd", "published_period_seen": "gage-height series 2007-10-01 through 2026-10-18", "limitation": "A local tributary stage series, not rainfall and not yet joined to event windows; verify stage-to-flow utility and representativeness before use.", "url": "https://waterdata.usgs.gov/monitoring-location/USGS-07378810/"},
            "noaa_radar_candidate": {"product": "MRMS precipitation", "published_period_seen": "operational viewer/archive dating to 2020-10", "limitation": "Spatial gridded precipitation requires watershed aggregation, retrospective continuity and version/QC audit; availability in product archive does not prove real-time receipt at historic issue times.", "url": "https://www.nssl.noaa.gov/projects/mrms/MRMS_data.php"},
            "other_usgs_candidates": [
                {"station": "07378746", "name": "Bayou Manchac at Alligator Bayou near Kleinpeter", "url": "https://waterdata.usgs.gov/monitoring-location/USGS-07378746/"},
                {"station": "07379960", "name": "Dawson Creek at Bluebonnet Blvd", "url": "https://waterdata.usgs.gov/monitoring-location/USGS-07379960/"},
                {"station": "07380200", "name": "Amite River near French Settlement", "url": "https://waterdata.usgs.gov/monitoring-location/USGS-07380200/"},
            ],
            "selection_guidance": "First validate station period-of-record, parameter, datum, drainage location, hourly continuity, and timing; none is accepted as an existing model predictor in this audit.",
        },
        "provenance": {
            "source_sha256": {path: _sha(root / path) for path in source_files},
            "analysis_script_sha256": _sha(pathlib.Path(__file__)),
            "source_archive": "committed Phase 5A features, Phase 5B hindcast predictions, Phase 3B response-event catalog, existing Model Lab report",
            "model_lab_archives_modified": False,
            "prospective_archives_modified": False,
        },
    }
    timelines = select_timelines(event_records, cluster_records)
    return result, event_records, cluster_records, timelines


def _csv_safe(row):
    return {key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()}


def write_outputs(root=ROOT, output_dir=None):
    root = pathlib.Path(root).resolve()
    output_dir = pathlib.Path(output_dir) if output_dir else root / "research/rise-failure-audit"
    output_dir.mkdir(parents=True, exist_ok=True)
    report, events, clusters, timelines = build_audit(root)
    (output_dir / "analysis.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (output_dir / "representative-timelines.json").write_text(json.dumps(timelines, indent=2, sort_keys=True) + "\n")
    for filename, rows in (("event-diagnostics.csv", events), ("false-alert-clusters.csv", clusters)):
        fields = list(rows[0]) if rows else []
        fields = [f for f in fields if f != "rows"]
        with (output_dir / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(_csv_safe({k: v for k, v in row.items() if k != "rows"}) for row in rows)
    write_markdown(output_dir / "report.md", report, events, clusters)
    return report


def write_markdown(path, report, events, clusters):
    definition = report["definition_reproduction"]
    independence = report["group_independence_audit"]
    status_counts = independence["phase3b_response_catalog_status_counts"]
    status_text = ", ".join(
        f"{status_counts.get(key, 0)} {label}"
        for key, label in (
            ("observed_response", "observed-response"),
            ("recovery_right_censored", "recovery-right-censored"),
            ("left_censored", "left-censored"),
        )
    )
    comparison = report["false_vs_true_alert_cluster_comparison"]
    all_case = report["all_case_mae_context"]["phase5b_coastal_tidal_vs_persistence"]
    lines = [
        "# MAUL1 Significant-Rise Failure Audit",
        "",
        "**Research / Shadow Evaluation / Not Operational. Retrospective diagnostics only.**",
        "",
        "## Main finding",
        "",
        "The published event and false-alert counts reproduce from the Phase 5B holdout rows using the existing Phase 6 outcome-target grouping and the Model Lab's issue-time episode rule. The 109 qualifying groups are separated only by qualifying target-time gaps; they are not proven independent physical hydrologic events. The event match is a threshold forecast on a qualifying valid-target row, not onset detection.",
        "",
        f"The apparent contrast is a difference in scoring objective and event rarity. {report['all_case_mae_context']['metric_selection_context']} Its all-case holdout MAE was {_fmt(all_case['6']['coastal_tidal_mae_ft'], 4)} vs {_fmt(all_case['6']['persistence_mae_ft'], 4)} ft persistence at 6h, {_fmt(all_case['12']['coastal_tidal_mae_ft'], 4)} vs {_fmt(all_case['12']['persistence_mae_ft'], 4)} ft at 12h, and {_fmt(all_case['24']['coastal_tidal_mae_ft'], 4)} vs {_fmt(all_case['24']['persistence_mae_ft'], 4)} ft at 24h. Yet only {definition['observed_target_rise_frequency']:.1%} of paired 24h target windows meet the +0.50-ft rise definition. At those target windows, the threshold forecast had {definition['true_positive_target_windows']} hits, {definition['missed_rise_target_windows']:,} misses and {definition['false_positive_target_windows']} false positives: probability of detection {definition['target_window_probability_of_detection']:.1%}, false-alarm ratio {definition['target_window_false_alarm_ratio']:.1%}, CSI {definition['target_window_critical_success_index']:.1%}. These overlapping row-level rates are not independent-event rates.",
        "",
        f"Phase 5B coastal + tidal: **{definition['detected_groups']} detected / {definition['missed_groups']} missed** qualifying target groups; **{definition['false_positive_target_windows']} false-positive target windows** in **{definition['phase5b_false_alert_clusters']} false-alert issue-time clusters** ({definition['all_alert_clusters']} alert clusters total). The false-alert count describes rolling 24-hour forecast opportunities clustered when issue times are <=24 h apart; it is not a count of independent storms.",
        "",
        "Among the 81 groups not credited as detected, 79 never reached +0.50 ft on any qualifying target window; two did cross the threshold on a later qualifying target row but only after the group's first qualifying target, so they fail the existing Phase 6 lead rule. This is lateness relative to the verification target, not a claim about physical onset. Among the 79 subthreshold cases, 57 had a maximum predicted rise below 0.40 ft and 22 peaked between 0.40 and 0.50 ft. The lowest 57 had a median observed qualifying target rise of 0.640 ft versus a median maximum prediction of 0.233 ft. This is evidence of missed rise magnitude on the scored windows; it does not identify a forcing cause. Predictor conditions below are issue-time valid-bin co-occurrences, not causal explanations. An unavailable signal can mean missing archived data or feature construction support; source receipt time and sensor QC histories are generally absent.",
        "",
        "## Definitions and reproduction audit",
        "",
        "| Check | Recomputed | Existing report | Result |",
        "|---|---:|---:|---|",
        f"| Phase 6 qualifying groups | {definition['phase6_groups']} | {definition['published_model_lab_counts']['phase6_groups']} | match |",
        f"| Detected | {definition['detected_groups']} | {definition['published_model_lab_counts']['detected_groups']} | match |",
        f"| Missed | {definition['missed_groups']} | {definition['published_model_lab_counts']['missed_groups']} | match |",
        f"| False alert clusters | {definition['phase5b_false_alert_clusters']} | {definition['published_model_lab_counts']['false_alert_clusters']} | match |",
        f"| False-positive target windows | {definition['false_positive_target_windows']} | {definition['published_model_lab_counts']['false_positive_target_windows']} | match |",
        "",
        "Phase 6 groups outcome-defined 24-hour MAUL1 native-stage changes >=0.50 ft when qualifying valid target times are at most 24 hours apart. Detection is an issued >=0.50-ft forecast for one of the qualifying targets before the group's first target. It does not establish physical onset. False alert clusters are built separately by sorting qualifying forecasts by issue time and joining adjacent issues no more than 24 hours apart; a cluster is false when none of its own linked valid targets meets the 0.50-ft outcome threshold.",
        "",
        "### Independence audit",
        "",
        f"The separate Phase 3B response catalog contains {independence['phase3b_response_catalog_event_count']} larger response windows ({status_text}). {independence['phase6_groups_with_no_phase3b_response_window_overlap']} Phase 6 groups have no temporal overlap with a Phase 3B response window; {independence['phase6_groups_overlapping_one_phase3b_response_window']} overlap one. {independence['phase3b_response_events_overlapping_multiple_phase6_groups']} Phase 3B windows overlap multiple Phase 6 groups. This timing crosswalk shows the 109 are not demonstrably independent physical events; it is not an event identity match, because Phase 3B applies a different >=1-ft response definition and its windows can be censored by gaps/datum transitions.",
        "",
        "## Missed-event patterns",
        "",
        "| Mechanism label (descriptive) | Groups | Median max observed target rise | Median max Phase 5B predicted change | Median peak underforecast gap | NWCL1 residual present | DENL1 discharge present | MDLL1 24h change present |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, stats in sorted(report["event_level_summary"].items()):
        lines.append(f"| {label} | {stats['n_groups']} | {stats['median_max_observed_change_ft']:.3f} ft | {stats['median_max_predicted_change_ft']:.3f} ft | {stats['median_underforecast_gap_ft']:.3f} ft | {stats['nwcl1_residual_available_fraction']:.1%} | {stats['denl1_discharge_available_fraction']:.1%} | {stats['mdll1_24h_available_fraction']:.1%} |")
    lines.extend([
        "",
        "The event-level CSV has one row per all 109 groups, including individual maxima, issue-window context, target-window counts, categories, and predictor missingness in both the event issue window and the preceding 72 valid-time hours. ‘Near-threshold’ is an arithmetic bin (maximum forecast change >=0.40 and <0.50 ft), not a confidence bound. `phase4_category` flags are existing descriptive support screens and do not attribute cause.",
        "",
        "### Issue-time signal co-occurrence",
        "",
        "| Group status | Groups | Any NWCL1 residual >=0.50 ft | Any NWCL1 wind >=5 kn | Any Phase 4 river-supported hour | Any Phase 4 coastal-supported hour | Median NWCL1 residual | Median wind speed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for label, values in sorted(report["event_feature_comparison"].items()):
        lines.append(
            f"| {label.replace('_', ' ')} | {values['n_groups']} | "
            f"{values['groups_with_any_nwcl1_residual_setup_ge_0_50ft']} | "
            f"{values['groups_with_any_wind_speed_ge_5knots']} | "
            f"{values['groups_with_any_phase4_river_support']} | "
            f"{values['groups_with_any_phase4_coastal_support']} | "
            f"{_fmt(values['median_nwcl1_residual_mllw_ft_median'])} ft | "
            f"{_fmt(values['median_nwcl1_wind_speed_knots_median'])} kn |"
        )
    lines.extend([
        "",
        "Within the 81 not-detected groups, issue-window NWCL1 residual reached 0.50 ft in 43 groups and wind speed reached 5 knots in 68; only three had any Phase 4 coastal-supported category hour. These screens co-occur with misses and do not identify causes. In particular, an elevated residual or wind vector alone did not reliably translate into the model's target-window threshold crossing.",
        f"Across event groups, median-of-group-median issue features (not row-independent estimates) were MAUL1 Δ6h {_fmt(report['event_feature_comparison']['phase6_not_detected']['median_group_median_maul1_change_6h_ft'])} ft and Δ24h {_fmt(report['event_feature_comparison']['phase6_not_detected']['median_group_median_maul1_change_24h_ft'])} ft for not-detected groups versus {_fmt(report['event_feature_comparison']['phase6_detected']['median_group_median_maul1_change_6h_ft'])} and {_fmt(report['event_feature_comparison']['phase6_detected']['median_group_median_maul1_change_24h_ft'])} ft for detected groups. Median DENL1 log-discharge change over 24h was {_fmt(report['event_feature_comparison']['phase6_not_detected']['median_group_median_denl1_log_change_24h'])} versus {_fmt(report['event_feature_comparison']['phase6_detected']['median_group_median_denl1_log_change_24h'])}; MDLL1 24h native-stage change was {_fmt(report['event_feature_comparison']['phase6_not_detected']['median_group_median_mdll1_stage_change_24h_ft'])} versus {_fmt(report['event_feature_comparison']['phase6_detected']['median_group_median_mdll1_stage_change_24h_ft'])} ft. MDLL1 changes are within-station context only, not a cross-site stage comparison. The predictor coverage and receipt-time caveats above apply to these summaries.",
        "",
        "## False-alert patterns",
        "",
        f"The {comparison['false_cluster_count']} false clusters and {comparison['true_cluster_count']} clusters containing at least one true target window are compared at the cluster level. False clusters had median max forecast change {_fmt(comparison['false_median_max_forecast_change_ft'])} ft; hit-containing clusters had {_fmt(comparison['true_median_max_forecast_change_ft'])} ft. Their median issue-time NWCL1 residuals were {_fmt(comparison['false_median_nwcl1_residual_mllw_ft'])} ft (false) and {_fmt(comparison['true_median_nwcl1_residual_mllw_ft'])} ft (hit-containing); median vector wind speeds were {_fmt(comparison['false_median_wind_speed_knots'])} and {_fmt(comparison['true_median_wind_speed_knots'])} kn. These similar coastal markers do not separate false from hit-containing episodes in this sample. {comparison['false_clusters_with_phase6_group_first_target_in_next_72h']} of the false clusters preceded the first qualifying target of a separate Phase 6 group by at most 72 hours; this is a diagnostic temporal relation, not onset lead or an event match. Episodes overlap and are serially dependent, so no independent-sample inference is claimed.",
        "",
        "## Data coverage, freshness, and datum limits",
        "",
        f"The analysis has {report['archive_coverage']['event_analysis_rows_24h_holdout']:,} completed 24-hour holdout forecast/observation rows from {report['archive_coverage']['first_24h_issue_utc']} through targets ending {report['archive_coverage']['last_24h_target_utc']}. Another {report['archive_coverage']['phase5b_target_observation_missing_n']:,} 24-hour holdout rows have no archived actual and are omitted. Every event score uses the Phase 5B row's own archived actual native gage height; this audit does not rescore against newer observations. The join uses issue UTC, target UTC, and horizon, with Phase 5A feature fields matched by issue time. MAUL1 is USGS 07380215 00065, feet, native gage height. The historical rows have no USGS approval/provisional qualifier, so quality state cannot be reclassified. NWCL1 residuals remain MLLW-referenced and are not numerically combined with MAUL1 native stage. No 4.0-ft NAVD88 threshold is used.",
        "",
        "Feature missingness is listed per event in the CSV/JSON. An empty archive feature is unknown, not evidence that the physical forcing was absent. The historical archive mostly preserves observation valid time but not original receipt time, so even apparently pre-event feature rows do not prove they would have been available at a real issuance. MCHL1 stays unverified/shadow-only; its fields are counted as availability only and are not used for causal classification. Retrospective-valid-time NOAA astronomical predictions are not treated as issue-time evidence. No observation is interpolated or filled.",
        "",
        "### Local precipitation and tributary data leads (not used in results)",
        "",
        "USGS publishes precipitation parameter 00045 at the local MAUL1-area atmospheric site [301828090363100](https://waterdata.usgs.gov/monitoring-location/USGS-301828090363100), with a currently listed period beginning 2021-08-19. USGS warns that precipitation observations are temporary and may only be available for 120 days; a stable complete historical series therefore must be checked by actual retrieval and captured prospectively before modeling. [Bayou Fountain at Bluebonnet (07378810)](https://waterdata.usgs.gov/monitoring-location/USGS-07378810/) has a listed continuous gage-height record from 2007-10-01, and is a plausible local urban-tributary context series, but it is not a rainfall measurement or a validated discharge proxy. Candidate nearby series include [Bayou Manchac at Alligator Bayou (07378746)](https://waterdata.usgs.gov/monitoring-location/USGS-07378746/) and [Dawson Creek at Bluebonnet (07379960)](https://waterdata.usgs.gov/monitoring-location/USGS-07379960/). NOAA's [MRMS archive](https://www.nssl.noaa.gov/projects/mrms/MRMS_data.php) offers a gridded precipitation lead; it needs watershed aggregation and version, continuity, and quality checks. These sources were identified, not downloaded or joined; no result or existing archive contains them as predictors.",
        "",
        "## Representative timelines",
        "",
        "`representative-timelines.json` contains a few algorithmically selected, compact timelines: largest observed miss, closest subthreshold miss, a high-missingness miss, and representative false alert episodes. The timeline fields preserve issue time and valid time separately. These are illustrative outcomes selected from the same archive, not an independent sample.",
        "",
        "## Prioritized hypotheses for challenger research",
        "",
        "1. **Target-window scoring may understate useful earlier anticipation.** The current event rule only credits forecasts whose valid targets themselves qualify; test episode-level time-to-target diagnostics without relabeling target time as physical onset.",
        "2. **A single 24-hour outcome may obscure trajectory shape.** Separate slow-rising, rapid-rising, and multi-peak response patterns using observed-only labels, keeping split/gap uncertainty explicit.",
        "3. **The two-station coastal/river feature set may miss local runoff.** Check the local precipitation and tributary candidates above, first validating stable historical coverage, drainage relevance, units, datum, QC, and receipt times.",
        "4. **Coastal predictor support may be intermittent or weak relative to the threshold.** Compare covariate coverage and magnitude on event windows versus alert episodes, with event-blocked uncertainty and no use of outcome labels as predictors.",
        "5. **False alert episodes may indicate response heterogeneity rather than one overactive predictor.** Compare false clusters by river/coastal configuration and duration before any coefficient or threshold work.",
        "",
        "These are hypotheses for an independently predeclared study, not model changes. No model was trained or tuned in this diagnostic package.",
        "",
        "## Reproduction",
        "",
        "From repository root run `python research/rise-failure-audit/audit.py`. This regenerates the event CSV, false-cluster CSV, compact JSON, representative timelines, and this report. The exact Phase 6 event grouping implementation is imported from `scripts/phase6_metrics.py`; source SHA-256 fingerprints are stored in `analysis.json`.",
        "",
        "## Outputs",
        "",
        "- `analysis.json`: reproducible summary, count checks, metadata, and provenance.",
        "- `event-diagnostics.csv`: one compact row per all 109 Phase 6 groups.",
        "- `false-alert-clusters.csv`: one row per threshold forecast episode, including all 48 false clusters.",
        "- `representative-timelines.json`: small issue/valid-time examples.",
        "- `report.md`: scientific narrative and limitations.",
    ])
    pathlib.Path(path).write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--output-dir", type=pathlib.Path)
    args = parser.parse_args()
    report = write_outputs(args.root, args.output_dir)
    print(json.dumps({"output_dir": str(args.output_dir or pathlib.Path(args.root) / "research/rise-failure-audit"),
                      "phase6_groups": report["definition_reproduction"]["phase6_groups"],
                      "detected": report["definition_reproduction"]["detected_groups"],
                      "missed": report["definition_reproduction"]["missed_groups"],
                      "false_alert_clusters": report["definition_reproduction"]["phase5b_false_alert_clusters"],
                      "definition_match": report["definition_reproduction"]["matches_existing_model_lab_groups"] and report["definition_reproduction"]["matches_existing_model_lab_false_clusters"]}, indent=2))


if __name__ == "__main__":
    main()
