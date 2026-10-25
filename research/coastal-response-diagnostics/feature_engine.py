"""Deterministic hourly wind and same-station response diagnostics.

Wind vectors are flow-to components in knots; stress values are directional
proxies in kt^2, not physical air-sea stress. Missing hours are never filled.
"""
from __future__ import annotations

import datetime as dt
import math
import statistics
from collections import defaultdict

UTC = dt.timezone.utc
HOUR = dt.timedelta(hours=1)
DEFAULT_WINDOWS = (3, 6, 12, 24, 48, 72)
DEFAULT_SECTORS = {"northerly": (337.5, 22.5), "northeasterly": (22.5, 67.5),
                   "easterly": (67.5, 112.5), "southeasterly": (112.5, 157.5),
                   "southerly": (157.5, 202.5), "southwesterly": (202.5, 247.5),
                   "westerly": (247.5, 292.5), "northwesterly": (292.5, 337.5)}


def _time(value):
    if isinstance(value, dt.datetime):
        stamp = value
    else:
        stamp = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return stamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def _valid(record):
    if record.get("valid") is False or record.get("missing") is True:
        return False
    if str(record.get("quality", "")).lower() in {"bad", "reject", "rejected", "invalid", "fail"}:
        return False
    return True


def _unit_vector(speed, direction_from):
    angle = math.radians(direction_from % 360.0)
    return -math.sin(angle), -math.cos(angle)


def _sector_contains(direction, bounds):
    if direction is None:
        return False
    start, end = (float(x) % 360.0 for x in bounds)
    direction %= 360.0
    return start <= direction < end if start <= end else direction >= start or direction < end


def _canonical_wind(records):
    grouped = defaultdict(list)
    for row in records:
        if row.get("station", "NWCL1") != "NWCL1":
            continue
        try:
            stamp = _time(row["time"])
        except (KeyError, TypeError, ValueError):
            continue
        grouped[stamp].append(row)
    if not grouped:
        return []
    result = []
    stamp = min(grouped)
    while stamp <= max(grouped):
        rows = grouped.get(stamp, [])
        row = rows[0] if len(rows) == 1 else {}
        valid = bool(row) and _valid(row)
        speed = row.get("speed_knots", row.get("value") if row.get("variable") in (None, "wind") else None)
        direction = row.get("direction_from_deg")
        if direction is None and row.get("variable") == "wind_direction":
            direction = row.get("value")
        u = row.get("u_east_knots", row.get("wind_u_knots"))
        v = row.get("v_north_knots", row.get("wind_v_knots"))
        if u is None and row.get("wind_u") is not None:
            u = row.get("wind_u")
        if v is None and row.get("wind_v") is not None:
            v = row.get("wind_v")
        if speed is None and _finite(u) and _finite(v):
            speed = math.hypot(u, v)
        if direction is None and _finite(u) and _finite(v) and (u or v):
            direction = math.degrees(math.atan2(-u, -v)) % 360.0
        if not _finite(speed) or speed < 0 or not _finite(direction) or not 0 <= direction <= 360:
            valid = False
        if valid:
            direction = float(direction) % 360.0
            speed = float(speed)
            if not (_finite(u) and _finite(v)):
                unit_u, unit_v = _unit_vector(speed, direction)
                u, v = speed * unit_u, speed * unit_v
            else:
                u, v = float(u), float(v)
            # Preserve the archived vector-mean magnitude; directional cancellation
            # within the hour is observed information, not a normalization error.
            vector_speed = math.hypot(u, v)
            if vector_speed > speed + 0.05 or (speed == 0 and vector_speed > 0.05):
                valid = False
        result.append({"time": stamp, "valid": valid,
                       "speed": speed if valid else None,
                       "direction": direction if valid else None,
                       "u": u if valid else None, "v": v if valid else None,
                       "coverage": row.get("coverage") if row else None})
        stamp += HOUR
    return result


