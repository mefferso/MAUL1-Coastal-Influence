"""Reproducible retrospective diagnostics and bounded-trend challenger study.

This module reads the existing Phase 5A/5B/historical archives and writes a
separate research report. It never writes forecasts, models, or verifications
to the frozen Phase 6 prospective archive.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import sys
import gzip
from collections import defaultdict

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import phase5a
import phase5b
import phase6_metrics

UTC = dt.timezone.utc
HORIZONS = (6, 12, 24)
EMBARGO_HOURS = 72
VALIDATION_GUARD_HOURS = 144
BOOTSTRAP_SEED = 20261024
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_BLOCK_HOURS = 168
CHALLENGER_FEATURES = ("maul1_stage_native_ft", "maul1_change_6h_ft")
CHALLENGER_METHOD = "bounded_damped_trend_ft"
METHODS = (
    ("persistence_ft", "Persistence"),
    ("maul1_only_ft", "Phase 5A MAUL1-only"),
    ("maul1_plus_coastal_ft", "Phase 5A coastal"),
    ("maul1_coastal_tidal", "Phase 5B coastal + tidal"),
    ("full_multivariable", "Phase 5B full multivariable"),
    ("bounded_damped_trend_ft", "Bounded damped-trend challenger"),
)
DEFAULT_CONFIG = {"shrink": 0.25, "cap_per_hour": 0.05}
CONFIGS = tuple({"shrink": shrink, "cap_per_hour": cap}
                for shrink in (0.10, 0.25, 0.50, 1.00)
                for cap in (0.01, 0.025, 0.05, 0.10))
FEATURES_FOR_MISSINGNESS = (
    "maul1_change_6h_ft", "denl1_log_discharge", "denl1_log_change_24h",
    "nwcl1_residual_mllw_ft", "nwcl1_residual_change_6h_ft",
    "nwcl1_wind_u_knots", "nwcl1_wind_v_knots",
    "mdll1_stage_change_24h_ft", "mchl1_stage_change_24h_native_ft",
)


def _iso(value: dt.datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json_number(value):
    return float(value) if value is not None and math.isfinite(float(value)) else None


def training_indices(rows, validation_start, embargo_hours=EMBARGO_HOURS):
    """Calibration-only rows whose targets end before the validation purge."""
    cutoff = validation_start - dt.timedelta(hours=embargo_hours)
    return [i for i, row in enumerate(rows)
            if row.get("split") == "calibration" and row.get("actual") is not None
            and row.get("target_time") is not None and row["target_time"] < cutoff
            and row.get("issue_time") is not None and row["issue_time"] < validation_start
            and row.get("maul1_stage_native_ft") is not None]


def load_lab_rows(root):
    """Join Phase 5B predictions onto issue features by exact issue/horizon/target identity."""
    root = pathlib.Path(root)
    rows_by_horizon, _ = phase5b._load_table(root)
    feature_rows = {}
    archive_path = root / "site/data/history/phase5b/predictions.csv.gz"
    with gzip.open(archive_path, "rt", newline="", encoding="utf-8") as stream:
        for prediction in csv.DictReader(stream):
            horizon = int(prediction["horizon_hours"])
            key = (prediction["issue_time_utc"], horizon, prediction["target_time_utc"])
            if key in feature_rows:
                raise ValueError(f"Duplicate Phase 5B issue/target key: {key}")
            feature_rows[key] = prediction
    phase5a_all = {}
    with gzip.open(root / "site/data/history/phase5a/predictions.csv.gz", "rt", newline="", encoding="utf-8") as stream:
        for prediction in csv.DictReader(stream):
            if prediction.get("split") not in ("calibration", "holdout"):
                continue
            key = (prediction["issue_time_utc"], int(prediction["horizon_hours"]), prediction["target_time_utc"])
            phase5a_all[key] = phase5b._num(prediction.get("maul1_all_ft"))
    source_columns = {
        "persistence_ft": "persistence_ft",
        "maul1_only_ft": "phase5a_maul1_only_ft",
        "maul1_plus_river_ft": "phase5a_river_ft",
        "maul1_plus_coastal_ft": "phase5a_coastal_ft",
        "maul1_periodic": "maul1_periodic",
        "maul1_astro_retrospective": "maul1_astro_retrospective",
        "maul1_coastal_tidal": "maul1_coastal_tidal",
        "full_multivariable": "full_multivariable",
        "gated_full": "gated_full",
    }
    for horizon, rows in rows_by_horizon.items():
        for row in rows:
            key = (_iso(row["issue_time"]), horizon, _iso(row["target_time"]))
            prediction = feature_rows.get(key)
            if prediction is None:
                raise ValueError(f"Missing Phase 5B prediction row for issue/target key: {key}")
            row["actual"] = phase5b._num(prediction.get("actual_native_gage_height_ft"))
            row["split"] = prediction.get("split")
            row["event_ids"] = [event for event in (prediction.get("event_ids") or "").split(";") if event]
            row["maul1_all_ft"] = phase5a_all.get(key)
            for name, column in source_columns.items():
                row[name] = phase5b._num(prediction.get(column))
    # Phase 5B's table excludes split-seam rows; its prediction archive keeps them for audit.
    return rows_by_horizon


def damped_trend(stage, change_6h, horizon, config):
    """Issue-time MAUL1-only trend; absent changes fall back to persistence."""
    if stage is None or not math.isfinite(float(stage)):
        return None
    if change_6h is None or not math.isfinite(float(change_6h)):
        return float(stage)
    cap = float(config["cap_per_hour"])
    slope = max(-cap, min(cap, float(change_6h) / 6.0))
    return float(stage) + slope * float(config["shrink"]) * int(horizon)


def challenger_prediction(row, horizon, config):
    """Read only the fixed feature contract; future target/forcing fields are ignored."""
    return damped_trend(row.get("maul1_stage_native_ft"),
                        row.get("maul1_change_6h_ft"), horizon, config)


def paired_rows(rows, methods):
    """Keep common eligible cases and require unique issue/target identity."""
    selected, seen = [], set()
    for row in rows:
        if row.get("actual") is None or any(row.get(name) is None for name in methods):
            continue
        issue, target = row.get("issue_time"), row.get("target_time")
        if issue is None or target is None:
            continue
        identity = (issue, target)
        if identity in seen:
            continue
        seen.add(identity)
        selected.append(row)
    return selected


def metrics(actual, forecast, persistence=None):
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    valid = np.isfinite(actual) & np.isfinite(forecast)
    if persistence is not None:
        persistence = np.asarray(persistence, dtype=float)
        valid &= np.isfinite(persistence)
    if not valid.any():
        return {"n": 0, "mae_ft": None, "rmse_ft": None, "bias_ft": None,
                "skill_vs_persistence": None}
    error = forecast[valid] - actual[valid]
    mae = float(np.mean(np.abs(error)))
    p_mae = (float(np.mean(np.abs(persistence[valid] - actual[valid])))
             if persistence is not None else None)
    skill = 1.0 - mae / p_mae if p_mae is not None and p_mae > 0 else None
    return {"n": int(valid.sum()), "mae_ft": mae,
            "rmse_ft": float(np.sqrt(np.mean(error * error))),
            "bias_ft": float(np.mean(error)), "skill_vs_persistence": skill}


def block_bootstrap_mae_difference(actual, challenger, baseline, seed=BOOTSTRAP_SEED,
                                   replicates=BOOTSTRAP_REPLICATES, block=BOOTSTRAP_BLOCK_HOURS):
    """Bootstrap baseline MAE minus challenger MAE in ordered circular blocks."""
    actual = np.asarray(actual, dtype=float)
    challenger = np.asarray(challenger, dtype=float)
    baseline = np.asarray(baseline, dtype=float)
    valid = np.isfinite(actual) & np.isfinite(challenger) & np.isfinite(baseline)
    actual, challenger, baseline = actual[valid], challenger[valid], baseline[valid]
    n = len(actual)
    if n < 2:
        return {"n": n, "replicates": 0, "status": "insufficient",
                "improvement_ft_ci95": [None, None]}
    rng = np.random.default_rng(seed)
    length = min(int(block), n)
    block_count = math.ceil(n / length)
    estimates = np.empty(replicates, dtype=float)
    starts = np.arange(n)
    offsets = np.arange(length)
    for i in range(replicates):
        indexes = np.concatenate([(start + offsets) % n
                                  for start in rng.choice(starts, block_count)])[:n]
        estimates[i] = (np.mean(np.abs(baseline[indexes] - actual[indexes]))
                        - np.mean(np.abs(challenger[indexes] - actual[indexes])))
    return {"n": n, "replicates": replicates, "block_hours": block,
            "seed": seed, "status": "computed",
            "improvement_ft_ci95": [float(np.quantile(estimates, .025)),
                                     float(np.quantile(estimates, .975))]}


def event_group_metrics(rows, method):
    groups = defaultdict(list)
    for row in rows:
        if row.get("actual") is None or row.get(method) is None:
            continue
        error = float(row[method]) - float(row["actual"])
        for event in set(row.get("event_ids") or ()):
            groups[event].append(error)
    events = {event: {"forecast_count": len(errors),
                      "mae_ft": float(np.mean(np.abs(errors))),
                      "bias_ft": float(np.mean(errors)),
                      "underforecast_fraction": float(np.mean(np.asarray(errors) < 0))}
              for event, errors in sorted(groups.items())}
    return {"event_count": len(events), "overlapping_forecast_rows_are_not_independent": True,
            "events": events}


def phase6_qualifying_rise_summary(rows, method):
    """Apply Phase 6's outcome-defined 24h rise grouping to the historical 24h horizon."""
    records = []
    for row in rows:
        stage, actual, forecast = (row.get("maul1_stage_native_ft"), row.get("actual"), row.get(method))
        if stage is None or actual is None:
            continue
        records.append({
            "actual_issue_time_utc": _iso(row["issue_time"]),
            "valid_time_utc": _iso(row["target_time"]),
            "observed_change_ft": actual - stage,
            "forecast_change_ft": forecast - stage if forecast is not None else None,
        })
    summary = phase6_metrics.summarize_qualifying_events(records, threshold_ft=.50, separation_hours=24)
    if summary.get("status") == "computed":
        detected_leads = [event["lead_to_first_qualifying_target_hours"]
                          for event in summary.get("events", []) if event.get("detected")
                          and event.get("lead_to_first_qualifying_target_hours") is not None]
        summary["detection_rate"] = (summary["detected_events"] / summary["event_count"]
                                     if summary["event_count"] else None)
        summary["median_lead_to_first_qualifying_verification_target_hours"] = (
            float(np.median(detected_leads)) if detected_leads else None)
        summary["interpretation"] = "Lead to first qualifying verification target, not physical water-level rise onset."
    return summary


