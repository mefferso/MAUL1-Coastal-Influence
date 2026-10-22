"""Reproducible, valid-time-only Phase 5A water-level hindcasts.

The pipeline consumes the committed Phase 3A hourly archive and Phase 4
causal evidence engine. It never downloads observations or uses future event
labels as forecast inputs. MAUL1 gage height remains in its native 00065
reference; no NAVD88 conversion is applied.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
import statistics
from collections import defaultdict

import numpy as np

import evidence
import phase4

UTC = dt.timezone.utc
HOUR = dt.timedelta(hours=1)
BOUNDARY = dt.datetime(2023, 1, 1, tzinfo=UTC)
ARCHIVE_START = dt.datetime(2016, 1, 1, tzinfo=UTC)
LOOKBACK_HOURS = 72
EMBARGO_HOURS = 72
HORIZONS = (6, 12, 24)
ALPHAS = (0.1, 1.0, 10.0, 100.0)
DEFAULT_ALPHA = 10.0
DEFAULT_TREND_WINDOW = 6
DEFAULT_TREND_SHRINK = 0.25
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_BLOCK_HOURS = 168
RANDOM_SEED = 20261022
SCHEMA_VERSION = "5A.1"

FEATURE_GROUPS = {}


def _group(name, group):
    FEATURE_GROUPS[name] = group
    return name


FEATURE_NAMES = (
    _group("maul1_stage_native_ft", "maul1"),
    _group("maul1_change_1h_ft", "maul1"),
    _group("maul1_change_3h_ft", "maul1"),
    _group("maul1_change_6h_ft", "maul1"),
    _group("maul1_change_12h_ft", "maul1"),
    _group("maul1_change_24h_ft", "maul1"),
    _group("maul1_change_72h_ft", "maul1"),
    _group("maul1_slope_6h_ft_per_h", "maul1"),
    _group("maul1_sd_24h_ft", "maul1"),
    _group("denl1_log_discharge", "river"),
    _group("denl1_log_change_6h", "river"),
    _group("denl1_log_change_12h", "river"),
    _group("denl1_log_change_24h", "river"),
    _group("denl1_log_change_72h", "river"),
    _group("denl1_stage_change_6h_ft", "river"),
    _group("denl1_stage_change_24h_ft", "river"),
    _group("nwcl1_residual_mllw_ft", "coastal"),
    _group("nwcl1_residual_change_6h_ft", "coastal"),
    _group("nwcl1_residual_change_12h_ft", "coastal"),
    _group("nwcl1_residual_change_24h_ft", "coastal"),
    _group("mdll1_stage_change_6h_ft", "coastal"),
    _group("mdll1_stage_change_24h_ft", "coastal"),
    _group("mdll1_stage_change_72h_ft", "coastal"),
    _group("nwcl1_wind_u_knots", "coastal"),
    _group("nwcl1_wind_v_knots", "coastal"),
    _group("nwcl1_wind_u_mean_6h_knots", "coastal"),
    _group("nwcl1_wind_v_mean_6h_knots", "coastal"),
    _group("nwcl1_wind_u_mean_24h_knots", "coastal"),
    _group("nwcl1_wind_v_mean_24h_knots", "coastal"),
    _group("nwcl1_wind_directional_persistence_6h", "coastal"),
    _group("mchl1_stage_change_6h_native_ft", "pass_context"),
    _group("mchl1_stage_change_24h_native_ft", "pass_context"),
    _group("mchl1_stage_change_72h_native_ft", "pass_context"),
    _group("phase4_river_present", "phase4_river"),
    _group("phase4_river_unknown", "phase4_river"),
    _group("phase4_coastal_present", "phase4_coastal"),
    _group("phase4_coastal_unknown", "phase4_coastal"),
)

MODEL_GROUPS = {
    "maul1_only": ("maul1",),
    "maul1_plus_river": ("maul1", "river", "phase4_river"),
    "maul1_plus_coastal": ("maul1", "coastal", "pass_context", "phase4_coastal"),
    "maul1_all": ("maul1", "river", "coastal", "pass_context", "phase4_river", "phase4_coastal"),
}
MODEL_NAMES = ("persistence", "stage_trend", *MODEL_GROUPS.keys())
METHOD_COLUMNS = {
    "persistence": "persistence_ft",
    "stage_trend": "stage_trend_ft",
    "maul1_only": "maul1_only_ft",
    "maul1_plus_river": "maul1_plus_river_ft",
    "maul1_plus_coastal": "maul1_plus_coastal_ft",
    "maul1_all": "maul1_all_ft",
}

EXPECTED = {
    ("MAUL1", "stage"): "ft",
    ("DENL1", "discharge"): "cfs",
    ("DENL1", "stage"): "ft",
    ("NWCL1", "residual"): "ft",
    ("MDLL1", "stage"): "ft",
    ("MCHL1", "stage"): "ft",
    ("NWCL1", "wind_u"): "knots",
    ("NWCL1", "wind_v"): "knots",
}


def iso(value):
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def finite_number(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def valid_observation(row, expected_unit, datum=None):
    """Validate one bin without retrospective full-month quality findings."""
    return bool(
        row
        and finite_number(row.get("value"))
        and row.get("coverage", 0) >= 1
        and not row.get("missing")
        and not row.get("phase4_quality_excluded")
        and row.get("unit") == expected_unit
        and row.get("datum")
        and (datum is None or row.get("datum") == datum)
    )


def latest_completed_bin(index, key, issue_time, unit=None, datum=None):
    """Return only the hour [issue-1h, issue) completed by this issuance."""
    if unit is None:
        unit = EXPECTED.get(tuple(key))
    row = index.get(tuple(key), {}).get(issue_time - HOUR)
    return row if valid_observation(row, unit, datum) else None


def change_at_issue(index, key, issue_time, lag_hours, unit=None):
    """Exact-endpoint native-unit change; never interpolates missing hours."""
    if unit is None:
        unit = EXPECTED.get(tuple(key))
    current = latest_completed_bin(index, key, issue_time, unit)
    old = index.get(tuple(key), {}).get(issue_time - dt.timedelta(hours=lag_hours + 1))
    if not valid_observation(old, unit) or not current or old.get("datum") != current.get("datum"):
        return None
    return float(current["value"]) - float(old["value"])


def _window(index, key, issue_time, hours, unit, require_fraction=0.8):
    rows = [index.get(key, {}).get(issue_time - HOUR * offset) for offset in range(1, hours + 1)]
    good = [r for r in rows if valid_observation(r, unit)]
    datums = {r["datum"] for r in good}
    if len(good) / hours < require_fraction or len(datums) != 1:
        return []
    return [float(r["value"]) for r in rows if valid_observation(r, unit)]


def _mean_feature(index, key, issue_time, hours, unit):
    vals = _window(index, key, issue_time, hours, unit, 0.8)
    return float(statistics.fmean(vals)) if vals else None


def _std_feature(index, key, issue_time, hours, unit):
    vals = _window(index, key, issue_time, hours, unit, 0.8)
    return float(statistics.pstdev(vals)) if len(vals) >= 2 else None


def issue_features(index, issue_time, thresholds=None, assessment=None):
    """Build a single causal feature row from completed bins only."""
    f = {name: None for name in FEATURE_NAMES}
    stage = latest_completed_bin(index, ("MAUL1", "stage"), issue_time, "ft", "gage height")
    if stage:
        f["maul1_stage_native_ft"] = float(stage["value"])
    for lag in (1, 3, 6, 12, 24, 72):
        f[f"maul1_change_{lag}h_ft"] = change_at_issue(index, ("MAUL1", "stage"), issue_time, lag, "ft")
    d6 = f["maul1_change_6h_ft"]
    if d6 is not None:
        f["maul1_slope_6h_ft_per_h"] = d6 / 6.0
    f["maul1_sd_24h_ft"] = _std_feature(index, ("MAUL1", "stage"), issue_time, 24, "ft")

    q = latest_completed_bin(index, ("DENL1", "discharge"), issue_time, "cfs", "native")
    if q:
        f["denl1_log_discharge"] = math.log1p(max(0.0, float(q["value"])))
    for lag in (6, 12, 24, 72):
        change = change_at_issue(index, ("DENL1", "discharge"), issue_time, lag, "cfs")
        old = index.get(("DENL1", "discharge"), {}).get(issue_time - dt.timedelta(hours=lag + 1))
        if q and valid_observation(old, "cfs", "native") and old["value"] >= 0:
            f[f"denl1_log_change_{lag}h"] = math.log1p(max(0.0, float(q["value"]))) - math.log1p(float(old["value"]))
    f["denl1_stage_change_6h_ft"] = change_at_issue(index, ("DENL1", "stage"), issue_time, 6, "ft")
    f["denl1_stage_change_24h_ft"] = change_at_issue(index, ("DENL1", "stage"), issue_time, 24, "ft")

    residual = latest_completed_bin(index, ("NWCL1", "residual"), issue_time, "ft", "MLLW")
    if residual:
        f["nwcl1_residual_mllw_ft"] = float(residual["value"])
    for lag in (6, 12, 24):
        f[f"nwcl1_residual_change_{lag}h_ft"] = change_at_issue(index, ("NWCL1", "residual"), issue_time, lag, "ft")
    for lag in (6, 24, 72):
        f[f"mdll1_stage_change_{lag}h_ft"] = change_at_issue(index, ("MDLL1", "stage"), issue_time, lag, "ft")
    for lag in (6, 24, 72):
        f[f"mchl1_stage_change_{lag}h_native_ft"] = change_at_issue(index, ("MCHL1", "stage"), issue_time, lag, "ft")

    for component in ("u", "v"):
        key = ("NWCL1", f"wind_{component}")
        current = latest_completed_bin(index, key, issue_time, "knots", "none")
        if current:
            f[f"nwcl1_wind_{component}_knots"] = float(current["value"])
        for hours in (6, 24):
            f[f"nwcl1_wind_{component}_mean_{hours}h_knots"] = _mean_feature(index, key, issue_time, hours, "knots")
    vectors = []
    for offset in range(1, 7):
        u = index.get(("NWCL1", "wind_u"), {}).get(issue_time - HOUR * offset)
        v = index.get(("NWCL1", "wind_v"), {}).get(issue_time - HOUR * offset)
        if valid_observation(u, "knots", "none") and valid_observation(v, "knots", "none"):
            vectors.append((float(u["value"]), float(v["value"])))
    if len(vectors) >= 5:
        unit_vectors = [(u / math.hypot(u, v), v / math.hypot(u, v)) for u, v in vectors if math.hypot(u, v) > 1e-9]
        if unit_vectors:
            f["nwcl1_wind_directional_persistence_6h"] = math.hypot(
                statistics.fmean(u for u, _ in unit_vectors),
                statistics.fmean(v for _, v in unit_vectors),
            )

    assessment = assessment or evidence.assess(index, issue_time, thresholds)
    for pathway in ("river", "coastal"):
        state = assessment["flags"][pathway]
        f[f"phase4_{pathway}_present"] = 1.0 if state == "present" else 0.0
        f[f"phase4_{pathway}_unknown"] = 1.0 if state == "unknown" else 0.0
    return f


def persistence_forecast(latest_stage):
    return float(latest_stage)


def trend_forecast(latest_stage, change, window_hours, horizon_hours, shrink, cap_per_hour):
    if latest_stage is None or change is None:
        return None
    slope = float(change) / float(window_hours)
    bounded = max(-float(cap_per_hour), min(float(cap_per_hour), slope))
    return float(latest_stage) + bounded * float(shrink) * float(horizon_hours)


def assign_split(issue_time, target_time, boundary=BOUNDARY, lookback_hours=LOOKBACK_HOURS,
                 embargo_hours=EMBARGO_HOURS, archive_start=ARCHIVE_START):
    feature_start = issue_time - dt.timedelta(hours=lookback_hours)
    if (feature_start >= archive_start + dt.timedelta(hours=lookback_hours)
            and target_time < boundary - dt.timedelta(hours=embargo_hours)):
        return "calibration"
    if feature_start >= boundary + dt.timedelta(hours=embargo_hours):
        return "holdout"
    return "excluded_split_seam"


def metric_bundle(actual, predicted, persistence=None):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = np.isfinite(actual) & np.isfinite(predicted)
    if persistence is not None:
        baseline = np.asarray(persistence, dtype=float)
        mask &= np.isfinite(baseline)
    if not np.any(mask):
        return dict(n=0, mae_ft=None, rmse_ft=None, bias_ft=None,
                    mae_skill_vs_persistence=None, skill_status="no_paired_cases")
    error = predicted[mask] - actual[mask]
    mae = float(np.mean(np.abs(error)))
    out = dict(n=int(mask.sum()), mae_ft=mae,
               rmse_ft=float(np.sqrt(np.mean(error * error))),
               bias_ft=float(np.mean(error)),
               abs_error_p50_ft=float(np.quantile(np.abs(error), .5)),
               abs_error_p90_ft=float(np.quantile(np.abs(error), .9)),
               signed_error_p05_ft=float(np.quantile(error, .05)),
               signed_error_p95_ft=float(np.quantile(error, .95)))
    if persistence is None:
        out.update(mae_skill_vs_persistence=None, skill_status="not_applicable")
    else:
        baseline_mae = float(np.mean(np.abs(baseline[mask] - actual[mask])))
        out["persistence_mae_ft"] = baseline_mae
        if baseline_mae == 0:
            out.update(mae_skill_vs_persistence=None, skill_status="zero_persistence_mae")
        else:
            out.update(mae_skill_vs_persistence=1.0 - mae / baseline_mae,
                       skill_status="computed")
    return out


def paired_rows(rows, method_columns):
    """Use precisely the same issue/target rows for every method comparison."""
    result = []
    for row in rows:
        if not finite_number(row.get("actual_gage_height_ft")):
            continue
        if all(finite_number(row.get(name)) for name in method_columns):
            result.append(row)
    return result


def fit_ridge(x, y, feature_names, alpha=DEFAULT_ALPHA, target_clip=(.01, .99)):
    """Fit standardized ridge regression with training-only imputation.

    Missingness indicators are fitted alongside median-imputed values. All
    transformation state is stored so a report can audit each missing input.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 2 or x.shape[0] != y.shape[0] or x.shape[1] != len(feature_names):
        raise ValueError("Ridge training arrays do not align")
    if x.shape[0] < 2 or not np.all(np.isfinite(y)):
        raise ValueError("Ridge requires at least two finite training targets")
    observed = np.isfinite(x)
    medians = np.zeros(x.shape[1], dtype=float)
    for j in range(x.shape[1]):
        vals = x[observed[:, j], j]
        medians[j] = float(np.median(vals)) if len(vals) else 0.0
    imputed = np.where(observed, x, medians)
    means = np.mean(imputed, axis=0)
    scales = np.std(imputed, axis=0)
    scales[scales < 1e-12] = 1.0
    values_z = (imputed - means) / scales
    flags = (~observed).astype(float)
    flag_means = np.mean(flags, axis=0)
    flag_scales = np.std(flags, axis=0)
    flag_scales[flag_scales < 1e-12] = 1.0
    flags_z = (flags - flag_means) / flag_scales
    design = np.concatenate((values_z, flags_z), axis=1)
    variances = np.std(design, axis=0)
    active = variances >= 1e-12
    design = design[:, active]
    design = np.column_stack((np.ones(len(y)), design))
    gram = design.T @ design
    rhs = design.T @ y
    penalty = np.eye(gram.shape[0]) * float(alpha)
    penalty[0, 0] = 0.0
    try:
        coefficients = np.linalg.solve(gram + penalty, rhs)
    except np.linalg.LinAlgError:
        coefficients = np.linalg.lstsq(gram + penalty, rhs, rcond=None)[0]
    low, high = np.quantile(y, target_clip)
    return dict(feature_names=list(feature_names), medians=medians, means=means,
                scales=scales, flag_means=flag_means, flag_scales=flag_scales,
                active=active, coefficients=coefficients, alpha=float(alpha),
                target_low=float(low), target_high=float(high), train_count=len(y),
                target_clip_quantiles=list(target_clip))


