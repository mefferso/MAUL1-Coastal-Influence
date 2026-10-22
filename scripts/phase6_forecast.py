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

def compact_with_immutable_snapshot(record, archive_root):
    """Create immutable compressed evidence and a compact forecast record.

    Legacy v1 issues remain readable without migration. The compact record
    preserves the existing forecast schema, keeping verification/dashboard code
    compatible, and exposes the exact separately archived source snapshot.
    """
    import gzip
    import copy
    root = Path(archive_root)
    evidence = record.get("snapshot", {}).get("source_snapshot")
    if evidence is None:
        raise ValueError("source snapshot required for lossless archival")
    raw = (json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    store = root / "snapshots"
    store.mkdir(parents=True, exist_ok=True)
    source_path = store / f"{digest}.json.gz"
    if not source_path.exists():
        try:
            with source_path.open("xb") as handle:
                handle.write(gzip.compress(raw, compresslevel=9, mtime=0))
        except FileExistsError:
            pass
    if gzip.decompress(source_path.read_bytes()) != raw:
        raise ValueError("immutable source snapshot hash collision or corruption")
    compact = copy.deepcopy(record)
    compact["snapshot"].pop("source_snapshot")
    compact["snapshot"]["source_snapshot_ref"] = {
        "path": f"../snapshots/{digest}.json.gz",
        "sha256": digest,
        "encoding": "gzip+json",
    }
    compact["schema"] = "phase6.forecast.v2"
    return compact


def recover_source_snapshot(record, archive_root):
    """Return v1 inline or v2 compressed source evidence with hash verification."""
    import gzip
    inline = record.get("snapshot", {}).get("source_snapshot")
    if inline is not None:
        return inline
    ref = record["snapshot"]["source_snapshot_ref"]
    digest = ref["sha256"]
    if ref.get("encoding") != "gzip+json" or not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("invalid source snapshot reference")
    path = Path(archive_root) / "snapshots" / f"{digest}.json.gz"
    raw = gzip.decompress(path.read_bytes())
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("archived source snapshot does not match hash")
    return json.loads(raw)