def _choose_config(previous_oof, horizon):
    eligible = [row for row in previous_oof if row.get("actual") is not None
                and row.get("maul1_change_6h_ft") is not None
                and row.get("maul1_stage_native_ft") is not None]
    if len(eligible) < 500:
        return dict(DEFAULT_CONFIG)
    scored = []
    for config in CONFIGS:
        errors = [abs(damped_trend(row["maul1_stage_native_ft"],
                                   row["maul1_change_6h_ft"], horizon, config) - row["actual"])
                  for row in eligible]
        scored.append((float(np.mean(errors)), config["shrink"], config["cap_per_hour"], config))
    return dict(min(scored, key=lambda item: item[:3])[3])


def challenger_predictions(rows, horizon):
    """Nested calibration-fold setting selection, then one frozen holdout setting."""
    oof, folds = [], []
    for year in range(2017, 2023):
        start = dt.datetime(year, 1, 1, tzinfo=UTC)
        end = dt.datetime(year + 1, 1, 1, tzinfo=UTC)
        train = training_indices(rows, start)
        validation = [row for row in rows if row.get("split") == "calibration"
                      and row.get("actual") is not None
                      and start + dt.timedelta(hours=VALIDATION_GUARD_HOURS)
                      <= row.get("issue_time", start - dt.timedelta(seconds=1)) < end]
        config = _choose_config(oof, horizon)
        for row in validation:
            prediction = challenger_prediction(row, horizon, config)
            if prediction is not None:
                row[CHALLENGER_METHOD] = prediction
                oof.append(row)
        folds.append({"validation_year": year, "training_n": len(train),
                      "validation_n": len(validation), "config_from_earlier_folds": config,
                      "training_target_cutoff_exclusive_utc": _iso(start - dt.timedelta(hours=EMBARGO_HOURS)),
                      "validation_start_inclusive_utc": _iso(start + dt.timedelta(hours=VALIDATION_GUARD_HOURS))})
    final_config = _choose_config(oof, horizon)
    holdout = [row for row in rows if row.get("split") == "holdout"]
    for row in holdout:
        row[CHALLENGER_METHOD] = challenger_prediction(row, horizon, final_config)
    return final_config, folds, oof, holdout