def predict_ridge(model, x):
    x = np.asarray(x, dtype=float)
    observed = np.isfinite(x)
    imputed = np.where(observed, x, model["medians"])
    values_z = (imputed - model["means"]) / model["scales"]
    flags = (~observed).astype(float)
    flags_z = (flags - model["flag_means"]) / model["flag_scales"]
    design = np.concatenate((values_z, flags_z), axis=1)[:, model["active"]]
    delta = model["coefficients"][0] + design @ model["coefficients"][1:]
    delta = np.clip(delta, model["target_low"], model["target_high"])
    return delta, np.sum(~observed, axis=1).astype(int)


class Fenwick:
    """Order-statistic multiset for causal expanding calibration quantiles."""
    def __init__(self, size):
        self.tree = [0] * (size + 1)
        self.size = size
        self.count = 0

    def add(self, index):
        self.count += 1
        i = index + 1
        while i <= self.size:
            self.tree[i] += 1
            i += i & -i

    def kth(self, order):
        """Return zero-based rank `order` among inserted values."""
        if order < 0 or order >= self.count:
            raise IndexError(order)
        index = 0
        bit = 1 << (self.size.bit_length() - 1)
        remaining = order + 1
        while bit:
            nxt = index + bit
            if nxt <= self.size and self.tree[nxt] < remaining:
                index = nxt
                remaining -= self.tree[nxt]
            bit >>= 1
        return index