def build_wind_features(records, windows=DEFAULT_WINDOWS, sectors=None,
                        speed_thresholds=(5.0, 10.0, 15.0), min_coverage=0.8,
                        reversal_min_speed_knots=5.0):
    """Return one row per UTC hour with causal trailing wind descriptors.

    Each duration is total qualifying hourly bins inside its trailing window;
    `longest_run` is the longest contiguous qualifying run and missing bins
    break runs. Windows include the timestamp's completed hourly bin.
    """
    if not 0 < min_coverage <= 1:
        raise ValueError("min_coverage must be in (0, 1]")
    if any(int(w) <= 0 for w in windows):
        raise ValueError("windows must be positive whole hours")
    sectors = sectors or DEFAULT_SECTORS
    series = _canonical_wind(records)
    output = []
    for index, item in enumerate(series):
        row = {"time": item["time"].isoformat().replace("+00:00", "Z"),
               "nwcl1_wind_valid": item["valid"],
               "wind_speed_knots": item["speed"],
               "wind_direction_from_deg": item["direction"],
               "wind_u_east_knots": item["u"], "wind_v_north_knots": item["v"],
               "stress_u_proxy_kt2": item["u"] * item["speed"] if item["valid"] else None,
               "stress_v_proxy_kt2": item["v"] * item["speed"] if item["valid"] else None,
               "wind_acceleration_knots_1h": None,
               "wind_relaxation_knots_1h": None,
               "direction_shift_deg_1h": None,
               "direction_reversal_1h": None}
        if index and item["valid"] and series[index - 1]["valid"]:
            previous = series[index - 1]
            delta = ((item["direction"] - previous["direction"] + 180) % 360) - 180
            row["wind_acceleration_knots_1h"] = item["speed"] - previous["speed"]
            row["wind_relaxation_knots_1h"] = max(0.0, previous["speed"] - item["speed"])
            row["direction_shift_deg_1h"] = abs(delta)
            row["direction_reversal_1h"] = bool(abs(delta) >= 150.0 and min(item["speed"], previous["speed"]) >= reversal_min_speed_knots)
        for window in windows:
            start = max(0, index - int(window) + 1)
            bins = series[start:index + 1]
            # A truncated archive edge is not a shorter version of a named window.
            full = len(bins) == int(window)
            valid_bins = [entry for entry in bins if entry["valid"]]
            covered = full and len(valid_bins) / int(window) >= min_coverage
            row[f"wind_coverage_{window}h"] = len(valid_bins) / int(window) if full else None
            for component in ("u", "v"):
                key = "stress_" + component
                value = sum(entry[component] * entry["speed"] for entry in valid_bins) if covered else None
                row[f"integrated_{key}_proxy_{window}h_kt2h"] = value
                row[f"mean_{component}_knots_{window}h"] = statistics.fmean(entry[component] for entry in valid_bins) if covered else None
            total_speed = sum(entry["speed"] for entry in valid_bins)
            resultant = math.hypot(sum(entry["u"] for entry in valid_bins), sum(entry["v"] for entry in valid_bins))
            row[f"directional_persistence_{window}h"] = min(1.0, resultant / total_speed) if covered and total_speed else (0.0 if covered else None)
            for sector, bounds in sectors.items():
                for threshold in speed_thresholds:
                    suffix = f"{sector}_ge{_fmt(threshold)}kt_{window}h"
                    qualifying = [entry["valid"] and entry["speed"] >= threshold and _sector_contains(entry["direction"], bounds) for entry in bins]
                    row[f"duration_{suffix}"] = sum(qualifying) if covered else None
                    longest = run = 0
                    for condition in qualifying:
                        run = run + 1 if condition else 0
                        longest = max(longest, run)
                    row[f"longest_run_{suffix}"] = longest if covered else None
        output.append(row)
    return output


def _valid_value(row):
    value = row.get("value")
    return (_valid(row) and _finite(value) and row.get("unit") is not None
            and row.get("datum") is not None)