def _calc_metrics(rows, method):
    paired = paired_rows(rows, ("persistence_ft", method))
    eligible = [row for row in rows if row.get("actual") is not None
                and row.get("maul1_stage_native_ft") is not None
                and row.get("persistence_ft") is not None]
    result = metrics([row["actual"] for row in paired], [row[method] for row in paired],
                     [row["persistence_ft"] for row in paired])
    result["eligible_issue_target_rows"] = len(eligible)
    result["available_prediction_rows"] = len(paired)
    result["abstention_n"] = max(0, len(eligible) - len(paired))
    result["abstention_fraction"] = result["abstention_n"] / len(eligible) if eligible else None
    return result


def _metric_table(rows):
    table = {}
    for name, label in METHODS:
        table[name] = {"label": label, **_calc_metrics(rows, name)}
    return table


def _strata(rows, horizon):
    calibration = [row for row in rows if row.get("split") == "calibration"
                   and row.get("denl1_log_discharge") is not None]
    q90 = float(np.quantile([row["denl1_log_discharge"] for row in calibration], .9)) if calibration else None
    predicates = {
        "all paired cases": lambda row: True,
        "qualifying event windows (catalog)": lambda row: bool(row.get("event_ids")),
        "quiet or falling target": lambda row: row.get("actual") is not None and row.get("maul1_stage_native_ft") is not None and row["actual"] <= row["maul1_stage_native_ft"],
        "high DENL1 flow (calibration q90)": lambda row: q90 is not None and row.get("denl1_log_discharge") is not None and row["denl1_log_discharge"] >= q90,
        "NWCL1 residual setup >= 0.50 ft MLLW": lambda row: row.get("nwcl1_residual_mllw_ft") is not None and row["nwcl1_residual_mllw_ft"] >= .5,
        "NWCL1 wind speed >= 5 knots": lambda row: row.get("nwcl1_wind_u_knots") is not None and row.get("nwcl1_wind_v_knots") is not None and math.hypot(row["nwcl1_wind_u_knots"], row["nwcl1_wind_v_knots"]) >= 5,
        "MDLL1 24-hour rise >= 0.10 ft": lambda row: row.get("mdll1_stage_change_24h_ft") is not None and row["mdll1_stage_change_24h_ft"] >= .1,
    }
    results = {}
    for label, predicate in predicates.items():
        selected = [row for row in rows if predicate(row)]
        results[label] = {"n_available_before_pairing": len(selected),
                          "models": _metric_table(selected)}
    results["definition_metadata"] = {
        "high_DENL1_log_discharge_calibration_q90": q90,
        "event_labels_are_verification_only": True,
        "covariates_are_valid_time_issue_approximations_without_receipt_time_proof": True,
    }
    return results


def _year_season(rows):
    groups = defaultdict(list)
    for row in rows:
        issue = row["issue_time"]
        groups[f"year:{issue.year}"].append(row)
        season = ("winter" if issue.month in (12, 1, 2) else
                  "spring" if issue.month in (3, 4, 5) else
                  "summer" if issue.month in (6, 7, 8) else "fall")
        groups[f"season:{season}"].append(row)
    return {name: _metric_table(values) for name, values in sorted(groups.items())}


def _false_alarm_diagnostics(rows):
    """Target-window confusion and clustered 24h alert episodes; rows are not independent."""
    output = {}
    target_rows = [row for row in rows if row.get("actual") is not None
                   and row.get("maul1_stage_native_ft") is not None]
    actual_rise = [row["actual"] - row["maul1_stage_native_ft"] >= .5 for row in target_rows]
    for method, label in METHODS:
        if method == "persistence_ft":
            predicted = [row[method] - row["maul1_stage_native_ft"] >= .5 for row in target_rows]
        else:
            predicted = [row.get(method) is not None and row[method] - row["maul1_stage_native_ft"] >= .5 for row in target_rows]
        available = [i for i, row in enumerate(target_rows) if row.get(method) is not None]
        tp = sum(actual_rise[i] and predicted[i] for i in available)
        fp = sum(not actual_rise[i] and predicted[i] for i in available)
        fn = sum(actual_rise[i] and not predicted[i] for i in available)
        alerts = [(target_rows[i]["issue_time"], not actual_rise[i]) for i in available if predicted[i]]
        clusters, false_clusters = 0, 0
        previous = None
        cluster_had_response = False
        for issue, is_false in alerts:
            if previous is None or issue - previous > dt.timedelta(hours=24):
                if previous is not None:
                    false_clusters += int(not cluster_had_response)
                clusters += 1
                cluster_had_response = False
            cluster_had_response |= not is_false
            previous = issue
        if previous is not None:
            false_clusters += int(not cluster_had_response)
        output[method] = {"label": label, "paired_target_windows_n": len(available),
                           "threshold_ft": .50, "true_positive_target_windows": tp,
                           "false_positive_target_windows": fp, "missed_rise_target_windows": fn,
                           "alert_episode_clusters": clusters,
                           "false_alert_episode_clusters": false_clusters,
                           "overlapping_hourly_target_windows_are_correlated": True}
    return output