def causal_discharge_thresholds(index, issues, minimum_samples=1000):
    """Expanding pre-issue calibration q90, frozen at the embargoed split.

    Coordinate compression includes only calibration-era values. Future
    values are never inserted into the order statistic; holdout uses the final
    calibration q90. The 20,000-cfs fallback matches the frozen Phase 4 rule.
    """
    cutoff = BOUNDARY - dt.timedelta(hours=EMBARGO_HOURS)
    samples = sorted((time, float(row["value"]))
                     for time, row in index.get(("DENL1", "discharge"), {}).items()
                     if ARCHIVE_START <= time < cutoff and valid_observation(row, "cfs", "native"))
    values = sorted({value for _, value in samples})
    ranks = {value: i for i, value in enumerate(values)}
    tree = Fenwick(len(values))
    result = {}
    cursor = 0
    for issue in sorted(issues):
        end = min(issue, cutoff)
        while cursor < len(samples) and samples[cursor][0] + HOUR <= end:
            tree.add(ranks[samples[cursor][1]])
            cursor += 1
        if tree.count < minimum_samples:
            threshold = evidence.DEFAULTS["discharge_high_cfs"]
        else:
            position = (tree.count - 1) * .9
            lo, hi = math.floor(position), math.ceil(position)
            lower = values[tree.kth(lo)]
            upper = values[tree.kth(hi)]
            threshold = lower + (upper - lower) * (position - lo)
        result[issue] = dict(discharge_high_cfs=threshold,
                             training_end_exclusive_utc=iso(end),
                             sample_hours=tree.count,
                             method="prior calibration-era upper decile; 20,000-cfs fallback before 1,000 prior hours")
    return result


def rolling_slope_cap(values, quantile=.99):
    values = np.asarray(values, dtype=float)
    values = np.abs(values[np.isfinite(values)])
    return float(np.quantile(values, quantile)) if len(values) else .02


def cv_fold_bounds(year):
    start = dt.datetime(year, 1, 1, tzinfo=UTC)
    end = dt.datetime(year + 1, 1, 1, tzinfo=UTC)
    return start, end


def _feature_indices(model_name):
    if model_name not in MODEL_GROUPS:
        raise KeyError(model_name)
    groups = set(MODEL_GROUPS[model_name])
    return [i for i, name in enumerate(FEATURE_NAMES) if FEATURE_GROUPS[name] in groups]


def _calendar_key(issue):
    return issue.strftime("%Y-%m")


def _quantile_positive_rise(values, q=.9, fallback=.1):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]
    return float(np.quantile(values, q)) if len(values) else float(fallback)


