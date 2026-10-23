"""Create a separate, provenance-preserving clean experimental hourly archive.

Only certain machine-readable invalid values are removed. Statistical jumps and
large but finite stage/discharge values are retained for source-level review;
they are not automatically treated as bad hydrology.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib

KNOWN_HADS_SENTINEL = 9_999_999.0
DERIVED_CORRUPTION_LIMIT = 1_000_000.0
STATIONS = ("DENL1", "NWCL1", "MDLL1", "MCHL1", "MAUL1")
MEASURED_VARIABLES = {"stage", "water", "discharge", "prediction", "wind", "wind_direction",
                      "wind_u", "wind_v", "gust"}


def clean_record(record):
    """Return a copied row and conservative, explicit cleaning reasons."""
    cleaned = dict(record)
    value = record.get("value")
    reasons = []
    if isinstance(value, (int, float)) and not math.isfinite(value):
        reasons.append("non_finite_numeric_value")
    elif (record.get("station") == "MCHL1" and record.get("variable") == "stage"
          and isinstance(value, (int, float)) and abs(value) >= DERIVED_CORRUPTION_LIMIT):
        reasons.append("known_hads_missing_sentinel" if value == KNOWN_HADS_SENTINEL
                       else "hads_sentinel_contaminated_hourly_stage")
    elif (record.get("station") == "MCHL1"
          and str(record.get("variable", "")).startswith("stage_change_")
          and isinstance(value, (int, float)) and abs(value) >= DERIVED_CORRUPTION_LIMIT):
        reasons.append("sentinel_contaminated_derived_change")
    if reasons:
        cleaned["value"] = None
        cleaned["missing"] = True
        cleaned["phase7_cleaning_reasons"] = reasons
    return cleaned, reasons


def _read_gzip_json(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def _write_gzip_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    path.write_bytes(gzip.compress(payload, mtime=0))


def _time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def audit_archive(input_dir):
    """Inspect an hourly archive; report structural and sentinel findings."""
    input_dir = pathlib.Path(input_dir)
    counts = collections.Counter()
    missing = collections.Counter()
    qc = collections.Counter()
    seen = collections.Counter()
    timestamps = collections.defaultdict(list)
    usable_timestamps = collections.defaultdict(list)
    input_ranges = collections.defaultdict(lambda: [None, None])
    usable_ranges = collections.defaultdict(lambda: [None, None])
    metadata_profiles = collections.defaultdict(collections.Counter)
    hashes = {}
    record_count = 0
    for path in sorted(input_dir.glob("*.json.gz")):
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        doc = _read_gzip_json(path)
        for row in doc.get("records", []):
            record_count += 1
            key = (row.get("station"), row.get("variable"))
            counts[key] += 1
            if key[0] in STATIONS and key[1] in MEASURED_VARIABLES:
                seen[(key, row.get("time"))] += 1
                profile = (row.get("unit"), row.get("datum"), row.get("source"))
                metadata_profiles[key][profile] += 1
            if row.get("missing") or row.get("value") is None:
                missing[key] += 1
            cleaned, reasons = clean_record(row)
            qc.update(reasons)
            if row.get("station") in STATIONS and row.get("variable") in {"stage", "water", "discharge"}:
                timestamps[key].append(_time(row["time"]))
                value = row.get("value")
                if isinstance(value, (int, float)) and math.isfinite(value):
                    lo, hi = input_ranges[key]
                    input_ranges[key] = [value if lo is None else min(lo, value),
                                         value if hi is None else max(hi, value)]
                    if not reasons and not row.get("missing"):
                        usable_timestamps[key].append(_time(row["time"]))
                        lo, hi = usable_ranges[key]
                        usable_ranges[key] = [value if lo is None else min(lo, value),
                                              value if hi is None else max(hi, value)]
    duplicate_counts = collections.Counter()
    for (key, _), n in seen.items():
        if n > 1:
            duplicate_counts[key] += n - 1
    duplicates = {f"{k[0]}:{k[1]}": duplicate_counts[k] for k in counts}
    cadence = {}
    for key, values in timestamps.items():
        times = sorted(values)
        valid_times = sorted(usable_timestamps[key])
        unique_times = sorted(set(times))
        unique_valid_times = sorted(set(valid_times))
        expected_slots = (round((unique_times[-1] - unique_times[0]).total_seconds() / 3600) + 1
                          if unique_times else 0)
        cadence[f"{key[0]}:{key[1]}"] = {
            "first_utc": times[0].strftime("%Y-%m-%dT%H:%M:%SZ") if times else None,
            "last_utc": times[-1].strftime("%Y-%m-%dT%H:%M:%SZ") if times else None,
            "duplicate_timestamp_rows": duplicates.get(f"{key[0]}:{key[1]}", 0),
            "expected_hour_slots_in_recorded_span": expected_slots,
            "recorded_hour_slots": len(unique_times),
            "unrecorded_hour_slots": max(0, expected_slots - len(unique_times)),
            "usable_observation_slots": len(unique_valid_times),
            "usable_observation_fraction_of_recorded_span": len(unique_valid_times) / expected_slots if expected_slots else None,
            "largest_record_timestamp_gap_hours": max(((b - a).total_seconds() / 3600 for a, b in zip(unique_times, unique_times[1:])), default=None),
            "largest_usable_observation_gap_hours": max(((b - a).total_seconds() / 3600 for a, b in zip(unique_valid_times, unique_valid_times[1:])), default=None),
            "finite_input_value_min_max": input_ranges[key],
            "usable_finite_value_min_max": usable_ranges[key],
        }
    return {
        "schema": "phase7.archive-audit.v1",
        "input_files_sha256": hashes,
        "record_count": record_count,
        "station_variable_counts": {f"{k[0]}:{k[1]}": {"rows": n, "missing": missing[k]} for k, n in sorted(counts.items())},
        "automatic_cleaning_counts": dict(sorted(qc.items())),
        "cadence_and_ranges": cadence,
        "source_unit_datum_profiles": {
            f"{key[0]}:{key[1]}": [
                {"unit": profile[0], "datum": profile[1], "source": profile[2], "rows": n}
                for profile, n in sorted(profiles.items(), key=lambda item: str(item[0]))
            ] for key, profiles in sorted(metadata_profiles.items())
        },
        "duplicate_timestamps": {k: v for k, v in duplicates.items() if v},
        "interpretation": "Finite stage/discharge extremes and statistical jumps are retained. They require source-level QC before exclusion.",
    }


def build_clean_experiment(input_dir, output_dir):
    """Write clean copies without changing any source file."""
    input_dir, output_dir = pathlib.Path(input_dir), pathlib.Path(output_dir)
    audit = audit_archive(input_dir)
    cleaned_counts = collections.Counter()
    for path in sorted(input_dir.glob("*.json.gz")):
        doc = _read_gzip_json(path)
        cleaned_rows = []
        file_cleaned_counts = collections.Counter()
        for row in doc.get("records", []):
            cleaned, reasons = clean_record(row)
            cleaned_rows.append(cleaned)
            cleaned_counts.update(reasons)
            file_cleaned_counts.update(reasons)
        doc["records"] = cleaned_rows
        doc["phase7_experimental_cleaning"] = {
            "method": "phase7-clean-v1",
            "source_sha256": audit["input_files_sha256"][path.name],
            "source_records_preserved": len(cleaned_rows),
            "invalid_values_marked_missing": sum(file_cleaned_counts.values()),
        }
        _write_gzip_json(output_dir / path.name, doc)
    audit["cleaned_files"] = len(list(input_dir.glob("*.json.gz")))
    audit["cleaning_method"] = "phase7-clean-v1"
    audit["cleaned_values_marked_missing"] = dict(sorted(cleaned_counts.items()))
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, default=pathlib.Path("site/data/history/hourly"))
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--summary", type=pathlib.Path)
    args = parser.parse_args(argv)
    result = build_clean_experiment(args.input, args.output)
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