def trajectory_diagnostics(rows_by_horizon):
    """Direction accuracy and threshold-time error on aligned forecasts from one issue."""
    output = {}
    by_issue = defaultdict(dict)
    for horizon in HORIZONS:
        for row in rows_by_horizon[horizon]:
            if row.get("split") != "holdout":
                continue
            by_issue[row["issue_time"]][horizon] = row
    for method, label in METHODS:
        correct = total = rising_underforecast = rising_n = 0
        timing_errors, timing_misses, timing_cases = [], 0, 0
        for horizons in by_issue.values():
            observed_crossing, predicted_crossing = None, None
            for horizon in HORIZONS:
                row = horizons.get(horizon)
                if not row or row.get("actual") is None or row.get("maul1_stage_native_ft") is None or row.get(method) is None:
                    continue
                actual_change = row["actual"] - row["maul1_stage_native_ft"]
                forecast_change = row[method] - row["maul1_stage_native_ft"]
                if abs(actual_change) >= .02:
                    total += 1
                    correct += int((actual_change > 0) == (forecast_change > 0))
                if actual_change >= .02:
                    rising_n += 1
                    rising_underforecast += int(forecast_change < actual_change)
                if actual_change >= .5 and observed_crossing is None:
                    observed_crossing = horizon
                if forecast_change >= .5 and predicted_crossing is None:
                    predicted_crossing = horizon
            if observed_crossing is not None:
                timing_cases += 1
                if predicted_crossing is None:
                    timing_misses += 1
                else:
                    timing_errors.append(abs(predicted_crossing - observed_crossing))
        output[method] = {
            "label": label, "direction_cases_abs_change_at_least_0_02_ft": total,
            "direction_correct_fraction": correct / total if total else None,
            "underforecast_fraction_on_rising_targets": rising_underforecast / rising_n if rising_n else None,
            "rising_target_n": rising_n,
            "threshold_timing_definition": "Within one issue's 6/12/24-hour trajectory, first horizon at which observed or predicted rise from the issue stage reaches 0.50 ft. This is a verification threshold, not physical rise onset.",
            "threshold_timing_eligible_issue_count": timing_cases,
            "threshold_timing_missed_by_forecast_n": timing_misses,
            "mean_absolute_horizon_timing_error_hours": float(np.mean(timing_errors)) if timing_errors else None,
            "timing_matched_issue_count": len(timing_errors),
        }
    return output


def _feature_missingness(rows):
    output = {}
    for name in FEATURES_FOR_MISSINGNESS:
        missing = sum(row.get(name) is None for row in rows)
        output[name] = {"missing_n": missing, "available_n": len(rows) - missing,
                        "eligible_n": len(rows),
                        "missing_fraction": missing / len(rows) if rows else None}
    return output


def _select_case_rows(holdout_rows):
    valid = [row for row in holdout_rows if row.get("actual") is not None
             and row.get("maul1_stage_native_ft") is not None
             and row.get("bounded_damped_trend_ft") is not None
             and row.get("maul1_coastal_tidal") is not None]
    rising = [row for row in valid if row["actual"] - row["maul1_stage_native_ft"] >= .5]
    quiet = [row for row in valid if row["actual"] <= row["maul1_stage_native_ft"]]
    coastal = [row for row in valid if row.get("nwcl1_residual_mllw_ft") is not None
               and row["nwcl1_residual_mllw_ft"] >= .5]
    def err(row, method):
        return row[method] - row["actual"]
    choices, seen = [], set()
    def choose(label, candidates, score, reverse=False):
        for row in sorted(candidates, key=score, reverse=reverse):
            identity = (row["issue_time"], row["target_time"])
            if identity not in seen:
                seen.add(identity); choices.append((label, row)); return
    choose("Largest challenger underforecast during a >=0.50 ft target rise", rising,
           lambda row: err(row, "bounded_damped_trend_ft"))
    choose("Largest challenger overforecast during a quiet/falling target", quiet,
           lambda row: err(row, "bounded_damped_trend_ft"), reverse=True)
    choose("Largest coastal-model error with NWCL1 residual setup", coastal,
           lambda row: abs(err(row, "maul1_coastal_tidal")), reverse=True)
    return choices


def _case_studies(rows_by_horizon):
    base = rows_by_horizon[6]
    chosen = _select_case_rows(rows_by_horizon[24])
    cases = []
    for index, (label, anchor) in enumerate(chosen, 1):
        center = anchor["issue_time"]
        start = center - dt.timedelta(hours=36)
        end = center + dt.timedelta(hours=37)
        observed_end = end + dt.timedelta(hours=24)
        observed = []
        seen = set()
        for row in base:
            valid = row["target_time"]
            stage = row.get("actual")
            if row.get("split") == "holdout" and start <= valid < observed_end and stage is not None and valid not in seen:
                observed.append({"time_utc": _iso(valid), "stage_ft": stage})
                seen.add(valid)
        forecast_series = {}
        for horizon, records in rows_by_horizon.items():
            points = []
            for row in records:
                if not start <= row["issue_time"] < end:
                    continue
                values = {name: _json_number(row.get(name)) for name, _ in METHODS}
                if not any(value is not None for value in values.values()):
                    continue
                points.append({"issue_time_utc": _iso(row["issue_time"]),
                               "valid_time_utc": _iso(row["target_time"]),
                               "observed_stage_ft": _json_number(row.get("actual")),
                               "forecasts": values})
            forecast_series[str(horizon)] = points
        cases.append({"case_id": f"case-{index}", "label": label,
                      "selection": "Algorithmically selected from reused holdout errors/outcomes; illustration only.",
                      "anchor_issue_time_utc": _iso(center),
                      "anchor_valid_time_utc": _iso(anchor["target_time"]),
                      "target_rise_from_issue_ft": anchor["actual"] - anchor["maul1_stage_native_ft"],
                      "issue_time_features": {name: _json_number(anchor.get(name)) for name in (
                          "maul1_change_6h_ft", "denl1_log_discharge", "nwcl1_residual_mllw_ft",
                          "nwcl1_wind_u_knots", "nwcl1_wind_v_knots", "mdll1_stage_change_24h_ft")},
                      "observations": observed, "forecasts_by_horizon": forecast_series})
    return cases