def _feature_data(root):
    root = pathlib.Path(root)
    archive_root = root / "site/data/history" if (root / "site/data/history/hourly").exists() else root
    index = phase4.load_inputs(archive_root, quality_mode="causal")
    observation_keys = tuple(EXPECTED)
    observed_times = [time for key in observation_keys
                      for time, row in index.get(key, {}).items()
                      if valid_observation(row, EXPECTED[key])]
    if not observed_times:
        raise ValueError("No usable historical predictor observations in the frozen hourly archive")
    first, last = min(observed_times), max(observed_times)
    issues = []
    cursor = first + HOUR
    stop = last + HOUR
    while cursor <= stop:
        issues.append(cursor)
        cursor += HOUR

    thresholds = causal_discharge_thresholds(index, issues)
    feature_rows = []
    phase4_categories = []
    phase4_states = []
    phase4_metrics = []
    for issue in issues:
        threshold = thresholds[issue]
        assessment = evidence.assess(index, issue, threshold)
        feature_rows.append(issue_features(index, issue, threshold, assessment))
        phase4_categories.append(assessment["category"])
        phase4_states.append(dict(river=assessment["flags"]["river"],
                                  coastal=assessment["flags"]["coastal"]))
        phase4_metrics.append(dict(threshold_cfs=threshold["discharge_high_cfs"],
                                   calibration_hours=threshold["sample_hours"]))

    x = np.asarray([[row[name] if row[name] is not None else np.nan for name in FEATURE_NAMES]
                    for row in feature_rows], dtype=float)
    current = x[:, FEATURE_NAMES.index("maul1_stage_native_ft")]
    issue_hours = np.asarray([int(value.timestamp() // 3600) for value in issues], dtype=np.int64)
    target_values = {}
    target_reasons = {}
    for horizon in HORIZONS:
        values = np.full(len(issues), np.nan)
        reasons = []
        key = ("MAUL1", "stage")
        series = index.get(key, {})
        for i, issue in enumerate(issues):
            valid_time = issue + dt.timedelta(hours=horizon)
            target = series.get(valid_time)
            if valid_time > last:
                reasons.append("beyond_archived_observations")
            elif target is None or target.get("value") is None or target.get("missing"):
                reasons.append("missing_target_observation")
            elif target.get("unit") != "ft" or target.get("datum") != "gage height":
                reasons.append("target_unit_or_datum_unverified")
            elif target.get("phase4_quality_excluded"):
                reasons.append("target_causal_quality_screen")
            elif not valid_observation(target, "ft", "gage height"):
                reasons.append("invalid_target_observation")
            else:
                values[i] = float(target["value"])
                reasons.append("observed")
        target_values[horizon] = values
        target_reasons[horizon] = reasons

    validation = json.loads((archive_root / "phase3b/validation.json").read_text())
    response_intervals = []
    for event in validation.get("maul1_first_analysis", {}).get("events", []):
        if not event.get("onset_utc") or not event.get("recovery_end_utc"):
            continue
        response_intervals.append((stamp(event["onset_utc"]), stamp(event["recovery_end_utc"]), event["event_id"]))
    response_intervals.sort()
    response_ids = []
    response_mask = np.zeros(len(issues), dtype=bool)
    for i, issue in enumerate(issues):
        ids = [event_id for start, end, event_id in response_intervals if start <= issue <= end]
        response_ids.append(ids)
        response_mask[i] = bool(ids)

    cases_file = json.loads((archive_root / "phase3b/cases.json").read_text())
    case_windows = []
    for case in cases_file.get("cases", []):
        case_windows.append(dict(case_id=case["event_id"], name=case["name"],
                                 start=stamp(case["start_utc"]), end=stamp(case["end_utc_exclusive"])))

    features_table = dict(
        issues=issues, feature_rows=feature_rows, x=x, feature_names=FEATURE_NAMES,
        phase4_categories=phase4_categories, phase4_states=phase4_states,
        phase4_metrics=phase4_metrics, target_values=target_values,
        target_reasons=target_reasons, current=current, issue_hours=issue_hours,
        response_ids=response_ids, response_mask=response_mask,
        response_intervals=response_intervals, case_windows=case_windows,
        archive_first_observation=first, archive_last_observation=last,
        discharge_thresholds=thresholds,
    )
    return index, features_table


def _delta_targets(features, horizon):
    actual = features["target_values"][horizon]
    current = features["current"]
    result = actual - current
    result[~(np.isfinite(actual) & np.isfinite(current))] = np.nan
    return result


def _target_times(issue_hours, horizon):
    return issue_hours + int(horizon)


def _training_mask(features, target, horizon, cutoff_hour, min_hour=None):
    issue_hours = features["issue_hours"]
    target_hours = _target_times(issue_hours, horizon)
    feature_start = issue_hours - LOOKBACK_HOURS
    mask = np.isfinite(target) & np.isfinite(features["current"])
    mask &= target_hours < cutoff_hour
    mask &= feature_start >= int(ARCHIVE_START.timestamp() // 3600) + LOOKBACK_HOURS
    if min_hour is not None:
        mask &= issue_hours >= min_hour
    return mask


def _validation_mask(features, target, year):
    start, end = cv_fold_bounds(year)
    start_hour = int(start.timestamp() // 3600)
    end_hour = int(end.timestamp() // 3600)
    issue_hours = features["issue_hours"]
    mask = np.isfinite(target) & np.isfinite(features["current"])
    mask &= issue_hours >= start_hour + LOOKBACK_HOURS + EMBARGO_HOURS
    mask &= issue_hours < end_hour
    return mask


def _trend_grid_predict(features, indices, horizon, window, shrink, cap):
    delta_name = f"maul1_change_{window}h_ft"
    delta = features["x"][indices, FEATURE_NAMES.index(delta_name)]
    current = features["current"][indices]
    valid = np.isfinite(delta) & np.isfinite(current)
    output = np.full(len(indices), np.nan)
    slope = delta[valid] / float(window)
    output[valid] = current[valid] + np.clip(slope, -cap, cap) * shrink * horizon
    return output


def _train_cutoff_hour(year):
    start, _ = cv_fold_bounds(year)
    return int((start - dt.timedelta(hours=EMBARGO_HOURS)).timestamp() // 3600)


def _fit_predict_fold(features, target, horizon, year, model_name, alpha):
    cutoff = _train_cutoff_hour(year)
    train_mask = _training_mask(features, target, horizon, cutoff)
    val_mask = _validation_mask(features, target, year)
    train_ix = np.flatnonzero(train_mask)
    val_ix = np.flatnonzero(val_mask)
    if len(train_ix) < 500 or not len(val_ix):
        return None
    cols = _feature_indices(model_name)
    model = fit_ridge(features["x"][train_ix][:, cols], target[train_ix],
                      [FEATURE_NAMES[i] for i in cols], alpha)
    delta, missing = predict_ridge(model, features["x"][val_ix][:, cols])
    prediction = features["current"][val_ix] + delta
    actual = features["target_values"][horizon][val_ix]
    return dict(train_n=len(train_ix), validation_n=len(val_ix), indices=val_ix,
                predicted=prediction, actual=actual, missing=missing)


def select_model_parameters(features, years=range(2017, 2023)):
    """Blocked forward CV; every fold trains strictly before its validation year."""
    years = list(years)
    scores = {name: {h: {str(a): [] for a in ALPHAS} for h in HORIZONS}
              for name in MODEL_GROUPS}
    trend_scores = {h: {f"{w}:{s:g}": [] for w in (3, 6, 12, 24) for s in (.25, .5, .75, 1.0)}
                    for h in HORIZONS}
    folds = []
    for year in years:
        fold_record = dict(year=year, horizons={})
        for horizon in HORIZONS:
            target = _delta_targets(features, horizon)
            val_mask = _validation_mask(features, target, year)
            n_val = int(val_mask.sum())
            cutoff = _train_cutoff_hour(year)
            train_n = int(_training_mask(features, target, horizon, cutoff).sum())
            fold_record["horizons"][str(horizon)] = dict(train_n=train_n, validation_n=n_val)
            val_ix = np.flatnonzero(val_mask)
            if train_n < 500 or not n_val:
                continue
            actual = features["target_values"][horizon][val_ix]
            current = features["current"][val_ix]
            for name in MODEL_GROUPS:
                for alpha in ALPHAS:
                    pred = _fit_predict_fold(features, target, horizon, year, name, alpha)
                    if pred:
                        errors = np.abs(pred["predicted"] - pred["actual"])
                        finite = np.isfinite(errors)
                        if finite.any():
                            scores[name][horizon][str(alpha)].append(dict(year=year,
                                sum_abs_error=float(errors[finite].sum()), n=int(finite.sum())))
            train_ix = np.flatnonzero(_training_mask(features, target, horizon, cutoff))
            for window in (3, 6, 12, 24):
                delta_col = features["x"][:, FEATURE_NAMES.index(f"maul1_change_{window}h_ft")]
                train_slope = delta_col[train_ix] / float(window)
                cap = rolling_slope_cap(train_slope)
                for shrink in (.25, .5, .75, 1.0):
                    pred = _trend_grid_predict(features, val_ix, horizon, window, shrink, cap)
                    valid = np.isfinite(pred) & np.isfinite(actual)
                    if valid.any():
                        errors = np.abs(pred[valid] - actual[valid])
                        trend_scores[horizon][f"{window}:{shrink:g}"].append(dict(year=year,
                            sum_abs_error=float(errors.sum()), n=int(len(errors)), cap_per_hour=cap))
        folds.append(fold_record)

    selected = {name: {} for name in MODEL_GROUPS}
    cv_summary = dict(schema_version=SCHEMA_VERSION, years=years, folds=folds,
                      alpha_grid=list(ALPHAS), trend_grid_windows_hours=[3, 6, 12, 24],
                      trend_grid_shrink=[.25, .5, .75, 1.0], models={}, trend={})
    for name in MODEL_GROUPS:
        cv_summary["models"][name] = {}
        for horizon in HORIZONS:
            aggregate = {}
            for alpha in ALPHAS:
                points = scores[name][horizon][str(alpha)]
                n = sum(x["n"] for x in points)
                mae = sum(x["sum_abs_error"] for x in points) / n if n else None
                aggregate[str(alpha)] = dict(n=n, pooled_mae_ft=mae, folds=points)
            viable = [(value["pooled_mae_ft"], float(alpha)) for alpha, value in aggregate.items()
                      if value["pooled_mae_ft"] is not None]
            selected[name][horizon] = min(viable)[1] if viable else DEFAULT_ALPHA
            cv_summary["models"][name][str(horizon)] = dict(
                selected_alpha=selected[name][horizon], by_alpha=aggregate,
                selection="minimum pooled forward-fold MAE within calibration; not an independent estimate")
    trend_selected = {}
    for horizon in HORIZONS:
        aggregate = {}
        for key, points in trend_scores[horizon].items():
            n = sum(x["n"] for x in points)
            mae = sum(x["sum_abs_error"] for x in points) / n if n else None
            aggregate[key] = dict(n=n, pooled_mae_ft=mae, folds=points)
        viable = [(v["pooled_mae_ft"], key) for key, v in aggregate.items() if v["pooled_mae_ft"] is not None]
        if viable:
            _, chosen = min(viable)
            window, shrink = chosen.split(":")
            trend_selected[horizon] = dict(window_hours=int(window), shrink=float(shrink))
        else:
            trend_selected[horizon] = dict(window_hours=DEFAULT_TREND_WINDOW, shrink=DEFAULT_TREND_SHRINK)
        cv_summary["trend"][str(horizon)] = dict(selected=trend_selected[horizon], by_setting=aggregate,
            selection="minimum pooled forward-fold MAE within calibration; cap is each fold's training q99 slope")
    return selected, trend_selected, cv_summary, scores, trend_scores


def _parameters_before_year(year, model_scores, trend_scores, horizon):
    prior_years = [y for y in range(2017, year) if y < 2023]
    if not prior_years:
        return ({name: DEFAULT_ALPHA for name in MODEL_GROUPS},
                dict(window_hours=DEFAULT_TREND_WINDOW, shrink=DEFAULT_TREND_SHRINK))
    alpha_result = {}
    for name in MODEL_GROUPS:
        candidates = []
        for alpha in ALPHAS:
            points = [x for x in model_scores[name][horizon][str(alpha)] if x["year"] in prior_years]
            n = sum(x["n"] for x in points)
            if n:
                mae = sum(x["sum_abs_error"] for x in points) / n
                candidates.append((mae, alpha))
        alpha_result[name] = min(candidates)[1] if candidates else DEFAULT_ALPHA
    trend_candidates = []
    for key, points in trend_scores[horizon].items():
        points = [x for x in points if x["year"] in prior_years]
        n = sum(x["n"] for x in points)
        if n:
            mae = sum(x["sum_abs_error"] for x in points) / n
            trend_candidates.append((mae, key))
    if trend_candidates:
        _, key = min(trend_candidates)
        window, shrink = key.split(":")
        trend = dict(window_hours=int(window), shrink=float(shrink))
    else:
        trend = dict(window_hours=DEFAULT_TREND_WINDOW, shrink=DEFAULT_TREND_SHRINK)
    return alpha_result, trend


def _fit_block(features, horizon, train_mask, alpha_by_model, trend_setting):
    train_ix = np.flatnonzero(train_mask)
    result = dict(train_n=len(train_ix), models={}, trend={})
    if len(train_ix) < 500:
        return result
    target = _delta_targets(features, horizon)
    for name, alpha in alpha_by_model.items():
        cols = _feature_indices(name)
        model = fit_ridge(features["x"][train_ix][:, cols], target[train_ix],
                          [FEATURE_NAMES[i] for i in cols], alpha)
        result["models"][name] = model
    window = trend_setting["window_hours"]
    slope_values = features["x"][train_ix, FEATURE_NAMES.index(f"maul1_change_{window}h_ft")] / float(window)
    result["trend"] = dict(window_hours=window, shrink=trend_setting["shrink"],
                           cap_per_hour=rolling_slope_cap(slope_values),
                           training_slope_count=int(np.isfinite(slope_values).sum()))
    return result


def _new_prediction_arrays(n):
    return {h: {name: np.full(n, np.nan) for name in MODEL_NAMES} for h in HORIZONS}


def _new_status_arrays(n):
    return {h: {name: np.full(n, "no_current_MAUL1_stage", dtype=object)
                for name in MODEL_NAMES} for h in HORIZONS}


def _new_missing_arrays(n):
    return {h: {name: np.zeros(n, dtype=np.int16) for name in MODEL_NAMES} for h in HORIZONS}


def _apply_block(features, indices, horizon, block, predictions, statuses, missing_arrays):
    current = features["current"][indices]
    current_ok = np.isfinite(current)
    predictions[horizon]["persistence"][indices[current_ok]] = current[current_ok]
    statuses[horizon]["persistence"][indices[current_ok]] = "predicted"
    statuses[horizon]["persistence"][indices[~current_ok]] = "no_current_MAUL1_stage"
    setting = block.get("trend") or {}
    if setting:
        window = setting["window_hours"]
        delta = features["x"][indices, FEATURE_NAMES.index(f"maul1_change_{window}h_ft")]
        ok = current_ok & np.isfinite(delta)
        predictions[horizon]["stage_trend"][indices[ok]] = np.asarray([
            trend_forecast(current[i], delta[i], window, horizon, setting["shrink"], setting["cap_per_hour"])
            for i in np.flatnonzero(ok)], dtype=float)
        statuses[horizon]["stage_trend"][indices[current_ok & ~np.isfinite(delta)]] = "missing_trend_window"
        statuses[horizon]["stage_trend"][indices[~current_ok]] = "no_current_MAUL1_stage"
        statuses[horizon]["stage_trend"][indices[ok]] = np.where(
            np.isnan(features["x"][indices[ok], FEATURE_NAMES.index("maul1_change_1h_ft")]),
            "predicted_with_feature_gaps", "predicted")
    else:
        statuses[horizon]["stage_trend"][indices] = "insufficient_pre_issue_training"
    for name in MODEL_GROUPS:
        model = block.get("models", {}).get(name)
        if model is None:
            statuses[horizon][name][indices] = "insufficient_pre_issue_training"
            continue
        cols = _feature_indices(name)
        delta, miss_count = predict_ridge(model, features["x"][indices][:, cols])
        forecast = current + delta
        ok = current_ok & np.isfinite(forecast)
        predictions[horizon][name][indices[ok]] = forecast[ok]
        missing_arrays[horizon][name][indices] = miss_count
        statuses[horizon][name][indices[~current_ok]] = "no_current_MAUL1_stage"
        statuses[horizon][name][indices[ok]] = np.where(miss_count[ok] > 0,
            "predicted_with_training_median_imputation", "predicted")


def _make_predictions(features, selected, trend_selected, model_scores, trend_scores, final_blocks):
    n = len(features["issues"])
    predictions = _new_prediction_arrays(n)
    statuses = _new_status_arrays(n)
    missing_arrays = _new_missing_arrays(n)
    update_metadata = []
    issue_months = defaultdict(list)
    for i, issue in enumerate(features["issues"]):
        issue_months[issue.strftime("%Y-%m")].append(i)
    for month, indices_list in sorted(issue_months.items()):
        year, number = map(int, month.split("-"))
        month_start = dt.datetime(year, number, 1, tzinfo=UTC)
        month_start_hour = int(month_start.timestamp() // 3600)
        idx = np.asarray(indices_list, dtype=int)
        for horizon in HORIZONS:
            if month_start < BOUNDARY:
                alpha_by_model, trend_setting = _parameters_before_year(year, model_scores, trend_scores, horizon)
                target = _delta_targets(features, horizon)
                cutoff = month_start_hour - EMBARGO_HOURS
                train = _training_mask(features, target, horizon, cutoff)
                block = _fit_block(features, horizon, train, alpha_by_model, trend_setting)
                update_metadata.append(dict(period=month, horizon_hours=horizon,
                    training_end_exclusive_utc=iso(month_start-dt.timedelta(hours=EMBARGO_HOURS)),
                    training_n=block["train_n"], alpha=alpha_by_model,
                    trend=block.get("trend", {}), strategy="expanding prior-only monthly refit"))
            else:
                block = final_blocks[horizon]
                update_metadata.append(dict(period=month, horizon_hours=horizon,
                    training_end_exclusive_utc=iso(BOUNDARY-dt.timedelta(hours=EMBARGO_HOURS)),
                    training_n=block["train_n"], alpha=selected,
                    trend=block.get("trend", {}), strategy="single frozen calibration fit for holdout"))
            _apply_block(features, idx, horizon, block, predictions, statuses, missing_arrays)
    return predictions, statuses, missing_arrays, update_metadata


def _bootstrap_skill(actual, forecast, baseline, seed=RANDOM_SEED, replicates=BOOTSTRAP_REPLICATES):
    """Seven-day moving-block interval for paired MAE skill."""
    actual = np.asarray(actual, float)
    forecast = np.asarray(forecast, float)
    baseline = np.asarray(baseline, float)
    valid = np.isfinite(actual) & np.isfinite(forecast) & np.isfinite(baseline)
    n = len(actual)
    if int(valid.sum()) < 2 or np.mean(np.abs(baseline[valid]-actual[valid])) <= 0:
        return dict(lower_95=None, upper_95=None, replicates=0, status="insufficient_or_zero_baseline")
    rng = np.random.default_rng(seed)
    block = min(BOOTSTRAP_BLOCK_HOURS, n)
    skills = []
    blocks_needed = math.ceil(n/block)
    starts = np.arange(n)
    for _ in range(replicates):
        ix = np.concatenate([(s + np.arange(block)) % n for s in rng.choice(starts, blocks_needed)])[:n]
        paired = valid[ix]
        if int(paired.sum()) < 2: continue
        denom = np.mean(np.abs(baseline[ix][paired]-actual[ix][paired]))
        if denom > 0:
            skills.append(1.0 - np.mean(np.abs(forecast[ix][paired]-actual[ix][paired]))/denom)
    return dict(lower_95=float(np.quantile(skills,.025)), upper_95=float(np.quantile(skills,.975)),
                replicates=len(skills), block_hours=BOOTSTRAP_BLOCK_HOURS, status="computed")


def _jsonable(value):
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, np.ndarray): return _jsonable(value.tolist())
    if isinstance(value, (dt.datetime,)): return iso(value)
    if isinstance(value, dict): return {str(k): _jsonable(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [_jsonable(v) for v in value]
    return value


def _write_json(path, data):
    path.write_text(json.dumps(_jsonable(data), indent=2, sort_keys=True, allow_nan=False)+"\n")


def _write_tables(outdir, features, predictions, statuses, missing):
    pred_path = outdir / "predictions.csv.gz"
    fields = ["issue_time_utc","split","horizon_hours","target_time_utc","actual_gage_height_ft","target_status",
              "phase4_category","phase4_river","phase4_coastal"]
    for name in MODEL_NAMES: fields += [METHOD_COLUMNS[name], f"{name}_status",f"{name}_imputed_feature_count"]
    with gzip.open(pred_path,"wt",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for i,issue in enumerate(features["issues"]):
            for h in HORIZONS:
                target=features["target_values"][h][i]
                targettime=issue+dt.timedelta(hours=h)
                target_reason=features["target_reasons"][h][i]
                split=assign_split(issue,targettime)
                rec=dict(issue_time_utc=iso(issue),split=split,horizon_hours=h,target_time_utc=iso(targettime),
                    actual_gage_height_ft=target if np.isfinite(target) else "",target_status=target_reason,
                    phase4_category=features["phase4_categories"][i],
                    phase4_river=features["phase4_states"][i]["river"],phase4_coastal=features["phase4_states"][i]["coastal"])
                for name in MODEL_NAMES:
                    p=predictions[h][name][i]
                    rec[METHOD_COLUMNS[name]]=p if np.isfinite(p) else ""
                    rec[f"{name}_status"]=statuses[h][name][i]
                    rec[f"{name}_imputed_feature_count"]=int(missing[h][name][i])
                writer.writerow(rec)
    feat_path=outdir/"features.csv.gz"
    with gzip.open(feat_path,"wt",newline="",encoding="utf-8") as f:
        names=["issue_time_utc","phase4_category","river_state","coastal_state"]+list(FEATURE_NAMES)
        w=csv.DictWriter(f,fieldnames=names); w.writeheader()
        for i,issue in enumerate(features["issues"]):
            rec=dict(issue_time_utc=iso(issue),phase4_category=features["phase4_categories"][i],
                     river_state=features["phase4_states"][i]["river"],coastal_state=features["phase4_states"][i]["coastal"])
            rec.update({k:(v if v is not None else "") for k,v in features["feature_rows"][i].items()})
            w.writerow(rec)
    return pred_path,feat_path


def _evaluation(features, predictions):
    issues=features["issues"]
    hold=np.asarray([assign_split(t,t+dt.timedelta(hours=24))=="holdout" for t in issues])
    results={}
    d6=features["x"][:,FEATURE_NAMES.index("maul1_change_6h_ft")]
    calibration=np.asarray([assign_split(t,t+dt.timedelta(hours=24))=="calibration" for t in issues])
    calrise=d6[calibration & np.isfinite(d6) & (d6>0)]
    rise_q90=float(np.quantile(calrise,.9)) if len(calrise) else .1
    calabs=np.abs(d6[calibration & np.isfinite(d6)])
    quiet_q25=float(np.quantile(calabs,.25)) if len(calabs) else .1
    strata={
        "prior_rising": (d6>=.1, "Issue-time six-hour MAUL1 rise >= 0.1 ft"),
        "prior_rapid_rising": (d6>=rise_q90, f"Issue-time six-hour rise >= calibration positive-rise q90 ({rise_q90:.4f} ft)"),
        "prior_quiet": (np.abs(d6)<=quiet_q25, f"Issue-time absolute six-hour change <= calibration q25 ({quiet_q25:.4f} ft)"),
        "phase3b_response_window": (features["response_mask"], "Retrospective Phase 3B event windows; evaluation labels only"),
    }
    for category in sorted(set(features["phase4_categories"])):
        strata[f"phase4_{category}"]=(np.asarray([x==category for x in features["phase4_categories"]]),
                                      f"Causal Phase 4 issue-time category: {category}")
    for h in HORIZONS:
        actual=features["target_values"][h]
        # Compare on one shared row set across all requested forecasting methods.
        valid=hold & np.isfinite(actual) & np.isfinite(predictions[h]["persistence"])
        for name in MODEL_NAMES: valid &= np.isfinite(predictions[h][name])
        ix=np.flatnonzero(valid)
        base=predictions[h]["persistence"][ix]
        model_result={}
        for name in MODEL_NAMES:
            forecast=predictions[h][name][ix]
            metrics=metric_bundle(actual[ix],forecast,base)
            hold_ix=np.flatnonzero(hold); ci_start,ci_end=int(hold_ix[0]),int(hold_ix[-1])+1
            ci_actual=actual[ci_start:ci_end]
            ci_forecast=predictions[h][name][ci_start:ci_end]
            ci_base=predictions[h]["persistence"][ci_start:ci_end]
            metrics["skill_block_bootstrap_95"]= _bootstrap_skill(ci_actual,ci_forecast,ci_base)
            model_result[name]=metrics
        outcome=features["target_values"][h]-features["current"]
        strata["future_rising_outcome"]=(outcome>=rise_q90, "Retrospective target-minus-issue stage change >= calibration q90; evaluation only")
        strata["future_quiet_outcome"]=(np.abs(outcome)<=quiet_q25, "Retrospective absolute target-minus-issue change <= calibration q25; evaluation only")
        stratified={}
        for name,(condition,definition) in strata.items():
            group_ix=np.flatnonzero(valid & condition)
            stratified[name]={"definition":definition,"paired_sample_n":len(group_ix),"methods":{
                method:metric_bundle(actual[group_ix],predictions[h][method][group_ix],predictions[h]["persistence"][group_ix])
                for method in MODEL_NAMES}}
        results[str(h)]=dict(paired_sample_n=len(ix),methods=model_result,strata=stratified,
                             target_valid_n=int(np.sum(hold & np.isfinite(actual))),
                             holdout_issue_n=int(hold.sum()))
    return results


def _plot_svg(path, series, title):
    width,height=900,430; margin=65
    all_values=np.concatenate([np.asarray(v,float) for v in series.values()]) if series else np.asarray([])
    finite=np.isfinite(all_values)
    if not finite.any():
        lo,hi=0.,1.
    else: lo=float(np.min(all_values[finite])); hi=float(np.max(all_values[finite]));
    if hi<=lo: hi=lo+1
    colors={"observed":"#202020","persistence":"#777777","stage_trend":"#d97706","maul1_only":"#16697a","maul1_plus_river":"#5b8c5a","maul1_plus_coastal":"#7b61a8","maul1_all":"#c44e52"}
    elements=[]
    n=max((len(v) for v in series.values()),default=0)
    for name,values in series.items():
        values=np.asarray(values,float); points=[]
        for x,y in enumerate(values):
            if np.isfinite(y): points.append(f"{margin+x*(width-2*margin)/max(1,n-1):.1f},{height-margin-(y-lo)*(height-2*margin)/(hi-lo):.1f}")
        elements.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{colors.get(name,"#444444")}" stroke-width="{2.4 if name=="observed" else 1.5}" opacity="{1 if name=="observed" else .8}"/>')
    legend=" · ".join(series.keys()).replace("&","&amp;").replace("<","&lt;")
    path.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/><text x="{width/2}" y="30" text-anchor="middle" font-family="sans-serif" font-size="18">{title}</text><path d="M {margin} {margin} V {height-margin} H {width-margin}" fill="none" stroke="#555"/>{''.join(elements)}<text x="{margin}" y="{height-34}" font-family="sans-serif" font-size="11">{legend}</text><text x="{margin}" y="{height-18}" font-family="sans-serif" font-size="12">Valid time ordered hourly issue sequence; native MAUL1 gage-height ft</text></svg>''',encoding="utf-8")


def run(root, outdir):
    """Build all causal hindcasts and machine-readable scientific reports."""
    root=pathlib.Path(root); archive_root=root/"site/data/history" if (root/"site/data/history/hourly").exists() else root
    outdir=pathlib.Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    index, features=_feature_data(root)
    selected,trend_selected,cv,model_scores,trend_scores=select_model_parameters(features)
    final_blocks={}
    boundary_hour=int(BOUNDARY.timestamp()//3600)
    for h in HORIZONS:
        target=_delta_targets(features,h)
        train=_training_mask(features,target,h,boundary_hour-EMBARGO_HOURS)
        alpha={name:selected[name][h] for name in MODEL_GROUPS}
        final_blocks[h]=_fit_block(features,h,train,alpha,trend_selected[h])
    preds,statuses,missing,updates=_make_predictions(features,selected,trend_selected,model_scores,trend_scores,final_blocks)
    verification=_evaluation(features,preds)
    _write_tables(outdir,features,preds,statuses,missing)
    # Causal calibration residuals define central 80% interval half-widths; holdout coverage is evaluated separately.
    uncertainty={}
    cases=[]
    for h in HORIZONS:
        uncertainty[str(h)]={}
        for name in MODEL_NAMES:
            cal=[]; held=[]
            for i,issue in enumerate(features["issues"]):
                y=features["target_values"][h][i]; p=preds[h][name][i]
                if not (np.isfinite(y) and np.isfinite(p)): continue
                split=assign_split(issue,issue+dt.timedelta(hours=h))
                (cal if split=="calibration" else held if split=="holdout" else []).append(abs(float(y-p)))
            radius=float(np.quantile(cal,.8)) if cal else None
            coverage=float(np.mean(np.asarray(held)<=radius)) if radius is not None and held else None
            uncertainty[str(h)][name]=dict(interval="central 80% empirical absolute-error interval; symmetric around point forecast",
                half_width_ft=radius,calibration_residual_n=len(cal),holdout_coverage=coverage,
                holdout_n=len(held),status="coverage_checked" if held else "no_holdout_residuals")
    for case in features["case_windows"]:
        choose=np.asarray([case["start"]<=t<case["end"] for t in features["issues"]])
        c=dict(case_id=case["case_id"],name=case["name"],start_utc=iso(case["start"]),end_utc_exclusive=iso(case["end"]),
               calibration_or_holdout="calibration (not independent)" if case["end"]<=BOUNDARY else "holdout",horizons={})
        for h in HORIZONS:
            ix=np.flatnonzero(choose & np.isfinite(features["target_values"][h]))
            c["horizons"][str(h)]={"n":len(ix),"actual_gage_height_ft":features["target_values"][h][ix].tolist(),
                "issue_times_utc":[iso(features["issues"][i]) for i in ix],
                "forecasts":{name:preds[h][name][ix].tolist() for name in MODEL_NAMES}}
        cases.append(c)
    summary=dict(schema_version=SCHEMA_VERSION,study="Phase 5A experimental historical hindcast; non-operational",
        target="MAUL1 stage 00065, ft, native gage-height reference (no NAVD88 conversion)",
        horizons_hours=list(HORIZONS),calibration="2016-01 through 2022-12; embargoed target end before 2022-12-29T00Z",
        holdout="2023-01-07 onward; first 72 h of boundary plus 72 h lookback/embargo excluded",
        archive_first_observation_utc=iso(features["archive_first_observation"]),archive_last_observation_utc=iso(features["archive_last_observation"]),
        issue_count=len(features["issues"]),feature_count=len(FEATURE_NAMES),models=list(MODEL_NAMES),
        valid_current_maul1_stage_n=int(np.isfinite(features["current"]).sum()),
        holdout_results=verification,missing_target_counts={str(h):dict((r,int(features["target_reasons"][h].count(r))) for r in set(features["target_reasons"][h])) for h in HORIZONS},
        scope_limitations=["research hindcasts only; not operational guidance", "no flood probabilities or threshold exceedance probabilities",
            "MCHL1 native stage changes are context-only; datum unverified", "event labels are retrospective evaluation strata only",
            "holdout is temporal and is not independent of the archive's site/station selection"],
        next_phase_recommendations=["Preserve a completely untouched period or external station network for independent replication.",
            "Test robustness to alternative issue-time availability, datum continuity, and feature-missingness conditions.",
            "Assess interval calibration by season and event regime before considering any operational evaluation.",
            "Keep any later operational study separate from this retrospective research hindcast."])
    _write_json(outdir/"summary.json",summary); _write_json(outdir/"cv.json",cv)
    _write_json(outdir/"verification.json",verification); _write_json(outdir/"uncertainty.json",uncertainty)
    _write_json(outdir/"case-studies.json",cases)
    _write_json(outdir/"models.json",dict(selected_alpha=selected,selected_trend=trend_selected,
        final_holdout_fit={str(h):{"training_n":final_blocks[h]["train_n"],"parameters":final_blocks[h]} for h in HORIZONS},
        monthly_prequential_fit_count=len(updates)))
    (outdir/"model-updates.json").write_text(json.dumps(_jsonable(updates),indent=2,sort_keys=True,allow_nan=False)+"\n")
    hashes={}
    for path in sorted((archive_root/"hourly").glob("*.json.gz")):
        hashes[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
    # Provenance paths are repository-relative when run from a checkout.
    hashes={str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((archive_root/"hourly").glob("*.json.gz"))}
    _write_json(outdir/"provenance.json",dict(schema_version=SCHEMA_VERSION,input_files_sha256=hashes,
        phase3b_validation_sha256=hashlib.sha256((archive_root/"phase3b/validation.json").read_bytes()).hexdigest(),
        feature_names=list(FEATURE_NAMES),feature_groups=FEATURE_GROUPS,issue_bin_convention="hour bins labelled by start; use t-1 at issue t",
        phase4_quality_mode="causal",code_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        issue_time_range_utc=[iso(features["issues"][0]),iso(features["issues"][-1])]))
    # Save a small, readable report and plot for each prescribed Phase 3B case.
    for case in cases:
        for h in HORIZONS:
            timeline=case["horizons"][str(h)]
            series={"observed":np.asarray(timeline["actual_gage_height_ft"],float)}
            series.update({name:np.asarray(values,float) for name,values in timeline["forecasts"].items()})
            _plot_svg(outdir/f"case-{case['case_id']}-{h}h.svg",series,f"{case['name']} — {h} h hindcast; native MAUL1 stage")
    lines=["# Phase 5A experimental water-level hindcast", "", summary["target"], "",
        "This is retrospective research evidence, not operational advice or a probability forecast. Models use only completed hourly bins at each issue time. The 2023 onward period is a temporally held-out verification set; calibration case studies are not independent tests.","",
        "## Holdout verification", "", "| Horizon | Model | N (paired) | MAE (ft) | RMSE (ft) | Bias (ft) | MAE skill vs persistence | Skill 95% block interval |", "|---:|---|---:|---:|---:|---:|---:|---|"]
    for hs,group in verification.items():
        for name,m in group["methods"].items():
            ci=m["skill_block_bootstrap_95"]
            cis="unavailable" if ci["lower_95"] is None else f"[{ci['lower_95']:.3f}, {ci['upper_95']:.3f}]"
            lines.append(f"| {hs} h | {name} | {m['n']} | {m['mae_ft']:.4f} | {m['rmse_ft']:.4f} | {m['bias_ft']:.4f} | {m['mae_skill_vs_persistence'] if m['mae_skill_vs_persistence'] is not None else 'n/a'} | {cis} |")
    lines += ["", "## Files", "", "`summary.json`, `cv.json`, `verification.json`, `uncertainty.json`, `case-studies.json`, `models.json`, `provenance.json`, `predictions.csv.gz`, and `features.csv.gz` contain full machine-readable results and issue-level audit data.",""]
    (outdir/"report.md").write_text("\n".join(lines),encoding="utf-8")
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument("--outdir",type=pathlib.Path,default=None)
    args=parser.parse_args(argv)
    output=args.outdir or args.root/"site/data/history/phase5a"
    result=run(args.root,output)
    print(json.dumps({"output":str(output),"issue_count":result["issue_count"],"holdout":result["holdout_results"]},indent=2))


if __name__=="__main__": main()


