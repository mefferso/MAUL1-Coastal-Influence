"""Adapter for the committed Phase 3A hourly archive.

This adapter reads valid-time aggregates only. It retains provenance fields,
marks source coverage below 80% as unusable, and does not infer receipt times.
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
import statistics
from collections import Counter, defaultdict

UTC = dt.timezone.utc
EXPECTED_SAMPLES = {"NWCL1": 10, "MDLL1": 4, "MAUL1": 4, "DENL1": 4}
WIND_KEYS = {("NWCL1", "wind"), ("NWCL1", "wind_direction"),
             ("NWCL1", "wind_u"), ("NWCL1", "wind_v")}
RESPONSE_KEYS = {("NWCL1", "water"), ("NWCL1", "prediction"),
                 ("MDLL1", "stage"), ("MAUL1", "stage"), ("DENL1", "discharge"), ("DENL1", "stage")}


def _time(value):
    stamp = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("archive timestamp is not timezone-aware")
    return stamp.astimezone(UTC)


def record_is_usable(row, min_source_coverage=0.8, expected_samples=None):
    """Apply only machine-readable missing, QC, unit, and source-coverage rules."""
    value = row.get("value")
    if row.get("missing") is True or value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
        return False
    if row.get("valid") is False:
        return False
    if str(row.get("quality", "")).lower() in {"bad", "reject", "rejected", "invalid", "fail"}:
        return False
    station = row.get("station")
    expected = expected_samples or row.get("expected_source_samples") or EXPECTED_SAMPLES.get(station)
    coverage = row.get("coverage")
    if expected is None or not isinstance(coverage, (int, float)) or coverage < min_source_coverage * expected:
        return False
    if not row.get("unit") or row.get("datum") is None:
        return False
    if station == "NWCL1" and row.get("variable") == "wind_direction" and not 0 <= value <= 360:
        return False
    if station == "NWCL1" and row.get("variable") in {"wind", "gust"} and value < 0:
        return False
    return True


def _month_paths(archive_dir, start=None, end=None):
    paths = sorted(pathlib.Path(archive_dir).glob("????-??.json.gz"))
    if start is None and end is None:
        return paths
    start = _time(start) if start is not None else None
    end = _time(end) if end is not None else None
    result = []
    for path in paths:
        year, month = map(int, path.name[:7].split("-"))
        month_start = dt.datetime(year, month, 1, tzinfo=UTC)
        next_month = dt.datetime(year + (month == 12), 1 if month == 12 else month + 1, 1, tzinfo=UTC)
        if (end is None or month_start < end) and (start is None or next_month > start):
            result.append(path)
    return result


def load_hourly_records(archive_dir, start=None, end=None):
    """Read only inputs used by diagnostics and return records plus SHA-256 provenance."""
    selected = WIND_KEYS | RESPONSE_KEYS
    records, hashes = [], {}
    lower = _time(start) if start is not None else None
    upper = _time(end) if end is not None else None
    for path in _month_paths(archive_dir, lower, upper):
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            document = json.load(stream)
        rows_in_month = document.get("records", [])
        coverage_profiles = defaultdict(list)
        for sample in rows_in_month:
            key = (sample.get("station"), sample.get("variable"))
            coverage = sample.get("coverage")
            if key in selected and not sample.get("missing") and sample.get("value") is not None and isinstance(coverage, (int, float)) and coverage > 0:
                coverage_profiles[key].append(int(coverage))
        expected_profiles = {key: Counter(values).most_common(1)[0][0] for key, values in coverage_profiles.items() if values}
        for row in rows_in_month:
            if (row.get("station"), row.get("variable")) not in selected:
                continue
            try:
                stamp = _time(row["time"])
            except (KeyError, TypeError, ValueError):
                continue
            if lower is not None and stamp < lower or upper is not None and stamp >= upper:
                continue
            copied = dict(row)
            key = (row.get("station"), row.get("variable"))
            copied["expected_source_samples"] = expected_profiles.get(key, EXPECTED_SAMPLES.get(row.get("station")))
            copied["valid"] = record_is_usable(copied)
            records.append(copied)
    records.sort(key=lambda item: (item["time"], item["station"], item["variable"]))
    return records, hashes


def combine_wind_records(records):
    """Join NWCL1 speed, direction and U/V only at exact shared hourly timestamps."""
    grouped = defaultdict(list)
    for row in records:
        if (row.get("station"), row.get("variable")) in WIND_KEYS:
            grouped[row.get("time")].append(row)
    output = []
    for stamp, rows in sorted(grouped.items()):
        by_variable = defaultdict(list)
        for row in rows:
            by_variable[row["variable"]].append(row)
        valid = all(len(by_variable[name]) == 1 and by_variable[name][0].get("valid", record_is_usable(by_variable[name][0]))
                    for name in ("wind", "wind_direction", "wind_u", "wind_v"))
        values = {name: by_variable[name][0] for name in by_variable if len(by_variable[name]) == 1}
        output.append({
            "time": stamp, "station": "NWCL1", "valid": valid,
            "speed_knots": values["wind"]["value"] if valid else None,
            "direction_from_deg": values["wind_direction"]["value"] if valid else None,
            "u_east_knots": values["wind_u"]["value"] if valid else None,
            "v_north_knots": values["wind_v"]["value"] if valid else None,
            "coverage": min((item.get("coverage", 0) for item in values.values()), default=0),
            "source": "NOAA CO-OPS station 8761927; hourly archive aggregate",
            "exposure_note": "New Canal shoreline/land exposure; not an open-water lake-wide observation",
        })
    return output


def phase_coverage(records, start, end):
    """Summarize available hourly bins over a half-open phase interval."""
    start, end = _time(start), _time(end)
    expected_hours = int((end - start).total_seconds() // 3600)
    grouped = defaultdict(set)
    for row in records:
        stamp = _time(row["time"])
        if start <= stamp < end and row.get("valid"):
            grouped[(row["station"], row["variable"])].add(stamp)
    result = {}
    for key in sorted(WIND_KEYS | RESPONSE_KEYS):
        count = len(grouped[key])
        result[f"{key[0]}:{key[1]}"] = {"valid_hours": count, "expected_hours": expected_hours,
                                         "coverage_fraction": count / expected_hours if expected_hours else None}
    return result


PROSPECTIVE_REQUIRED_FIELDS = (
    "source_id", "station", "variable", "valid_time_utc", "received_time_utc",
    "value", "unit", "datum", "quality_status",
)

def normalize_prospective_observation(record):
    """Validate a receipt-timestamped observation for future archival adapters.

    This does not connect to or modify any live collector. Both valid time and
    actual local receipt time are required; retrospective bins cannot supply
    the latter.
    """
    missing = [name for name in PROSPECTIVE_REQUIRED_FIELDS if record.get(name) is None]
    if missing:
        raise ValueError("prospective observation missing required fields: " + ", ".join(missing))
    valid_time, received_time = _time(record["valid_time_utc"]), _time(record["received_time_utc"])
    value = record["value"]
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("prospective observation value must be finite numeric data")
    return {**record, "valid_time_utc": valid_time.isoformat().replace("+00:00", "Z"),
            "received_time_utc": received_time.isoformat().replace("+00:00", "Z"),
            "receipt_latency_seconds": (received_time - valid_time).total_seconds()}