def build_response_features(records, change_windows=(1, 3, 6, 12, 24, 48, 72),
                            baseline_hours=72, min_coverage=0.8):
    """Return within-station anomalies/tendencies without cross-datum subtraction.

    The NWCL1 residual is water minus prediction only at exact matching UTC
    time, unit, and datum. MDLL1 and MAUL1 absolute levels are never compared.
    """
    indexed = defaultdict(list)
    for record in records:
        station = record.get("station")
        variable = record.get("variable")
        if station not in {"NWCL1", "MDLL1", "MAUL1", "DENL1"}:
            continue
        if variable not in {"water", "prediction", "stage", "discharge"}:
            continue
        try:
            stamp = _time(record["time"])
        except (KeyError, TypeError, ValueError):
            continue
        indexed[(station, variable, stamp)].append(record)
    if not indexed:
        return []
    start, end = min(key[2] for key in indexed), max(key[2] for key in indexed)

    def get(station, variable, stamp):
        rows = indexed.get((station, variable, stamp), [])
        return rows[0] if len(rows) == 1 and _valid_value(rows[0]) else None

    def exact_delta(station, variable, stamp, hours):
        current, prior = get(station, variable, stamp), get(station, variable, stamp - HOUR * hours)
        if not current or not prior or current.get("unit") != prior.get("unit") or current.get("datum") != prior.get("datum"):
            return None
        if variable == "stage" and (current.get("unit") != "ft" or current.get("datum") != "gage height"):
            return None
        if variable == "discharge" and (current.get("unit") != "cfs" or current.get("datum") != "native"):
            return None
        return float(current["value"]) - float(prior["value"])

    output = []
    stamp = start
    while stamp <= end:
        row = {"time": stamp.isoformat().replace("+00:00", "Z")}
        water, prediction = get("NWCL1", "water", stamp), get("NWCL1", "prediction", stamp)
        residual = None
        if (water and prediction and water.get("unit") == prediction.get("unit") == "ft"
                and water.get("datum") == prediction.get("datum") == "MLLW"):
            residual = float(water["value"]) - float(prediction["value"])
        row["nwcl1_residual_mllw_ft"] = residual
        for hours in change_windows:
            row[f"nwcl1_residual_change_{hours}h_ft"] = _exact_residual_delta(indexed, stamp, hours, get)
            row[f"mdll1_stage_change_{hours}h_ft"] = exact_delta("MDLL1", "stage", stamp, hours)
            row[f"maul1_stage_change_{hours}h_native_ft"] = exact_delta("MAUL1", "stage", stamp, hours)
            row[f"denl1_discharge_change_{hours}h_cfs"] = exact_delta("DENL1", "discharge", stamp, hours)
        for station, name in (("MDLL1", "mdll1"), ("MAUL1", "maul1")):
            current = get(station, "stage", stamp)
            prior_times = [stamp - HOUR * offset for offset in range(1, baseline_hours + 1)]
            prior_rows = [get(station, "stage", prior_time) for prior_time in prior_times]
            valid_prior = [record for record in prior_rows if record]
            enough = len(valid_prior) / baseline_hours >= min_coverage
            compatible = (current and current.get("unit") == "ft" and current.get("datum") == "gage height"
                          and valid_prior and all(record.get("unit") == current.get("unit")
                                                  and record.get("datum") == current.get("datum")
                                                  for record in valid_prior))
            row[f"{name}_stage_anomaly_{baseline_hours}h_native_ft"] = (
                float(current["value"]) - statistics.median(float(item["value"]) for item in valid_prior)
                if enough and compatible else None)
        output.append(row)
        stamp += HOUR
    return output


def _exact_residual_delta(indexed, stamp, hours, get):
    now_water, now_prediction = get("NWCL1", "water", stamp), get("NWCL1", "prediction", stamp)
    then = stamp - HOUR * hours
    old_water, old_prediction = get("NWCL1", "water", then), get("NWCL1", "prediction", then)
    pairs = ((now_water, now_prediction), (old_water, old_prediction))
    if any(not a or not b or a.get("unit") != b.get("unit")
           or a.get("datum") != b.get("datum") or a.get("unit") != "ft" or a.get("datum") != "MLLW" for a, b in pairs):
        return None
    if now_water.get("unit") != old_water.get("unit") or now_water.get("datum") != old_water.get("datum"):
        return None
    return (float(now_water["value"]) - float(now_prediction["value"])) - (float(old_water["value"]) - float(old_prediction["value"]))


def _fmt(value):
    return str(int(value)) if float(value).is_integer() else str(value).replace(".", "p")
