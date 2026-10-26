"""Read-only exact-time versus ±30-minute verification sensitivity audit."""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path

UTC = dt.timezone.utc


def parse(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


def match_observation(target_time, observations, tolerance_minutes, as_of=None):
    """Select the nearest eligible observed value; preserve input order for ties."""
    target = parse(target_time)
    cutoff = parse(as_of) if as_of is not None else None
    limit = float(tolerance_minutes) * 60
    candidates = []
    for observation in observations:
        value = observation.get("value_ft")
        valid = observation.get("valid_time_utc")
        if value is None or not valid:
            continue
        try:
            numeric = float(value)
            stamp = parse(valid)
            received = parse(observation["ingested_utc"]) if observation.get("ingested_utc") else None
        except (TypeError, ValueError, KeyError):
            continue
        if not math.isfinite(numeric) or (cutoff and received and received > cutoff):
            continue
        distance = abs((stamp - target).total_seconds())
        if distance <= limit:
            candidates.append((distance, observation))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def _load_json(path):
    raw = Path(path).read_bytes()
    if str(path).endswith(".gz"):
        raw = gzip.decompress(raw)
    return json.loads(raw)


def _observations(root):
    result = []
    paths = sorted((Path(root) / "site/data/prospective/archive/observations").glob("*.json*"))
    for path in paths:
        capture = _load_json(path)
        capture_time = capture.get("retrieved_utc")
        if not capture_time:
            continue
        for row in capture.get("observations", []):
            if (row.get("station") == "MAUL1" and row.get("parameter") == "stage"
                    and row.get("datum") == "gage height"):
                result.append({"valid_time_utc": row.get("valid_time_utc"),
                               "ingested_utc": row.get("retrieved_utc") or capture_time,
                               "value_ft": row.get("value")})
    return paths, result


def _first_match(target, observations, tolerance_minutes):
    """Use the first archived capture after target with a qualifying row."""
    target_time = parse(target)
    by_capture = {}
    for observation in observations:
        received = observation.get("ingested_utc")
        if not received or parse(received) < target_time:
            continue
        by_capture.setdefault(received, []).append(observation)
    for captured_at in sorted(by_capture, key=parse):
        matched = match_observation(target, by_capture[captured_at], tolerance_minutes,
                                    as_of=captured_at)
        if matched is not None:
            return matched
    return None


def _metrics(rows):
    errors = [float(row["forecast_change_ft"]) - float(row["observed_change_ft"]) for row in rows]
    return {"n": len(rows),
            "mae_ft": sum(abs(x) for x in errors) / len(errors) if errors else None,
            "rmse_ft": math.sqrt(sum(x*x for x in errors) / len(errors)) if errors else None,
            "bias_ft": sum(errors) / len(errors) if errors else None}


def build_report(root):
    root = Path(root)
    issue_paths = sorted((root / "site/data/prospective/archive/issues").glob("*.json"))
    records = [_load_json(path) for path in issue_paths]
    records = [record for record in records if record.get("mode", "authentic") == "authentic"]
    observation_paths, observations = _observations(root)
    results = {"exact": {}, "within_30_minutes": {}}
    row_matches = {"exact": {}, "within_30_minutes": {}}
    for record in records:
        issue_id = record["issuance_id"]
        initial_stage = record.get("latest_maul1_native_stage_ft")
        if initial_stage is None:
            initial_stage = record.get("snapshot", {}).get("maul1_stage_native_ft")
        if initial_stage is None:
            continue
        for horizon, forecast in record.get("forecasts", {}).items():
            target = forecast["valid_time_utc"]
            for model, item in forecast.get("models", {}).items():
                if item.get("status") != "issued" or item.get("predicted_stage_native_ft") is None:
                    continue
                key = f"{model}:{int(horizon)}h"
                match_key = f"{issue_id}:{int(horizon)}:{model}"
                prediction = float(item["predicted_stage_native_ft"])
                for label, tolerance in (("exact", 0), ("within_30_minutes", 30)):
                    observation = _first_match(target, observations, tolerance)
                    if observation is None:
                        continue
                    row = {"issuance_id": issue_id, "horizon_hours": int(horizon), "model": model,
                           "forecast_valid_time_utc": target,
                           "observation_valid_time_utc": observation["valid_time_utc"],
                           "observation_ingested_utc": observation["ingested_utc"],
                           "offset_minutes": (parse(observation["valid_time_utc"])-parse(target)).total_seconds()/60,
                           "forecast_change_ft": prediction-float(initial_stage),
                           "observed_change_ft": float(observation["value_ft"])-float(initial_stage)}
                    results[label].setdefault(key, []).append(row)
                    row_matches[label][match_key] = row
    metrics = {label: {key: _metrics(rows) for key, rows in sorted(groups.items())}
               for label, groups in results.items()}
    keys = sorted(set(metrics["exact"]) | set(metrics["within_30_minutes"]))
    comparison = {}
    for key in keys:
        exact = metrics["exact"].get(key, {"n": 0, "mae_ft": None, "rmse_ft": None, "bias_ft": None})
        window = metrics["within_30_minutes"].get(key, {"n": 0, "mae_ft": None, "rmse_ft": None, "bias_ft": None})
        comparison[key] = {"exact": exact, "within_30_minutes": window,
                           "delta_n": window["n"]-exact["n"],
                           "delta_mae_ft": (window["mae_ft"]-exact["mae_ft"]
                                            if window["mae_ft"] is not None and exact["mae_ft"] is not None else None),
                           "delta_rmse_ft": (window["rmse_ft"]-exact["rmse_ft"]
                                             if window["rmse_ft"] is not None and exact["rmse_ft"] is not None else None)}
    issue_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in issue_paths}
    obs_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in observation_paths}
    return {"schema": "phase6.verification-matching-sensitivity.v1",
            "research_only": True, "original_verification_modified": False,
            "method": "Read authentic immutable issue records and archived MAUL1 native-stage captures. For each target, use the first archived capture at or after target with a qualifying observation; choose nearest timestamp within the declared tolerance. No interpolation, synthetic observation, or source QC reinterpretation.",
            "issue_count": len(records), "observation_capture_count": len(observation_paths),
            "input_sha256": {"issues": issue_hashes, "observation_captures": obs_hashes},
            "match_policy": {"exact": "0 minutes", "within_30_minutes": "nearest observation with absolute valid-time offset <= 30 minutes"},
            "metrics": metrics, "comparison": comparison}


