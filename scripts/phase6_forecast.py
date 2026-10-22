"""Immutable prospective issuance record helpers; forecasts remain research-only."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
from pathlib import Path

UTC = dt.timezone.utc
HORIZONS = (6, 12, 24)

def parse_time(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if parsed.tzinfo is None: raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(UTC)

def stamp(value): return parse_time(value).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def make_record(actual_issue_time, nominal_slot, snapshot, forecasts, *, simulated=False, run_id="", model_anchor_time=None):
    actual, nominal = parse_time(actual_issue_time), parse_time(nominal_slot)
    anchor = parse_time(model_anchor_time) if model_anchor_time is not None else actual
    if anchor > actual: raise ValueError("model anchor cannot be later than actual issuance")
    latest = snapshot.get("maul1_stage_native_ft")
    cycle = actual.strftime("%Y%m%dT%H%M%SZ")
    identity = hashlib.sha256(f"{cycle}|{run_id}|{int(simulated)}".encode()).hexdigest()[:16]
    by_horizon = {}
    for h in HORIZONS:
        valid = anchor + dt.timedelta(hours=h)
        if valid <= actual: raise ValueError("forecast target is not after actual issuance")
        entries = forecasts.get(str(h), {})
        if isinstance(entries, list): entries = {x["model"]: x for x in entries}
        by_horizon[str(h)] = {"valid_time_utc": stamp(valid), "effective_lead_hours": round((valid-actual).total_seconds()/3600, 6), "models": entries}
    return {"schema": "phase6.forecast.v1", "issuance_id": identity,
            "mode": "simulation" if simulated else "authentic", "nominal_issue_time_utc": stamp(nominal),
            "actual_issue_time_utc": stamp(actual), "model_anchor_time_utc": stamp(anchor), "latest_maul1_native_stage_ft": latest,
            "snapshot": snapshot, "forecasts": by_horizon, "run_id": run_id}

def write_immutable(record, archive_root):
    root = Path(archive_root) / ("simulations" if record["mode"] == "simulation" else "issues")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{record['issuance_id']}.json"
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, sort_keys=True, indent=2); handle.write("\n")
    return path