def _baseline_parity(root, reproduction_dir, committed_a, committed_b):
    if reproduction_dir is None:
        return {"status": "not_run", "reason": "No temporary reproduction output directory supplied."}
    reproduction_dir = pathlib.Path(reproduction_dir)
    checks = []
    generated_a = json.loads((reproduction_dir / "phase5a/summary.json").read_text())
    generated_b = json.loads((reproduction_dir / "phase5b/summary.json").read_text())
    a_methods = ("persistence", "stage_trend", "maul1_only", "maul1_plus_river",
                 "maul1_plus_coastal", "maul1_all")
    b_methods = ("persistence_ft", "maul1_only_ft", "maul1_plus_river_ft",
                 "maul1_plus_coastal_ft", "maul1_periodic", "maul1_astro_retrospective",
                 "maul1_coastal_tidal", "full_multivariable", "gated_full")
    for h in HORIZONS:
        comparisons = [("phase5a", name,
                        committed_a["holdout_results"][str(h)]["methods"][name],
                        generated_a["holdout_results"][str(h)]["methods"][name])
                       for name in a_methods]
        comparisons.extend(("phase5b", name,
                            committed_b["holdout_results"][str(h)][name],
                            generated_b["holdout_results"][str(h)][name])
                           for name in b_methods)
        for family, method, old, new in comparisons:
            deltas = {}
            for key in ("n", "mae_ft", "rmse_ft", "bias_ft", "mae_skill_vs_persistence", "skill_vs_persistence"):
                left, right = old.get(key), new.get(key)
                if left is not None or right is not None:
                    delta = abs(float(left) - float(right)) if left is not None and right is not None else math.inf
                    deltas[key] = delta
                    if delta > 1e-8:
                        raise ValueError(f"{family} reproduction mismatch {method} {h} {key}: {left} != {right}")
            checks.append({"horizon_hours": h, "model_family": family, "method": method,
                           "status": "matched", "absolute_differences": deltas})
    return {"status": "matched", "tolerance": 1e-8, "checks": checks,
            "temporary_output_only": True}


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def build_report(root=ROOT, output=None, reproduction_dir=None):
    root = pathlib.Path(root).resolve()
    output = pathlib.Path(output) if output else root / "site/data/research/model-lab.json"
    rows_by_horizon = load_lab_rows(root)
    committed_a = json.loads((root / "site/data/history/phase5a/summary.json").read_text())
    committed_b = json.loads((root / "site/data/history/phase5b/summary.json").read_text())
    challenge, folds, oof_by_horizon, holdout_by_horizon = {}, {}, {}, {}
    for horizon in HORIZONS:
        config, fold_results, oof, holdout = challenger_predictions(rows_by_horizon[horizon], horizon)
        challenge[str(horizon)] = config
        folds[str(horizon)] = fold_results
        oof_by_horizon[horizon] = oof
        holdout_by_horizon[horizon] = holdout

    horizons = {}
    for horizon in HORIZONS:
        holdout = holdout_by_horizon[horizon]
        pairs = paired_rows(holdout, tuple(name for name, _ in METHODS))
        table = _metric_table(pairs)
        uncertainty = {}
        for method, _ in METHODS:
            compare = paired_rows(holdout, ("persistence_ft", method))
            uncertainty[method] = block_bootstrap_mae_difference(
                [row["actual"] for row in compare], [row[method] for row in compare],
                [row["persistence_ft"] for row in compare],
                seed=BOOTSTRAP_SEED + horizon + sum(map(ord, method)))
        challenger_pairs = paired_rows(holdout_by_horizon[horizon],
                                       ("maul1_only_ft", "bounded_damped_trend_ft"))
        uncertainty["bounded_damped_trend_ft"]["vs_maul1_only"] = block_bootstrap_mae_difference(
            [row["actual"] for row in challenger_pairs],
            [row["bounded_damped_trend_ft"] for row in challenger_pairs],
            [row["maul1_only_ft"] for row in challenger_pairs],
            seed=BOOTSTRAP_SEED + horizon + sum(map(ord, "vs_maul1_only")))
        horizons[str(horizon)] = {
            "paired_sample_n": len(pairs), "metrics": table,
            "improvement_vs_persistence_bootstrap": uncertainty,
            "annual_and_seasonal": _year_season(pairs),
            "regimes": _strata(holdout, horizon),
            "event_groups": {method: event_group_metrics(holdout, method)
                             for method in ("persistence_ft", "maul1_only_ft", "maul1_plus_coastal_ft",
                                            "maul1_coastal_tidal", "full_multivariable", "bounded_damped_trend_ft")},
            "trajectory_diagnostics": trajectory_diagnostics(holdout_by_horizon),
            "underforecast_and_false_alarm": _false_alarm_diagnostics(holdout) if horizon == 24 else None,
            "issue_feature_missingness": _feature_missingness(holdout),
        }

    predictor_ablations = {}
    for horizon in HORIZONS:
        rows = rows_by_horizon[horizon]
        held = [row for row in rows if row.get("split") == "holdout"]
        ablation_methods = ("persistence_ft", "maul1_only_ft", "maul1_plus_river_ft",
                            "maul1_plus_coastal_ft", "maul1_all_ft", "maul1_periodic",
                            "maul1_coastal_tidal", "full_multivariable", "maul1_astro_retrospective")
        shared = paired_rows(held, ablation_methods)
        ablation_scores = {
            name: metrics([row["actual"] for row in shared], [row[name] for row in shared],
                          [row["persistence_ft"] for row in shared])
            for name in ablation_methods}
        maul_score = ablation_scores["maul1_only_ft"]["mae_ft"]
        persistence_score = ablation_scores["persistence_ft"]["mae_ft"]
        for name, score in ablation_scores.items():
            score["mae_delta_vs_maul1_only_ft"] = (score["mae_ft"] - maul_score
                                                   if score["mae_ft"] is not None and maul_score is not None else None)
            score["mae_delta_vs_persistence_ft"] = (score["mae_ft"] - persistence_score
                                                      if score["mae_ft"] is not None and persistence_score is not None else None)
        predictor_ablations[str(horizon)] = {
            "paired_sample_n": len(shared),
            "maul1_additive_value_and_degradation": ablation_scores,
            "interpretation": "Same issue/target rows for every ablation. NOAA astronomical valid-time prediction is retrospective-only because no capture-time ledger proves availability.",
        }

    primary = {}
    for horizon in HORIZONS:
        primary[str(horizon)] = {}
        for method, _ in METHODS:
            common = paired_rows(holdout_by_horizon[horizon], ("persistence_ft", method))
            primary[str(horizon)][method] = metrics([r["actual"] for r in common],
                [r[method] for r in common], [r["persistence_ft"] for r in common])
            primary[str(horizon)][method]["paired_improvement_vs_persistence_ft"] = (
                primary[str(horizon)][method]["mae_ft"] - primary[str(horizon)]["persistence_ft"]["mae_ft"]
                if primary[str(horizon)][method]["mae_ft"] is not None else None)
        challenger = primary[str(horizon)]["bounded_damped_trend_ft"]
        base = primary[str(horizon)]["persistence_ft"]
        single = primary[str(horizon)]["maul1_only_ft"]
        challenger["beats_persistence"] = (challenger["mae_ft"] is not None and base["mae_ft"] is not None
                                             and challenger["mae_ft"] < base["mae_ft"])
        challenger["beats_maul1_only"] = (challenger["mae_ft"] is not None and single["mae_ft"] is not None
                                           and challenger["mae_ft"] < single["mae_ft"])

    # Concise strongest failure modes by independent catalog event, not by hourly row count.
    event_failures = {}
    for horizon in HORIZONS:
        events = horizons[str(horizon)]["event_groups"]["maul1_coastal_tidal"]["events"]
        event_failures[str(horizon)] = sorted(
            [{"event_id": key, **value} for key, value in events.items()],
            key=lambda item: item["bias_ft"])[:10]

    cases = _case_studies(holdout_by_horizon)
    timestamps = [row["target_time"] for rows in rows_by_horizon.values() for row in rows
                  if row.get("actual") is not None]
    source_paths = [root / "scripts/phase5a.py", root / "scripts/phase5b.py",
                    root / "scripts/phase6_models.py", root / "scripts/phase6_metrics.py",
                    root / "scripts/model_lab.py", root / "docs/model-lab-methodology.md",
                    root / "docs/phase5a-methodology.md", root / "docs/phase5b-methodology.md",
                    root / "docs/phase6-methodology.md",
                    root / "site/data/history/phase5a/predictions.csv.gz",
                    root / "site/data/history/phase5a/features.csv.gz",
                    root / "site/data/history/phase5b/predictions.csv.gz",
                    root / "site/data/history/phase5a/summary.json",
                    root / "site/data/history/phase5b/summary.json",
                    root / "site/data/history/phase3b/response-events.csv",
                    root / "site/data/history/phase3b/validation.json"]
    for path in sorted((root / "site/data/history/hourly").glob("*.json.gz")):
        source_paths.append(path)
    parity = _baseline_parity(root, reproduction_dir, committed_a, committed_b)
    archive_start = json.loads((root / "site/data/history/phase5a/summary.json").read_text())["archive_first_observation_utc"]
    archive_end = json.loads((root / "site/data/history/phase5a/summary.json").read_text())["archive_last_observation_utc"]
    report = {
        "schema": "maul1.model-lab.report.v1",
        "title": "MAUL1 Model Diagnostics & Challenger Lab",
        "status": "Research / Shadow Evaluation / Not Operational",
        "evidence_label": "Retrospective / Development Evidence",
        "summary": {
            "archive_first_observation_utc": archive_start,
            "archive_last_observation_utc": archive_end,
            "verification_period": "2023 onward; previously inspected and reused for historical development/evaluation, not a pristine test set",
            "calibration_period": committed_b.get("calibration"),
            "phase5a_baseline_model_version": "historical Phase 5A published estimates; frozen Phase 6 artifacts are separate",
            "phase5b_baseline_model_version": "historical Phase 5B published estimates; retrospective-only astronomy remains segregated",
            "horizons_hours": list(HORIZONS),
            "all_rows_are_historical_hindcasts": True,
            "receipt_time_availability": "Original source receipt times are not archived; completed valid-time bins are only an as-of approximation.",
            "prospective_archive_modified": False,
            "conclusion": "See per-horizon paired challenger results; historical improvements do not establish prospective skill.",
        },
        "baseline_reproduction": parity,
        "challenger_protocol": {
            "method": CHALLENGER_METHOD, "model_version": "model-lab-bounded-damped-trend-v1",
            "features": list(CHALLENGER_FEATURES),
            "formula": "stage + horizon_hours * shrink * clip(MAUL1_6h_change_ft / 6, -cap_per_hour, +cap_per_hour)",
            "config_by_horizon": challenge,
            "candidate_menu": list(CONFIGS), "nested_forward_calibration_folds": folds,
            "training_purge_hours": EMBARGO_HOURS, "validation_guard_hours": VALIDATION_GUARD_HOURS,
            "missing_issue_feature": "fall back to persistence; no missing prediction is scored as zero",
            "no_NOAA_astro_or_MCHL1": True,
            "status": "historical challenger only; not issued prospectively",
        },
        "horizons": horizons,
        "phase6_qualifying_rise_groups_24h": {
            method: phase6_qualifying_rise_summary(holdout_by_horizon[24], method)
            for method, _ in METHODS},
        "challenger_headline": primary,
        "predictor_ablations": predictor_ablations,
        "worst_event_failures_phase5b_coastal_tidal": event_failures,
        "case_studies": cases,
        "promotion_criteria": {
            "criteria": ["paired MAE beats persistence and MAUL1-only", "paired seven-day block-bootstrap 95% improvement interval excludes zero", "robust across years, seasons, and independent event groups", "coverage and abstention rates are acceptable", "separate prospective shadow protocol and isolated archive are reviewed"],
            "challenger_promoted": False,
            "prospective_issuance_created": False,
        },
        "provenance": {
            "source": "committed Phase 5A/5B report and feature archives plus site/data/history/hourly/*.json.gz",
            "source_sha256": {str(path.relative_to(root)): _sha(path) for path in source_paths},
            "hourly_archive_months": len(list((root / "site/data/history/hourly").glob("*.json.gz"))),
            "source_time_basis": "UTC valid time; source receipt times unavailable",
            "target": "USGS MAUL1 station 07380215 parameter 00065, ft, native gage height",
            "navigation_and_phase6_artifacts_modified": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return report


def write_markdown(report, path):
    path = pathlib.Path(path)
    h = report["challenger_headline"]
    lines = ["# Model Lab findings", "", "**Research / Shadow Evaluation / Not Operational.**",
             "**Retrospective / Development Evidence.** The 2023 onward holdout has already been inspected and is not an independent prospective test.", "",
             "## Historical challenger results", "",
             "The bounded damped-trend challenger used only the latest completed MAUL1 6-hour change. Settings were selected using nested forward calibration folds ending before each validation block; the final settings were frozen before applying them to the reused 2023+ historical benchmark. These are valid-time hindcasts; source receipt-time availability is not archived.", "",
             "| Horizon | Paired n | Persistence MAE | Challenger MAE | Challenger skill vs persistence | Challenger MAE − persistence | Challenger MAE − MAUL1-only | Improvement vs MAUL1-only 95% block interval | Beats both? |", "|---:|---:|---:|---:|---:|---:|---:|---:|:---:|"]
    for horizon in HORIZONS:
        current = h[str(horizon)]
        p = current["persistence_ft"]; c = current["bounded_damped_trend_ft"]; m = current["maul1_only_ft"]
        fmt = lambda value: "—" if value is None else f"{value:.4f}"
        ci = report["horizons"][str(horizon)]["improvement_vs_persistence_bootstrap"]["bounded_damped_trend_ft"]["vs_maul1_only"]["improvement_ft_ci95"]
        ci_text = f"{fmt(ci[0])} to {fmt(ci[1])} ft" if ci[0] is not None else "Unavailable"
        lines.append(f"| {horizon} h | {c['n']:,} | {fmt(p['mae_ft'])} ft | {fmt(c['mae_ft'])} ft | {fmt(c['skill_vs_persistence'])} | {fmt(c['mae_ft'] - p['mae_ft'])} ft | {fmt(c['mae_ft'] - m['mae_ft'])} ft | {ci_text} | {'Yes' if c['beats_persistence'] and c['beats_maul1_only'] else 'No'} |")
    lines.extend(["", "Positive MAE differences mean the challenger is worse.", "",
                  "## Reproduced model benchmark", "",
                  "These five methods were compared on the same eligible rows within each horizon after regenerating the Phase 5A and Phase 5B reports into temporary directories. The 2023+ period is reused historical evidence.", "",
                  "| Model | 6h MAE (ft) / skill | 12h MAE (ft) / skill | 24h MAE (ft) / skill |", "|---|---:|---:|---:|"])
    model_rows = (("persistence_ft", "Persistence"), ("maul1_only_ft", "Phase 5A MAUL1-only"),
                  ("maul1_plus_coastal_ft", "Phase 5A coastal"),
                  ("maul1_coastal_tidal", "Phase 5B coastal + tidal"),
                  ("full_multivariable", "Phase 5B full multivariable"))
    for key, label in model_rows:
        values = []
        for horizon in HORIZONS:
            current = report["horizons"][str(horizon)]["metrics"][key]
            score = "Unavailable" if current["mae_ft"] is None else f"{current['mae_ft']:.4f} / {current['skill_vs_persistence']:.1%}"
            values.append(score)
        lines.append(f"| {label} | {values[0]} | {values[1]} | {values[2]} |")
    lines.extend(["", "## Predictor-family ablations", "",
                  "Same-row MAE deltas below compare each Phase 5A/5B family with MAUL1-only; negative values improve MAE. The 2023+ holdout is reused development/evaluation evidence.", "",
                  "| Horizon | Model family | Paired n | MAE (ft) | Δ MAE vs MAUL1-only (ft) |", "|---:|---|---:|---:|---:|"])
    ablation_names = (("maul1_only_ft", "MAUL1-only"), ("maul1_plus_river_ft", "MAUL1 + DENL1 river"),
                      ("maul1_plus_coastal_ft", "MAUL1 + coastal observations"),
                      ("maul1_all_ft", "MAUL1 + all Phase 5A context"),
                      ("maul1_coastal_tidal", "MAUL1 + coastal + UTC harmonics"),
                      ("full_multivariable", "Full multivariable"),
                      ("maul1_astro_retrospective", "NOAA future-valid retrospective sensitivity †"))
    for horizon in HORIZONS:
        scores = report["predictor_ablations"][str(horizon)]["maul1_additive_value_and_degradation"]
        for key, label in ablation_names:
            score = scores[key]
            delta = "—" if score["mae_delta_vs_maul1_only_ft"] is None else f"{score['mae_delta_vs_maul1_only_ft']:+.4f}"
            mae = "—" if score["mae_ft"] is None else f"{score['mae_ft']:.4f}"
            lines.append(f"| {horizon} h | {label} | {score['n']:,} | {mae} | {delta} |")
    alert = report["horizons"]["24"]["underforecast_and_false_alarm"]["bounded_damped_trend_ft"]
    rise_groups = report["phase6_qualifying_rise_groups_24h"]
    lines.extend(["", "### Phase 6 independent qualifying-rise groups", "",
                  "The existing Phase 6 rule groups outcome-defined 24-hour rises ≥0.50 ft when qualifying target times are no more than 24 hours apart. Lead is to the first qualifying verification target, not physical onset.", "",
                  "| Model | Independent rise groups | Detected / missed | Detection fraction | Median lead to first qualifying verification target |", "|---|---:|---:|---:|---:|"])
    phase6_model_rows = model_rows + (("bounded_damped_trend_ft", "Bounded damped-trend challenger"),)
    for key, label in phase6_model_rows:
        result = rise_groups[key]
        if result["status"] != "computed":
            lines.append(f"| {label} | {result['event_count']} | Skill withheld (<5 groups) | — | — |")
        else:
            lead = "—" if result["median_lead_to_first_qualifying_verification_target_hours"] is None else f"{result['median_lead_to_first_qualifying_verification_target_hours']:.1f} h"
            lines.append(f"| {label} | {result['event_count']} | {result['detected_events']} / {result['missed_events']} | {result['detection_rate']:.1%} | {lead} |")
    lines.extend(["", f"The 24-hour trend challenger flagged **{alert['true_positive_target_windows']}** observed ≥0.50 ft target rises and missed **{alert['missed_rise_target_windows']:,}** such overlapping target windows. These are correlated hourly windows; grouped event metrics are reported separately. The candidate did not beat MAUL1-only at 6, 12, or 24 hours (6h: {fmt(h['6']['bounded_damped_trend_ft']['mae_ft'])} vs {fmt(h['6']['maul1_only_ft']['mae_ft'])} ft; 12h: {fmt(h['12']['bounded_damped_trend_ft']['mae_ft'])} vs {fmt(h['12']['maul1_only_ft']['mae_ft'])} ft; 24h: {fmt(h['24']['bounded_damped_trend_ft']['mae_ft'])} vs {fmt(h['24']['maul1_only_ft']['mae_ft'])} ft). **No challenger is promoted.**", "",
                  "† NOAA future-valid prediction is retrospective-only without capture-time evidence; it is not an eligible causal feature.", "",
                  "The report JSON includes paired MAE for persistence, MAUL1-only, river-only addition, coastal addition, all Phase 5A families, causal harmonic/tidal experiments, and full multivariable models. Future-valid-time NOAA astronomical values are explicitly marked retrospective-only because archive capture times are unavailable. MCHL1 remains context-only in historic reports and is excluded from this challenger.", "",
                  "## Events and failure diagnostics", "",
                  "MAUL1 qualifying event rows are grouped by the existing Phase 3B event IDs. Hourly overlapping forecasts within one group are not independent sample units. Underforecast tails, quiet/falling conditions, high DENL1 flow, NWCL1 residual/wind conditions, MDLL1 context, and 24-hour threshold alert episodes are available in the compact report. Event windows are outcome-defined verification strata, not the physical onset time of a rise.", "",
                  "## Reproduction and limitations", "",
                  f"Phase 5A/5B baseline parity: **{report['baseline_reproduction']['status']}**. The original scripts were directed to temporary output directories and did not rewrite historical records. All sources and code are hashed in `site/data/research/model-lab.json`.", "",
                  "Historical findings do not establish prospective skill. Original source receipt times are missing, so hourly valid-time bins cannot prove real-time availability. The 2023+ period was previously inspected. Case studies were selected algorithmically from those same reused outcomes. Provisional/quality limitations remain those of the source archive. No challenger was connected to Phase 6 issuance; a new, isolated, prospective shadow study is required before any operational interpretation.", "",
                  "## Reproduce", "", "```sh", "mkdir -p /tmp/maul1-reproduce/phase5a /tmp/maul1-reproduce/phase5b", "python scripts/phase5a.py --root . --outdir /tmp/maul1-reproduce/phase5a", "python scripts/phase5b.py --root . --out /tmp/maul1-reproduce/phase5b", "python scripts/model_lab.py --root . --reproduction-dir /tmp/maul1-reproduce", "```", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--output", type=pathlib.Path, default=None)
    parser.add_argument("--reproduction-dir", type=pathlib.Path, default=None)
    parser.add_argument("--markdown", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    output = args.output or args.root / "site/data/research/model-lab.json"
    report = build_report(args.root, output, args.reproduction_dir)
    markdown = args.markdown or args.root / "docs/model-lab-findings.md"
    write_markdown(report, markdown)
    site_markdown = args.root / "site/data/research/model-lab-findings.md"
    if site_markdown.resolve() != markdown.resolve():
        write_markdown(report, site_markdown)
    print(json.dumps({"output": str(output), "status": report["baseline_reproduction"]["status"],
                      "horizons": report["challenger_headline"], "markdown": str(markdown)}, indent=2))


if __name__ == "__main__":
    main()