def write_report(report, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "verification-matching-sensitivity.json").write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lines = ["# Phase 6 retrospective verification matching sensitivity", "",
             "Research-only comparison. Original verification revisions and `performance.json` are unchanged.", "",
             f"- Authentic issues: {report['issue_count']}",
             f"- Archived observation captures: {report['observation_capture_count']}",
             "- Exact matching: same valid timestamp.",
             "- Window matching: nearest archived observation within ±30 minutes.",
             "- Both use the first archived capture at or after the target; no interpolation or imputed observation.",
             "", "| Model / horizon | Exact N | Exact MAE (ft) | ±30 min N | ±30 min MAE (ft) | ΔN | ΔMAE (ft) |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for key, row in sorted(report["comparison"].items()):
        exact, window = row["exact"], row["within_30_minutes"]
        vals = [exact["mae_ft"], window["mae_ft"], row["delta_mae_ft"]]
        display = ["—" if x is None else f"{x:.4f}" for x in vals]
        lines.append(f"| {key} | {exact['n']} | {display[0]} | {window['n']} | {display[1]} | {row['delta_n']} | {display[2]} |")
    lines.extend(["", "The comparison is sensitive to sample composition as well as timestamp tolerance. These are alternative retrospective matches, not a correction to published verification and not independent-sample skill claims.", ""])
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True,
                        help="separate experimental output directory; must not be inside the archived evidence tree")
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    evidence = (root / "site/data/prospective/archive").resolve()
    if evidence == output or evidence in output.parents or output in evidence.parents:
        raise ValueError("experimental output must be separate from immutable prospective evidence")
    report = build_report(root)
    write_report(report, output)
    print(json.dumps({"issue_count": report["issue_count"],
                      "observation_capture_count": report["observation_capture_count"],
                      "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
