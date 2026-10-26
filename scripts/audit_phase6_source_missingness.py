"""Audit archived source rows for missing values, QC flags, and sentinel markers."""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path

NDBC_SPEED_SENTINEL_KNOTS = round(99.0 * 1.943844492, 6)
STATIONS = ("MAUL1", "DENL1", "MDLL1", "NWCL1", "MCHL1", "NWCL1-NDBC")


def _read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def _quality_key(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _coops_flags_usable(value):
    if value in (None, ""):
        return True
    flags = value.split(",") if isinstance(value, str) else value
    return all(str(flag).strip() in ("", "0", "P", "provisional") for flag in flags)


def audit_source_missingness(root):
    root = Path(root)
    row_counts = collections.defaultdict(collections.Counter)
    qc_counts = collections.defaultdict(collections.Counter)
    value_ranges = collections.defaultdict(lambda: [None, None])
    sentinel_counts = collections.Counter()
    exact_water, exact_prediction = {}, {}
    input_hashes = {}
    file_counts = {}
    for station in STATIONS:
        paths = sorted((root / "site/data/history/raw" / station).glob("*.json.gz"))
        file_counts[station] = len(paths)
        for path in paths:
            raw = path.read_bytes()
            input_hashes[str(path.relative_to(root))] = hashlib.sha256(raw).hexdigest()
            document = json.loads(gzip.decompress(raw))
            for row in document.get("rows", []):
                variable = row.get("variable", "unknown")
                key = (station, variable)
                row_counts[station][variable] += 1
                qc_counts[key][_quality_key(row.get("quality"))] += 1
                value = row.get("value")
                if value is None:
                    row_counts[station][f"{variable}:missing"] += 1
                    continue
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    sentinel_counts["non_numeric_values"] += 1
                    continue
                if not math.isfinite(number):
                    sentinel_counts["non_finite_values"] += 1
                    continue
                limits = value_ranges[key]
                limits[0] = number if limits[0] is None else min(limits[0], number)
                limits[1] = number if limits[1] is None else max(limits[1], number)
                source = str(row.get("source", ""))
                if source.startswith("USGS") and station in {"MAUL1", "DENL1", "MDLL1"} and number <= -9999:
                    sentinel_counts["usgs_negative_numeric"] += 1
                if station == "NWCL1" and source.startswith("NOAA CO-OPS") and not math.isfinite(number):
                    sentinel_counts["coops_non_finite"] += 1
                if station == "MCHL1" and variable == "stage":
                    if number == 9_999_999.0:
                        sentinel_counts["hads_exact_missing"] += 1
                    elif abs(number) >= 1_000_000:
                        sentinel_counts["hads_sentinel_contaminated_numeric"] += 1
                if station == "NWCL1-NDBC" and variable in {"wind", "gust"} and number == NDBC_SPEED_SENTINEL_KNOTS:
                    sentinel_counts["ndbc_speed_or_gust_99_mps"] += 1
                if station == "NWCL1" and variable in {"water", "prediction"}:
                    if row.get("unit") == "ft" and row.get("datum") == "MLLW":
                        if variable == "water":
                            exact_water.setdefault(row["time"], []).append(row)
                        else:
                            exact_prediction.setdefault(row["time"], []).append(row)
    water_times, prediction_times = set(exact_water), set(exact_prediction)
    pair_times = water_times & prediction_times
    eligible_pairs = sum(
        any(_coops_flags_usable(row.get("quality")) for row in exact_water[stamp])
        and any(_coops_flags_usable(row.get("quality")) for row in exact_prediction[stamp])
        for stamp in pair_times)
    flagged_water = sum(not _coops_flags_usable(row.get("quality"))
                        for rows in exact_water.values() for row in rows)
    station_summary = {}
    for station in STATIONS:
        station_summary[station] = {
            "source_file_count": file_counts[station],
            "variable_rows": dict(sorted(row_counts[station].items())),
            "qc_value_counts": {variable: dict(sorted(counter.items()))
                                for (item_station, variable), counter in sorted(qc_counts.items())
                                if item_station == station},
            "finite_value_min_max": {variable: values for (item_station, variable), values in sorted(value_ranges.items())
                                     if item_station == station},
        }
    return {
        "schema": "phase6.source-missingness-qc-audit.v1",
        "research_only": True,
        "source_scope": "Committed normalized monthly source rows; no provider requests and no archive rewrites.",
        "input_sha256": dict(sorted(input_hashes.items())),
        "stations": station_summary,
        "sentinel_counts": dict(sorted(sentinel_counts.items())),
        "nwcl1_residual_pairing": {
            "source_pair_rule": "same exact UTC timestamp, ft, MLLW; eligible QC flags must be empty or zero/provisional only",
            "eligible_water_timestamps": len(water_times),
            "eligible_prediction_timestamps": len(prediction_times),
            "exact_mllw_pairs": len(pair_times),
            "qc_eligible_exact_pairs": eligible_pairs,
            "flagged_water_rows": flagged_water,
            "water_without_exact_prediction": len(water_times-prediction_times),
            "prediction_without_exact_water": len(prediction_times-water_times),
        },
        "limitations": [
            "Historical NDBC normalized rows cannot reveal WDIR=999 records that the old parser dropped wholesale; original provider response bodies were not archived in these monthly normalized partitions.",
            "Historical normalized source rows do not include provider receipt times; they cannot establish causal availability at Phase 5 issue times.",
            "The audit counts source missing values and QC; it does not alter Phase 5 features, frozen artifacts, forecasts, or verification.",
        ],
    }


def write_report(result, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "source-missingness-qc-audit.json").write_text(
        json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    pairs = result["nwcl1_residual_pairing"]
    lines = ["# Phase 6 archived source missingness and QC audit", "",
             "Research-only, read-only audit of committed normalized monthly source rows.", "",
             f"- NWCL1 observed water rows with exact MLLW prediction timestamp: {pairs['exact_mllw_pairs']:,}",
             f"- Those timestamp pairs with acceptable stored CO-OPS QC: {pairs['qc_eligible_exact_pairs']:,}",
             f"- CO-OPS water rows rejected by nonzero flags: {pairs['flagged_water_rows']:,}",
             f"- USGS negative numeric missing markers retained in normalized archives: {result['sentinel_counts'].get('usgs_negative_numeric', 0):,}",
             f"- HADS exact 9,999,999-ft markers retained in normalized archives: {result['sentinel_counts'].get('hads_exact_missing', 0):,}",
             f"- HADS sentinel-contaminated numeric rows (>=1,000,000 ft): {result['sentinel_counts'].get('hads_sentinel_contaminated_numeric', 0):,}",
             f"- NDBC 99.0-m/s speed/gust sentinel conversions retained as normalized rows: {result['sentinel_counts'].get('ndbc_speed_or_gust_99_mps', 0):,}",
             "", "Counts by station, product variable, QC value, and finite range are in `source-missingness-qc-audit.json`.",
             "Input file SHA-256 values are included for reproducibility.", "",
             "This audit does not recalculate or replace historical features, frozen model artifacts, authentic issues, verification revisions, or published skill.", "",
             "Limitations: the previous NDBC parser discarded rows with `WDIR=999` before writing normalized archives, so those lost speed/gust values cannot be reconstructed without archived provider bodies. Historical normalized records also lack source receipt times.", ""]
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    source_root = (root / "site/data/history/raw").resolve()
    if source_root == output or source_root in output.parents or output in source_root.parents:
        raise ValueError("audit output must be separate from historical source archives")
    result = audit_source_missingness(root)
    write_report(result, output)
    print(json.dumps({"stations": len(result["stations"]),
                      "nwcl1_exact_pairs": result["nwcl1_residual_pairing"]["exact_mllw_pairs"],
                      "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
