"""Research-only Phase 5B tidal-feature and forecast-robustness experiments.

Uses the committed Phase 5A issue-time tables and existing hourly archive. NOAA
prediction rows have valid-time coverage but no historical capture-time ledger;
their use at a future valid time is therefore isolated as a retrospective-only
sensitivity and never enters the causal candidate or selector.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
import pathlib
import statistics
from collections import defaultdict

import numpy as np

import phase5a

UTC = dt.timezone.utc
HOUR = dt.timedelta(hours=1)
BOUNDARY = phase5a.BOUNDARY
HORIZONS = phase5a.HORIZONS
ALPHAS = (1.0, 10.0, 100.0)
SEED = 20261023
SCHEMA = "5B.1"

MAUL = ("maul1_stage_native_ft", "maul1_change_1h_ft", "maul1_change_3h_ft",
        "maul1_change_6h_ft", "maul1_change_12h_ft", "maul1_change_24h_ft",
        "maul1_change_72h_ft", "maul1_sd_24h_ft")
COASTAL = ("nwcl1_residual_mllw_ft", "nwcl1_residual_change_6h_ft",
           "nwcl1_residual_change_12h_ft", "nwcl1_residual_change_24h_ft",
           "mdll1_stage_change_6h_ft", "mdll1_stage_change_24h_ft",
           "mdll1_stage_change_72h_ft", "nwcl1_wind_u_knots", "nwcl1_wind_v_knots",
           "nwcl1_wind_u_mean_6h_knots", "nwcl1_wind_v_mean_6h_knots",
           "nwcl1_wind_u_mean_24h_knots", "nwcl1_wind_v_mean_24h_knots",
           "nwcl1_wind_directional_persistence_6h")
_RIVER = ("denl1_log_discharge", "denl1_log_change_6h", "denl1_log_change_12h",
          "denl1_log_change_24h", "denl1_log_change_72h", "denl1_stage_change_6h_ft",
          "denl1_stage_change_24h_ft", "mchl1_stage_change_6h_native_ft",
          "mchl1_stage_change_24h_native_ft", "mchl1_stage_change_72h_native_ft",
          "phase4_river_present", "phase4_river_unknown", "phase4_coastal_present",
          "phase4_coastal_unknown")
HARMONICS = ("diurnal_sin", "diurnal_cos", "semidiurnal_sin", "semidiurnal_cos",
             "spring_neap_sin", "spring_neap_cos")
MODEL_FEATURES = {
    "maul1_periodic": MAUL + HARMONICS,
    "maul1_astro_retrospective": MAUL + HARMONICS + ("astronomical_prediction_change_mllw_ft",),
    "maul1_coastal_tidal": MAUL + COASTAL + HARMONICS,
    "full_multivariable": MAUL + COASTAL + _RIVER + HARMONICS,
}
PRIMARY_METHODS = ("persistence_ft", "maul1_only_ft", "maul1_plus_coastal_ft",
                   "maul1_plus_river_ft",
                   "maul1_periodic", "maul1_coastal_tidal", "full_multivariable", "gated_full")


def parse_time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def forecast_valid_time(issue_time, horizon_hours):
    if horizon_hours not in HORIZONS:
        raise ValueError("forecast horizon must be 6, 12, or 24 hours")
    return issue_time + dt.timedelta(hours=int(horizon_hours))


def harmonic_features(issue_time):
    """UTC clock harmonics and a declared 14.765-day proxy, not station phase."""
    hours = issue_time.astimezone(UTC).timestamp() / 3600.0
    phase_day = 2 * math.pi * hours / 24.0
    phase_m2 = 2 * math.pi * hours / 12.42
    phase_spring_neap = 2 * math.pi * hours / (14.765 * 24.0)
    return {"diurnal_sin": math.sin(phase_day), "diurnal_cos": math.cos(phase_day),
            "semidiurnal_sin": math.sin(phase_m2), "semidiurnal_cos": math.cos(phase_m2),
            "spring_neap_sin": math.sin(phase_spring_neap),
            "spring_neap_cos": math.cos(phase_spring_neap)}


def assess_prediction_availability(provenance):
    """Require timestamped evidence that predictions existed before issue time."""
    receipt = provenance.get("capture_time_utc") or provenance.get("receipt_time_utc")
    lead = provenance.get("forecast_lead_hours")
    verified = bool(receipt and lead and provenance.get("source_product_verified"))
    return {"verified_advance_availability": verified,
            "reason": ("timestamped capture and source product metadata establish advance availability"
                       if verified else "archive lacks capture-time evidence proving predictions were available before issue")}


def datum_compatible(row, unit, datum):
    return bool(row and row.get("unit") == unit and row.get("datum") == datum
                and datum and row.get("value") is not None and not row.get("missing"))


def gated_forecast(persistence, issue_variability, threshold, advanced):
    """Causal gate: recent variability is known at issue; outcomes are not accepted."""
    if persistence is None or not math.isfinite(float(persistence)):
        return (advanced, "advanced")
    if issue_variability is None or not math.isfinite(float(issue_variability)):
        return (persistence, "persistence_missing_issue_feature")
    if advanced is None or not math.isfinite(float(advanced)):
        return (persistence, "persistence_missing_advanced")
    if abs(float(issue_variability)) <= float(threshold):
        return (float(persistence), "persistence")
    return (float(advanced), "advanced")


def rising_bias_metrics(actual, forecast):
    actual = np.asarray(actual, float); forecast = np.asarray(forecast, float)
    valid = np.isfinite(actual) & np.isfinite(forecast)
    if not valid.any():
        return {"n": 0, "mean_signed_error_ft": None, "underforecast_fraction": None,
                "mean_underforecast_magnitude_ft": None, "abs_error_p90_ft": None,
                "abs_error_p99_ft": None}
    error = forecast[valid] - actual[valid]
    under = error < 0
    return {"n": int(valid.sum()), "mean_signed_error_ft": float(error.mean()),
            "underforecast_fraction": float(under.mean()),
            "mean_underforecast_magnitude_ft": float((-error[under]).mean()) if under.any() else 0.0,
            "abs_error_p90_ft": float(np.quantile(np.abs(error), .90)),
            "abs_error_p99_ft": float(np.quantile(np.abs(error), .99))}


def is_rising_outcome(row):
    """Retrospective verification label; missing issue or target stage is unknown."""
    actual = row.get("actual")
    current = row.get("maul1_stage_native_ft")
    return actual is not None and current is not None and float(actual) > float(current)


def event_group_metrics(rows):
    groups = defaultdict(list)
    for row in rows:
        if row.get("event_id") and row.get("actual") is not None and row.get("forecast") is not None:
            groups[row["event_id"]].append(float(row["forecast"]) - float(row["actual"]))
    events = {key: {"forecast_count": len(values), "mae_ft": float(np.mean(np.abs(values))),
                    "bias_ft": float(np.mean(values)), "p90_absolute_error_ft": float(np.quantile(np.abs(values), .90))}
              for key, values in sorted(groups.items())}
    return {"event_count": len(events), "events": events}


def empirical_interval_radius(actual, forecast, coverage=.8):
    actual = np.asarray(actual, float); forecast = np.asarray(forecast, float)
    valid = np.isfinite(actual) & np.isfinite(forecast)
    residuals = np.abs(forecast[valid]-actual[valid])
    return {"half_width_ft": float(np.quantile(residuals, coverage)) if len(residuals) else None,
            "calibration_residual_n": int(len(residuals))}


def block_bootstrap_mae(actual, forecast, seed=SEED, replicates=1000, block=168):
    actual = np.asarray(actual, float); forecast = np.asarray(forecast, float)
    valid = np.isfinite(actual) & np.isfinite(forecast)
    actual, forecast = actual[valid], forecast[valid]
    if len(actual) < 2:
        return {"lower_95": None, "upper_95": None, "replicates": 0, "status": "insufficient"}
    rng = np.random.default_rng(seed); n = len(actual); length = min(int(block), n)
    starts = np.arange(n); count = math.ceil(n / length); values = []
    for _ in range(replicates):
        ix = np.concatenate([(start + np.arange(length)) % n for start in rng.choice(starts, count)])[:n]
        values.append(float(np.mean(np.abs(forecast[ix] - actual[ix]))))
    return {"lower_95": float(np.quantile(values, .025)), "upper_95": float(np.quantile(values, .975)),
            "replicates": len(values), "block_hours": int(block), "status": "computed"}


def _metrics(actual, forecast, persistence=None):
    actual = np.asarray(actual, float); forecast = np.asarray(forecast, float)
    valid = np.isfinite(actual) & np.isfinite(forecast)
    if not valid.any():
        return {"n": 0, "mae_ft": None, "rmse_ft": None, "bias_ft": None, "skill_vs_persistence": None}
    error = forecast[valid] - actual[valid]
    persistence = np.asarray(persistence, float) if persistence is not None else None
    base = np.isfinite(persistence[valid]) if persistence is not None else np.zeros(valid.sum(), dtype=bool)
    skill = None
    if persistence is not None and base.all():
        baseline_mae = float(np.mean(np.abs(persistence[valid] - actual[valid])))
        if baseline_mae:
            skill = 1.0 - float(np.mean(np.abs(error))) / baseline_mae
    return {"n": int(valid.sum()), "mae_ft": float(np.mean(np.abs(error))),
            "rmse_ft": float(np.sqrt(np.mean(error * error))), "bias_ft": float(np.mean(error)),
            "skill_vs_persistence": skill}


def annual_metrics(rows, methods):
    years = defaultdict(list)
    for row in rows:
        if row.get("actual") is None:
            continue
        years[row["issue_time"].year].append(row)
    return {str(year): {name: _metrics([r["actual"] for r in items], [r.get(name) for r in items],
                                       [r.get("persistence_ft") for r in items])
                        for name in methods}
            for year, items in sorted(years.items())}


def _read_csv_gz(path):
    with gzip.open(path, "rt", newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _num(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _load_prediction_archive(root):
    """Return completed/valid-time NWCL1 astronomical predictions, with datum."""
    archive = root / "site/data/history/hourly"
    index = {}
    for path in sorted(archive.glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            data = json.load(stream)
        for row in data.get("records", []):
            if row.get("station") == "NWCL1" and row.get("variable") == "prediction":
                try:
                    timestamp = parse_time(row["time"])
                except (KeyError, ValueError):
                    continue
                index[timestamp] = row
    return index


def _load_table(root):
    folder = root / "site/data/history/phase5a"
    predictions = _read_csv_gz(folder / "predictions.csv.gz")
    features = _read_csv_gz(folder / "features.csv.gz")
    feature_by_issue = {row["issue_time_utc"]: row for row in features}
    index = _load_prediction_archive(root)
    records = {h: [] for h in HORIZONS}
    for raw in predictions:
        if raw.get("split") not in ("calibration", "holdout"):
            continue
        issue_s = raw["issue_time_utc"]; issue = parse_time(issue_s)
        horizon = int(raw["horizon_hours"]); feature = feature_by_issue[issue_s]
        row = {name: _num(value) for name, value in feature.items() if name not in
               ("issue_time_utc", "phase4_category", "river_state", "coastal_state")}
        row.update({"issue_time": issue, "target_time": parse_time(raw["target_time_utc"]),
                    "actual": _num(raw.get("actual_gage_height_ft")),
                    "phase4_category": raw.get("phase4_category", "Indeterminate"),
                    "river_state": raw.get("phase4_river", "unknown"),
                    "coastal_state": raw.get("phase4_coastal", "unknown"),
                    "split": raw["split"]})
        for name in ("persistence_ft", "maul1_only_ft", "maul1_plus_river_ft",
                     "maul1_plus_coastal_ft", "maul1_all_ft"):
            row[name] = _num(raw.get(name))
        row.update(harmonic_features(issue))
        issue_prediction = index.get(issue - HOUR)
        target_prediction = index.get(row["target_time"])
        good_issue = datum_compatible(issue_prediction, "ft", "MLLW")
        good_target = datum_compatible(target_prediction, "ft", "MLLW")
        row["astronomical_prediction_change_mllw_ft"] = (
            float(target_prediction["value"]) - float(issue_prediction["value"])
            if good_issue and good_target else None)
        row["astronomical_feature_status"] = "retrospective_valid_time_only" if row[
            "astronomical_prediction_change_mllw_ft"] is not None else "missing_or_incompatible"
        records[horizon].append(row)
    for horizon in HORIZONS:
        records[horizon].sort(key=lambda r: r["issue_time"])
    return records, index


def _matrix(rows, names):
    return np.asarray([[row.get(name) if row.get(name) is not None else np.nan for name in names]
                       for row in rows], dtype=float)


def add_delta_to_stage(stage, delta):
    if stage is None or delta is None:
        return float("nan")
    return float(stage) + float(delta)


def _training_rows(rows, cutoff):
    return [i for i, row in enumerate(rows)
            if row["split"] == "calibration" and row["actual"] is not None
            and row["target_time"] < cutoff and row.get("maul1_stage_native_ft") is not None]


def _forecast_with_model(rows, feature_names, train_ix, predict_ix, alpha):
    train = [rows[i] for i in train_ix]
    predict = [rows[i] for i in predict_ix]
    target = np.asarray([row["actual"] - row["maul1_stage_native_ft"] for row in train], float)
    model = phase5a.fit_ridge(_matrix(train, feature_names), target, feature_names, alpha)
    delta, missing = phase5a.predict_ridge(model, _matrix(predict, feature_names))
    forecasts = np.asarray([add_delta_to_stage(r.get("maul1_stage_native_ft"), change)
                            for r, change in zip(predict, delta)])
    return forecasts, missing, model


def _folds(rows, feature_names):
    """Select alpha and generate expanding blocked OOF calibration predictions."""
    score = {str(alpha): 0.0 for alpha in ALPHAS}; counts = {str(alpha): 0 for alpha in ALPHAS}
    fold_data = []
    for year in range(2017, 2023):
        start = dt.datetime(year, 1, 1, tzinfo=UTC)
        end = dt.datetime(year + 1, 1, 1, tzinfo=UTC)
        cutoff = start - dt.timedelta(hours=72)
        train_ix = _training_rows(rows, cutoff)
        val_ix = [i for i, row in enumerate(rows) if row["split"] == "calibration"
                  and row["actual"] is not None and start + dt.timedelta(hours=144) <= row["issue_time"] < end]
        if len(train_ix) < 500 or not val_ix:
            continue
        fold_data.append((year, train_ix, val_ix))
        for alpha in ALPHAS:
            pred, _, _ = _forecast_with_model(rows, feature_names, train_ix, val_ix, alpha)
            actual = np.asarray([rows[i]["actual"] for i in val_ix])
            valid = np.isfinite(pred) & np.isfinite(actual)
            score[str(alpha)] += float(np.abs(pred[valid] - actual[valid]).sum())
            counts[str(alpha)] += int(valid.sum())
    selected = min(ALPHAS, key=lambda alpha: score[str(alpha)] / counts[str(alpha)]
                   if counts[str(alpha)] else float("inf"))
    oof = {}; fold_summary = []
    for year, train_ix, val_ix in fold_data:
        pred, _, _ = _forecast_with_model(rows, feature_names, train_ix, val_ix, selected)
        for index, value in zip(val_ix, pred):
            oof[index] = float(value)
        fold_summary.append({"year": year, "train_n": len(train_ix), "validation_n": len(val_ix),
                             "train_end_exclusive_utc": phase5a.iso(dt.datetime(year, 1, 1, tzinfo=UTC)-dt.timedelta(hours=72))})
    return selected, oof, {"selected_alpha": selected,
                           "by_alpha": {key: {"n": counts[key], "mae_ft": score[key]/counts[key] if counts[key] else None}
                                        for key in score}, "folds": fold_summary}


def _select_gate(rows, oof, advanced_name):
    ix = [i for i in oof if rows[i]["actual"] is not None and rows[i].get("persistence_ft") is not None
          and rows[i].get("maul1_change_6h_ft") is not None]
    if not ix:
        return {"threshold_ft": None, "advanced_method": advanced_name, "calibration_oof_n": 0}
    variability = np.asarray([abs(rows[i]["maul1_change_6h_ft"]) for i in ix])
    candidates = sorted(set([0.0, .01, .02, .05, .1] + [float(np.quantile(variability, q)) for q in (.1, .2, .3, .4, .5, .6, .7, .8, .9)]))
    actual = np.asarray([rows[i]["actual"] for i in ix]); base = np.asarray([rows[i]["persistence_ft"] for i in ix])
    adv = np.asarray([oof[i] for i in ix])
    best = None
    for threshold in candidates:
        forecast = np.where(variability <= threshold, base, adv)
        mae = float(np.mean(np.abs(forecast-actual)))
        candidate = (mae, threshold)
        if best is None or candidate < best:
            best = candidate
    return {"threshold_ft": best[1], "calibration_oof_mae_ft": best[0],
            "calibration_oof_n": len(ix), "advanced_method": advanced_name,
            "rule": "use persistence when absolute issue-time MAUL1 six-hour change is <= threshold; otherwise use advanced forecast",
            "fitted_on": "blocked forward calibration-only out-of-fold predictions"}


def _fit_models(rows):
    model_data = {}; oof_by_method = {}
    for horizon, items in rows.items():
        model_data[str(horizon)] = {}
        oof_by_method[horizon] = {}
        for name, features in MODEL_FEATURES.items():
            alpha, oof, cv = _folds(items, features)
            train_ix = [i for i, row in enumerate(items) if row["split"] == "calibration"
                        and row["actual"] is not None and row["target_time"] < BOUNDARY-dt.timedelta(hours=72)
                        and row.get("maul1_stage_native_ft") is not None]
            held_ix = [i for i, row in enumerate(items) if row["split"] == "holdout"
                       and row["actual"] is not None and row.get("maul1_stage_native_ft") is not None]
            forecasts = {}
            if train_ix and held_ix:
                pred, _, model = _forecast_with_model(items, features, train_ix, held_ix, alpha)
                forecasts = {i: float(value) for i, value in zip(held_ix, pred)}
                model_data[str(horizon)][name] = {"feature_names": list(features), "alpha": alpha,
                    "training_n": len(train_ix), "holdout_n": len(held_ix),
                    "coefficients": model["coefficients"].tolist(), "medians": model["medians"].tolist(),
                    "target_clip_ft": [model["target_low"], model["target_high"]], "cv": cv}
            else:
                model_data[str(horizon)][name] = {"feature_names": list(features), "alpha": alpha,
                                                  "training_n": len(train_ix), "holdout_n": len(held_ix), "cv": cv}
            oof_by_method[horizon][name] = oof
            for i, value in oof.items():
                items[i][name] = value
            for i, value in forecasts.items():
                items[i][name] = value
        candidate_names = [name for name in MODEL_FEATURES if name != "maul1_astro_retrospective"
                           and oof_by_method[horizon][name]]
        if candidate_names:
            # Pick the single advanced candidate on pooled forward calibration OOF MAE.
            chosen = min(candidate_names, key=lambda name: np.mean([
                abs(items[i]["actual"]-oof_by_method[horizon][name][i])
                for i in oof_by_method[horizon][name]]))
            gate = _select_gate(items, oof_by_method[horizon][chosen], chosen)
        else:
            gate = {"threshold_ft": None, "advanced_method": None, "calibration_oof_n": 0}
        model_data[str(horizon)]["gate"] = gate
        for row_index, row in enumerate(items):
            row["gated_full"] = None
            row["gate_state"] = "unavailable"
            if row["split"] == "calibration":
                chosen_oof = oof_by_method[horizon].get(gate.get("advanced_method"), {})
                advanced = chosen_oof.get(row_index) if chosen_oof else None
            else:
                advanced = row.get(gate.get("advanced_method")) if gate.get("advanced_method") else None
            if gate.get("threshold_ft") is not None and advanced is not None:
                value, state = gated_forecast(row.get("persistence_ft"), row.get("maul1_change_6h_ft"),
                                              gate["threshold_ft"], advanced)
                row["gated_full"], row["gate_state"] = value, state
    return model_data, oof_by_method


def _event_ids(root, rows):
    file = root / "site/data/history/phase3b/validation.json"
    events = json.loads(file.read_text()).get("maul1_first_analysis", {}).get("events", [])
    intervals = sorted((parse_time(event["onset_utc"]), parse_time(event["recovery_end_utc"]), event.get("event_id"))
                       for event in events if event.get("onset_utc") and event.get("recovery_end_utc"))
    starts = [item[0] for item in intervals]
    for row in rows:
        end = bisect.bisect_right(starts, row["issue_time"])
        row["event_ids"] = [event_id for start, finish, event_id in intervals[:end]
                            if start <= row["issue_time"] <= finish]


def _evaluate(rows, model_data, oof):
    summary = {}; paired = {}; annual = {}; event_reports = {}; bias = {}; intervals = {}; strata = {}
    base_methods = list(PRIMARY_METHODS)
    for horizon, items in rows.items():
        held = [r for r in items if r["split"] == "holdout" and r["actual"] is not None]
        summary[str(horizon)] = {}
        for method in base_methods:
            forecast = [r.get(method) for r in held]
            actual = [r["actual"] for r in held]
            metrics = _metrics(actual, forecast, [r.get("persistence_ft") for r in held])
            metrics["skill_block_bootstrap_95"] = block_bootstrap_mae(actual, forecast,
                seed=SEED+horizon+sum(map(ord, method)), replicates=500, block=168)
            summary[str(horizon)][method] = metrics
        paired_names = ("persistence_ft", "maul1_only_ft", "maul1_plus_river_ft", "maul1_plus_coastal_ft", "maul1_periodic",
                        "maul1_coastal_tidal", "full_multivariable", "gated_full")
        common = [r for r in held if all(r.get(name) is not None for name in paired_names)]
        paired[str(horizon)] = {"paired_sample_n": len(common), "methods": {
            name: _metrics([r["actual"] for r in common], [r.get(name) for r in common],
                           [r.get("persistence_ft") for r in common]) for name in paired_names}}
        astro = _metrics([r["actual"] for r in held], [r.get("maul1_astro_retrospective") for r in held],
                         [r.get("persistence_ft") for r in held])
        astro["availability_status"] = "retrospective_only_unverified_advance_availability"
        summary[str(horizon)]["maul1_astro_retrospective"] = astro
        annual[str(horizon)] = annual_metrics(held, base_methods)
        events = []
        for method in base_methods:
            event_rows = [{"event_id": event, "actual": row["actual"], "forecast": row.get(method)}
                          for row in held for event in row.get("event_ids", [])]
            events.append((method, event_group_metrics(event_rows)))
        event_map = {name: result for name, result in events}
        event_reports[str(horizon)] = dict(events=event_map,
            worst_events_by_method={name: sorted(value["events"].items(), key=lambda item: item[1]["mae_ft"], reverse=True)[:10]
                                    for name, value in event_map.items()})
        # Rising/rapid-rise strata use retrospective outcomes strictly for evaluation.
        cal_rises = [r["actual"]-r["maul1_stage_native_ft"] for r in items
                     if r["split"] == "calibration" and r["actual"] is not None and r.get("maul1_stage_native_ft") is not None
                     and r["actual"] > r["maul1_stage_native_ft"]]
        q90 = float(np.quantile(cal_rises, .9)) if cal_rises else None
        masks = {
            "all": lambda r: True,
            "rising_outcome": is_rising_outcome,
            "rapid_rise_outcome": lambda r: q90 is not None and is_rising_outcome(r)
                and r["actual"]-r["maul1_stage_native_ft"] >= q90,
        }
        for category in sorted(set(r.get("phase4_category", "Indeterminate") for r in held)):
            masks["phase4_"+category.lower().replace(" ", "_")] = lambda r, c=category: r.get("phase4_category") == c
        masks.update({"season_winter": lambda r: r["issue_time"].month in (12, 1, 2),
                      "season_spring": lambda r: r["issue_time"].month in (3, 4, 5),
                      "season_summer": lambda r: r["issue_time"].month in (6, 7, 8),
                      "season_fall": lambda r: r["issue_time"].month in (9, 10, 11)})
        masks["issue_time_maul1_rising"] = lambda r: r.get("maul1_change_6h_ft") is not None and r["maul1_change_6h_ft"] >= .1
        masks["issue_time_maul1_quiet"] = lambda r: r.get("maul1_change_6h_ft") is not None and abs(r["maul1_change_6h_ft"]) <= .02
        masks["missing_coastal_predictors"] = lambda r: any(r.get(name) is None for name in COASTAL)
        masks["coastal_residual_setup_high"] = lambda r: r.get("nwcl1_residual_mllw_ft") is not None and r["nwcl1_residual_mllw_ft"] > 0
        strata[str(horizon)] = {name: {method: _metrics(
            [r["actual"] for r in held if predicate(r)], [r.get(method) for r in held if predicate(r)],
            [r.get("persistence_ft") for r in held if predicate(r)]) for method in base_methods}
            for name, predicate in masks.items()}
        bias[str(horizon)] = {method: rising_bias_metrics(
            [r["actual"] for r in held if masks["rising_outcome"](r)],
            [r.get(method) for r in held if masks["rising_outcome"](r)]) for method in base_methods}
        intervals[str(horizon)] = {}
        for method in base_methods:
            residual_actual = [r["actual"] for i, r in enumerate(items)
                               if method in oof[horizon] and i in oof[horizon][method] and r["actual"] is not None]
            residual_forecast = [oof[horizon][method][i] for i, r in enumerate(items)
                                 if method in oof[horizon] and i in oof[horizon][method] and r["actual"] is not None]
            # Original Phase 5A forecasts for comparators do not have Phase 5B OOF entries.
            if method in ("persistence_ft", "maul1_only_ft", "maul1_plus_river_ft", "maul1_plus_coastal_ft"):
                cal_rows = [r for r in items if r["split"] == "calibration" and r["actual"] is not None]
                residual_actual = [r["actual"] for r in cal_rows]
                residual_forecast = [r.get(method) for r in cal_rows]
            if method == "gated_full":
                cal_rows = [r for r in items if r["split"] == "calibration" and r["actual"] is not None]
                residual_actual = [r["actual"] for r in cal_rows]
                residual_forecast = [r.get(method) for r in cal_rows]
            calibrated = empirical_interval_radius(residual_actual, residual_forecast)
            radius = calibrated["half_width_ft"]
            held_errors = [abs(r[method]-r["actual"]) for r in held if radius is not None and r.get(method) is not None]
            coverage = float(np.mean(np.asarray(held_errors) <= radius)) if held_errors else None
            intervals[str(horizon)][method] = {"nominal_coverage": .8, "half_width_ft": radius,
                "calibration_residual_n": calibrated["calibration_residual_n"], "holdout_coverage": coverage,
                "holdout_interval_width_ft": 2*radius if radius is not None else None,
                "undercoverage_during_rising": (float(np.mean([
                    abs(r[method]-r["actual"]) <= radius for r in held
                    if masks["rising_outcome"](r) and r.get(method) is not None]))
                    if radius is not None and any(masks["rising_outcome"](r) and r.get(method) is not None for r in held) else None)}
    return {"holdout": summary, "paired_holdout": paired, "annual": annual, "event_groups": event_reports,
            "rising_bias": bias, "stratified": strata, "intervals": intervals}


def _write_predictions(path, rows):
    fields = ["issue_time_utc", "horizon_hours", "target_time_utc", "split", "actual_native_gage_height_ft",
              "persistence_ft", "phase5a_maul1_only_ft", "phase5a_river_ft", "phase5a_coastal_ft", *MODEL_FEATURES.keys(),
              "gated_full", "gate_state", "astronomical_feature_status", "phase4_category", "event_ids"]
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
                for horizon in HORIZONS:
                    for row in rows[horizon]:
                        writer.writerow({"issue_time_utc": phase5a.iso(row["issue_time"]), "horizon_hours": horizon,
                            "target_time_utc": phase5a.iso(row["target_time"]), "split": row["split"],
                            "actual_native_gage_height_ft": row.get("actual"), "persistence_ft": row.get("persistence_ft"),
                            "phase5a_maul1_only_ft": row.get("maul1_only_ft"),
                            "phase5a_river_ft": row.get("maul1_plus_river_ft"),
                            "phase5a_coastal_ft": row.get("maul1_plus_coastal_ft"),
                            **{name: row.get(name) for name in MODEL_FEATURES}, "gated_full": row.get("gated_full"),
                            "gate_state": row.get("gate_state"), "astronomical_feature_status": row.get("astronomical_feature_status"),
                            "phase4_category": row.get("phase4_category"), "event_ids": ";".join(row.get("event_ids", []))})


def _json(path, data):
    path.write_text(json.dumps(phase5a._jsonable(data), indent=2, sort_keys=True, allow_nan=False)+"\n")


def causal_report_methods(method_results):
    return [name for name in method_results if name != "maul1_astro_retrospective"]


def _report(outdir, result, models, records, astro_index):
    lines = ["# Phase 5B tidal-aware forecasting and robustness validation", "",
        "Research-only retrospective hindcasts in native MAUL1 gage height; not operational forecasts or flood probabilities.", "",
        "Calibration is 2016–2022; holdout is 2023 onward and is a reused benchmark already inspected in Phase 5A. Features, alpha and the gate are fitted by blocked forward calibration validation with 72-hour target embargo. All forecast inputs use completed issue-time bins. The 4.0-ft NAVD88 threshold is not assessed.", "",
        "## Holdout MAE and persistence-relative skill", "",
        "Rows use each method's eligible paired issue times; differences against Phase 5A should use identical samples. Overlapping hourly forecasts are not independent.", "",
        "| Horizon | Method | n | MAE (ft) | Skill vs persistence | Bias (ft) | 95% blocked MAE interval |", "|---:|---|---:|---:|---:|---:|---|"]
    for horizon, methods in result["holdout"].items():
        for method in causal_report_methods(methods):
            metrics = methods[method]
            ci=metrics["skill_block_bootstrap_95"]
            lines.append(f"| {horizon} h | {method} | {metrics['n']} | {metrics['mae_ft'] if metrics['mae_ft'] is not None else 'n/a'} | {metrics['skill_vs_persistence'] if metrics['skill_vs_persistence'] is not None else 'n/a'} | {metrics['bias_ft'] if metrics['bias_ft'] is not None else 'n/a'} | {ci['lower_95']}–{ci['upper_95']} |")
    lines.extend(["", "## Paired model comparison on shared issue times", "",
                  "All methods below use the same eligible issue/target rows at each horizon; this is the preferred incremental comparison.",
                  "", "| Horizon | Paired n | Method | MAE (ft) | Skill vs persistence |", "|---:|---:|---|---:|---:|"])
    for horizon, group in result["paired_holdout"].items():
        for method, metrics in group["methods"].items():
            lines.append(f"| {horizon} h | {group['paired_sample_n']} | {method} | {metrics['mae_ft']} | {metrics['skill_vs_persistence']} |")
    lines.extend(["", "This paired table answers whether tidal features, additional river/coastal evidence, or issue-time gating add value over the Phase 5A coastal reference on identical opportunities. Read it together with rising-water bias; overall MAE alone is insufficient.", "",
                  "## Interpretation of incremental changes", ""])
    for horizon, group in result["paired_holdout"].items():
        methods = group["methods"]
        coast = methods["maul1_plus_coastal_ft"]["mae_ft"]
        periodic = methods["maul1_periodic"]["mae_ft"]
        coastal_tide = methods["maul1_coastal_tidal"]["mae_ft"]
        full = methods["full_multivariable"]["mae_ft"]
        gate = methods["gated_full"]["mae_ft"]
        river = methods["maul1_plus_river_ft"]["mae_ft"]
        astro = result["holdout"][horizon]["maul1_astro_retrospective"]["mae_ft"]
        lines.append(f"At {horizon} h, adding issue-time harmonics to MAUL1 changes MAE by {periodic-methods['maul1_only_ft']['mae_ft']:+.4f} ft versus Phase 5A MAUL1-only. The tidal/coastal candidate changes MAE by {coastal_tide-coast:+.4f} ft versus the Phase 5A coastal candidate; the full river/coastal candidate changes it by {full-coast:+.4f} ft. The Phase 5A river-only comparator MAE is {river:.4f} ft. The calibration-fitted gate changes paired MAE by {gate-coast:+.4f} ft versus the Phase 5A coastal reference. The unverified-availability astronomical sensitivity has MAE {astro:.4f} ft and is not causal evidence.")
    lines.extend(["", "The calendar-harmonic model adds little beyond MAUL1 history. Adding tidal/coastal features shifts holdout MAE only slightly relative to Phase 5A, while the full multivariable and issue-time gate do not consistently improve the coastal reference. The gate selected a zero variability threshold in each horizon, so it almost always issued the advanced periodic candidate; this failed to retain the stronger Phase 5A coastal model. The 6-hour coastal+tidal improvement is small and must not be treated as robust without prospective verification. The archived astronomical sensitivity modestly changes scores but relies on unverified future valid-time archive values and cannot justify a forecast feature.", ""])
    lines.extend(["", "The `maul1_astro_retrospective` method is not a causal forecast and is kept out of the primary table above. Its holdout sensitivity is in `summary.json`; compare its paired sample size before interpreting it against the harmonic-only candidate.", ""])
    astro_n=sum(row.get("astronomical_prediction_change_mllw_ft") is not None for group in records.values() for row in group if row["split"]=="holdout")
    total=sum(row["split"]=="holdout" for group in records.values() for row in group)
    lines.extend(["", "## Tidal features and availability", "",
        f"The causal periodic candidate uses UTC 24-hour and 12.42-hour sinusoids and a 14.765-day spring-neap phase proxy. These are calendar harmonics, not a calibrated local tide prediction; NWCL1 phase is not transferred to MAUL1. NOAA CO-OPS prediction rows use MLLW and pass an exact datum check, but the archive has no capture timestamp or issue-time availability ledger. Therefore target-valid-time astronomical values are isolated in `maul1_astro_retrospective`, excluded from all causal model selection and gating. Holdout rows with a matched retrospective prediction delta: {astro_n} of {total} horizon rows. Their scores are not an advance forecast skill estimate.", "",
        "## Gating and rising-water errors", "",
        "The issue-time gate selects persistence below a calibration-only variability threshold and the chosen advanced candidate above it. Missing issue features fall back to persistence. Rising-water strata use target outcomes for verification only.", "",
        "| Horizon | Method | Rising n | Mean signed error (ft) | Underforecast frequency | Mean underforecast (ft) | P99 abs error (ft) |", "|---:|---|---:|---:|---:|---:|---:|"])
    for horizon, methods in result["rising_bias"].items():
        for method, metrics in methods.items():
            lines.append(f"| {horizon} h | {method} | {metrics['n']} | {metrics['mean_signed_error_ft']} | {metrics['underforecast_fraction']} | {metrics['mean_underforecast_magnitude_ft']} | {metrics['abs_error_p99_ft']} |")
    lines.extend(["", "## Robustness and uncertainty", "",
        "Annual metrics, Phase 3B response-event group metrics, Phase 4 issue-state strata, interval coverage, model parameters, and paired issue forecasts are in the adjacent JSON/CSV files. Event grouping avoids interpreting overlapping hourly forecasts as independent events. Empirical 80% symmetric residual intervals are calibrated from forward OOF calibration predictions for Phase 5B models and calibration residuals for Phase 5A comparators.", "",
        "No verified lead-time capture metadata exists for the archived NOAA prediction product. The archive does not provide reliable operational forecast availability; no model here is eligible for deployment. The 2023-onward scores are reused retrospective benchmarks, not pristine independent model-selection results. A prospective research trial should freeze this code, issue forecasts prospectively at fixed UTC hours, archive the full input snapshot and receipt time, and verify against future completed MAUL1 bins after a predeclared period; remain free and non-operational.", "",
        "## Historical case comparisons", "",
        "The case-level table reports matched-window MAE and rising-outcome underforecast frequency. August 2016 and Beta 2020 are calibration-era examples; November 2024 and April 2025 are part of the reused historical benchmark, not pristine model-selection cases.",
        "", "| Case | Period class | Horizon | Phase 5A coastal MAE | Phase 5B coastal+tide MAE | Phase 5B full MAE | Phase 5B gated MAE |", "|---|---|---:|---:|---:|---:|---:|"])
    cases = json.loads((outdir / "case-studies.json").read_text())
    for case in cases["priority_cases"]:
        for horizon, values in case["horizons"].items():
            metrics = values.get("comparison_metrics", {})
            get = lambda name: metrics.get(name, {}).get("mae_ft")
            lines.append(f"| {case['case_id']} | {case['calibration_or_holdout']} | {horizon} h | {get('phase5a_coastal')} | {get('phase5b_coastal_tidal')} | {get('phase5b_full')} | {get('phase5b_gated')} |")
    lines.extend(["", "Additional post-2022 cases are selected by the largest positive 24-hour outcome changes with non-overlapping 72-hour windows; because selection uses future outcomes, these examples describe retrospective outcomes and do not measure operational selection skill.", ""])
    for case in cases["post_2022_mechanical_cases"]:
        lines.append(f"- {case['issue_time_utc']}: observed +{case['observed_24h_rise_ft']:.3f} ft in 24 h; Phase 5A coastal {case['phase5a_coastal_forecast_ft']}; Phase 5B periodic {case['phase5b_forecasts'].get('maul1_periodic')}, coastal+tide {case['phase5b_forecasts'].get('maul1_coastal_tidal')}, full {case['phase5b_forecasts'].get('full_multivariable')}.")
    lines.append("")
    (outdir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _case_studies(root, rows):
    phase5a_cases = json.loads((root / "site/data/history/phase5a/case-studies.json").read_text())
    by_key = {(h, phase5a.iso(r["issue_time"])): r for h, items in rows.items() for r in items}
    cases = []
    for old in phase5a_cases:
        case = {"case_id": old["case_id"], "case_name": old.get("name", old["case_id"]),
                "calibration_or_holdout": old["calibration_or_holdout"], "horizons": {}}
        for horizon, content in old.get("horizons", {}).items():
            issues = content.get("issue_times_utc", [])
            case["horizons"][horizon] = {"issue_times_utc": issues,
                "actual_native_gage_height_ft": content.get("actual_gage_height_ft", []),
                "phase5a_forecasts": content.get("forecasts", {}),
                "phase5a_river_forecast_ft": [by_key.get((int(horizon), issue), {}).get("maul1_plus_river_ft") for issue in issues],
                "phase5b_forecasts": {name: [by_key.get((int(horizon), issue), {}).get(name) for issue in issues]
                                       for name in MODEL_FEATURES}}
            case_rows = [by_key.get((int(horizon), issue), {}) for issue in issues]
            actuals = content.get("actual_gage_height_ft", [])
            phase5a_forecasts = content.get("forecasts", {})
            phase5b = case["horizons"][horizon]["phase5b_forecasts"]
            forecast_sets = {
                "phase5a_persistence": phase5a_forecasts.get("persistence", []),
                "phase5a_maul1_only": phase5a_forecasts.get("maul1_only", []),
                "phase5a_river": case["horizons"][horizon]["phase5a_river_forecast_ft"],
                "phase5a_coastal": phase5a_forecasts.get("maul1_plus_coastal", []),
                "phase5b_periodic": phase5b.get("maul1_periodic", []),
                "phase5b_coastal_tidal": phase5b.get("maul1_coastal_tidal", []),
                "phase5b_full": phase5b.get("full_multivariable", []),
                "phase5b_gated": [row.get("gated_full") for row in case_rows],
            }
            comparison = {}
            for method, forecasts in forecast_sets.items():
                aligned = [(float(y), float(f), row.get("maul1_stage_native_ft"))
                           for y, f, row in zip(actuals, forecasts, case_rows)
                           if y is not None and f is not None and math.isfinite(float(f))]
                errors = [forecast - actual for actual, forecast, _ in aligned]
                rising = [error for (actual, _, stage), error in zip(aligned, errors)
                          if stage is not None and actual > stage]
                comparison[method] = {"n": len(aligned),
                    "mae_ft": float(np.mean(np.abs(errors))) if errors else None,
                    "bias_ft": float(np.mean(errors)) if errors else None,
                    "rising_outcome_n": len(rising),
                    "rising_underforecast_fraction": float(np.mean(np.asarray(rising) < 0)) if rising else None}
            case["horizons"][horizon]["comparison_metrics"] = comparison
        cases.append(case)
    # Predeclared mechanical rule: largest 24-h stage rises in disjoint 72-h issue windows.
    held = [r for r in rows[24] if r["split"] == "holdout" and r["actual"] is not None
            and r.get("maul1_stage_native_ft") is not None]
    selected = []
    for row in sorted(held, key=lambda r: r["actual"]-r["maul1_stage_native_ft"], reverse=True):
        if row["actual"] <= row["maul1_stage_native_ft"]:
            continue
        if any(abs((row["issue_time"]-old["issue_time"]).total_seconds()) < 72*3600 for old in selected):
            continue
        selected.append(row)
        if len(selected) == 6:
            break
    selected_cases = [{"selection_rule": "largest positive 24-hour stage changes after 2022; non-overlapping 72-hour issue windows",
        "retrospective_outcome_selected": True, "issue_time_utc": phase5a.iso(row["issue_time"]),
        "target_time_utc": phase5a.iso(row["target_time"]), "actual_native_gage_height_ft": row["actual"],
        "issue_native_gage_height_ft": row["maul1_stage_native_ft"],
        "observed_24h_rise_ft": row["actual"]-row["maul1_stage_native_ft"],
        "phase5a_coastal_forecast_ft": row.get("maul1_plus_coastal_ft"),
        "phase5b_forecasts": {name: row.get(name) for name in MODEL_FEATURES}}
        for row in selected]
    return {"priority_cases": cases, "post_2022_mechanical_cases": selected_cases,
            "limitation": "Historical case comparisons are retrospective illustrations; calibration-era cases are not independent verification.",
            "case_window_warning": "The post-2022 examples are selected using observed future stage outcomes and cannot estimate forecast selection skill."}


def run(root, outdir):
    root = pathlib.Path(root); outdir = pathlib.Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    rows, astro = _load_table(root)
    for horizon in HORIZONS:
        _event_ids(root, rows[horizon])
    model_data, oof = _fit_models(rows)
    result = _evaluate(rows, model_data, oof)
    _write_predictions(outdir / "predictions.csv.gz", rows)
    availability = assess_prediction_availability({"source": "NOAA CO-OPS", "product": "predictions",
                                                    "valid_time_coverage": len(astro)})
    input_files = sorted((root / "site/data/history/hourly").glob("*.json.gz")) + [
        root / "site/data/history/phase5a/features.csv.gz",
        root / "site/data/history/phase5a/predictions.csv.gz",
        root / "site/data/history/phase5a/case-studies.json",
        root / "site/data/history/phase3b/validation.json"]
    input_hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in input_files}
    summary = {"schema_version": SCHEMA, "study": "Phase 5B experimental tidal-feature hindcasts; research-only",
        "calibration": "2016-01-01 through 2022-12-31, with 72-hour embargo",
        "holdout": "2023 onward, reused historical benchmark; not pristine independent selection",
        "target": "MAUL1 native stage gage height in ft; no NAVD88 conversion",
        "astronomical_prediction_availability": availability,
        "astronomical_prediction_valid_time_rows": len(astro), "holdout_results": result["holdout"],
        "tidal_feature_definition": {"diurnal": "UTC 24 h harmonic", "semidiurnal": "UTC 12.42 h harmonic",
            "spring_neap": "14.765 d calendar proxy; not a local astronomical prediction"},
        "gates": {h: model_data[h]["gate"] for h in model_data},
        "limitations": ["Retrospective MAUL1 stage hindcasts, not operational forecasts.",
            "NOAA prediction capture times and advance availability are unverified; target-valid-time results are a separate retrospective sensitivity.",
            "NWCL1 astronomical/tidal phase is not assumed to transfer to MAUL1.",
            "2023-onward holdout has already been inspected in Phase 5A.",
            "Hourly overlapping forecasts are dependent; use blocked intervals and event groups.",
            "No 4.0-ft NAVD88 threshold inference is made from native gage height."]}
    _json(outdir / "summary.json", summary)
    _json(outdir / "paired-comparisons.json", result["paired_holdout"])
    _json(outdir / "models.json", model_data)
    _json(outdir / "annual.json", result["annual"])
    _json(outdir / "event-robustness.json", result["event_groups"])
    _json(outdir / "rising-bias.json", result["rising_bias"])
    _json(outdir / "stratified.json", result["stratified"])
    _json(outdir / "uncertainty.json", result["intervals"])
    _json(outdir / "case-studies.json", _case_studies(root, rows))
    _json(outdir / "provenance.json", {"schema_version": SCHEMA, "source_reports": [
        "site/data/history/phase5a/features.csv.gz", "site/data/history/phase5a/predictions.csv.gz",
        "site/data/history/hourly/*.json.gz", "site/data/history/phase3b/validation.json"],
        "input_files_sha256": input_hashes,
        "code_sha256": hashlib.sha256((root/"scripts/phase5b.py").read_bytes()).hexdigest(),
        "astronomical_availability": availability,
        "future_known_feature_policy": "Only completed issue-time observations and issue timestamp harmonics are causal; future valid-time prediction products are segregated.",
        "split": "2016-2022 calibration; 2023 onward reused holdout; 72-hour temporal embargo"})
    _report(outdir, result, model_data, rows, astro)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args(argv)
    output = args.out or args.root / "site/data/history/phase5b"
    run(args.root, output)
    print(f"Phase 5B reports generated in {output}")


if __name__ == "__main__":
    main()
