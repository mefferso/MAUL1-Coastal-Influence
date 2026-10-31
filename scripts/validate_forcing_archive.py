"""Validate append-only, provenance-rich prospective observation batches.

Research / Shadow Evaluation / Not Operational. This module never produces forecasts.
Use: python scripts/validate_forcing_archive.py path/to/batch.jsonl
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
from collections import defaultdict

UTC = dt.timezone.utc
REQUIRED = {
    "schema_version", "station_id", "source", "variable", "unit", "datum",
    "valid_time", "retrieved_at", "value", "status", "raw_id", "qc_flags",
}
VARIABLE_UNITS = {
    "wind_speed": {"knots"},
    "wind_direction": {"degrees"},
    "wind_gust": {"knots"},
    "wind_u": {"knots"},
    "wind_v": {"knots"},
    "water_level": {"ft"},
    "tide_prediction": {"ft"},
    "discharge": {"cfs"},
    "gage_height": {"ft"},
    "precipitation": {"mm", "in"},
}
ALLOWED_STATUS = {"observed", "provisional", "predicted", "missing", "rejected"}


def parse_utc(value: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamps must be explicit UTC ISO-8601 ending Z")
    stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timezone required")
    return stamp.astimezone(UTC)


def validate(record: dict) -> None:
    if not isinstance(record, dict):
        raise ValueError("record must be object")
    missing = REQUIRED - set(record)
    if missing:
        raise ValueError("missing keys: " + ", ".join(sorted(missing)))
    if record["schema_version"] != "forcing-1":
        raise ValueError("unsupported schema_version")
    for key in ("station_id", "source", "variable", "unit", "datum", "raw_id"):
        if not isinstance(record[key], str) or not record[key].strip():
            raise ValueError(f"{key} must be nonempty text")
    if record["variable"] not in VARIABLE_UNITS:
        raise ValueError("unsupported variable")
    if record["unit"] not in VARIABLE_UNITS[record["variable"]]:
        raise ValueError("unit inconsistent with variable")
    if record["status"] not in ALLOWED_STATUS:
        raise ValueError("invalid observation status")
    if not isinstance(record["qc_flags"], list) or not all(isinstance(x, str) for x in record["qc_flags"]):
        raise ValueError("qc_flags must be a list of strings")
    valid = parse_utc(record["valid_time"])
    received = parse_utc(record["retrieved_at"])
    record_type = record.get("record_type", "observation")
    if record_type not in {"observation", "prediction"}:
        raise ValueError("record_type must be observation or prediction")
    if record_type == "prediction" and record["variable"] != "tide_prediction":
        raise ValueError("only tide_prediction may be a prediction record")
    if record_type == "observation" and record["status"] == "predicted":
        raise ValueError("predicted status requires prediction record_type")
    if "acquisition_mode" in record and record["acquisition_mode"] not in {"prospective", "delayed_recovery"}:
        raise ValueError("acquisition_mode must be prospective or delayed_recovery")
    if received < valid and record_type != "prediction":
        raise ValueError("receipt timestamp predates valid time; check time basis")
    val = record["value"]
    if record["status"] in {"observed", "provisional", "predicted"}:
        if not isinstance(val, (float, int)) or isinstance(val, bool) or not math.isfinite(val):
            raise ValueError("observed/provisional values must be finite numbers")
    elif val is not None:
        raise ValueError("missing/rejected values must be null; raw values belong in source files")
    if record["variable"] in {"water_level", "tide_prediction", "gage_height"} and record["datum"] == "unspecified":
        # Keep uncertain datums visible. Never silently treat them as NAVD88.
        pass


def validate_file(path: pathlib.Path) -> int:
    # Duplicate source receipts may be retained, but exact replay of one receipt is rejected.
    seen = set()
    count = 0
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                validate(item)
                key = (item["source"], item["station_id"], item["variable"],
                       item["valid_time"], item["retrieved_at"], item["raw_id"])
                if key in seen:
                    raise ValueError("duplicate source observation/receipt")
                seen.add(key)
                count += 1
            except (ValueError, TypeError, json.JSONDecodeError) as err:
                raise ValueError(f"{path}:{line_number}: {err}") from err
    if count == 0:
        raise ValueError("empty observation batch")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=pathlib.Path, nargs="+")
    args = parser.parse_args()
    total = sum(validate_file(path) for path in args.paths)
    print(f"Validated {total} observation receipts (research only)")


if __name__ == "__main__":
    main()

