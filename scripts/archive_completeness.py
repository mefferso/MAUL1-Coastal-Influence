"""Report observation archive cadence, gaps, latency, revisions and issue availability.

Research / Shadow Evaluation / Not Operational. This report audits stored receipts;
it does not infer when a provider first made a value available.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import statistics
from collections import defaultdict

UTC = dt.timezone.utc


def stamp(value):
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("archive timestamps must include a timezone")
    return parsed.astimezone(UTC)


def _read_receipts(root):
    base = pathlib.Path(root) / "research/prospective-forcing-archive/receipts"
    rows = []
    for path in sorted(base.glob("*.jsonl")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                try:
                    row = json.loads(line)
                    if row.get("record_type", "observation") == "observation":
                        rows.append(row)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSON receipt") from exc
    return rows


def _read_issues(root):
    issues = []
    for path in sorted((pathlib.Path(root) / "site/data/prospective/attempts").glob("*.json")):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            value = report.get("actual_issue_time_utc")
            if value:
                issues.append(stamp(value))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return issues


def _identity(row):
    return (row.get("value"), row.get("status"), row.get("unit"), row.get("datum"),
            row.get("provider_updated_at"), tuple(row.get("qc_flags", [])),
            row.get("accumulation_period_seconds"), row.get("measurement_semantics"))


def build_report(root, issue_times=None):
    rows = _read_receipts(root)
    grouped = defaultdict(list)
    for row in rows:
        key = (row.get("source"), row.get("station_id"), row.get("parameter_code"), row.get("variable"))
        grouped[key].append(row)
    series = []
    for key in sorted(grouped, key=lambda x: tuple(str(v or "") for v in x)):
        items = grouped[key]
        by_valid = defaultdict(list)
        for row in items:
            by_valid[row["valid_time"]].append(row)
        valid_stamps = sorted(stamp(t) for t in by_valid)
        gaps = [(b-a).total_seconds() for a, b in zip(valid_stamps, valid_stamps[1:])]
        latencies = [(stamp(r["retrieved_at"])-stamp(r["valid_time"])).total_seconds() for r in items]
        if any(value < 0 for value in latencies):
            raise ValueError("observation receipt retrieval predates its valid time")
        repeated = 0
        for first, second in zip(valid_stamps, valid_stamps[1:]):
            a, b = first.isoformat().replace("+00:00", "Z"), second.isoformat().replace("+00:00", "Z")
            if any(_identity(x)[0] == _identity(y)[0] for x in by_valid[a] for y in by_valid[b]):
                repeated += 1
        revisions = sum(len({_identity(row) for row in values}) > 1 for values in by_valid.values())
        median_gap = statistics.median(gaps) if gaps else None
        series.append({"source":key[0], "station_id":key[1], "parameter_code":key[2], "variable":key[3],
                       "receipt_count":len(items), "unique_valid_timestamps":len(valid_stamps),
                       "valid_time_min":valid_stamps[0].isoformat().replace("+00:00", "Z") if valid_stamps else None,
                       "valid_time_max":valid_stamps[-1].isoformat().replace("+00:00", "Z") if valid_stamps else None,
                       "cadence_seconds_median":median_gap, "gaps_over_1_5x_cadence":sum(g > median_gap*1.5 for g in gaps) if median_gap else 0,
                       "max_gap_seconds":max(gaps) if gaps else None,
                       "latency_seconds":{"median":statistics.median(latencies) if latencies else None,
                                           "max":max(latencies) if latencies else None},
                       "repeated_value_transitions":repeated, "revision_valid_times":revisions,
                       "delayed_recovery_records":sum(r.get("acquisition_mode")=="delayed_recovery" for r in items),
                       "prospective_records":sum(r.get("acquisition_mode", "prospective")=="prospective" for r in items)})
    times = [stamp(x) if isinstance(x, str) else x.astimezone(UTC) for x in (issue_times if issue_times is not None else _read_issues(root))]
    availability = []
    for issue in sorted(times):
        available = sum(stamp(r["valid_time"]) <= issue and stamp(r["retrieved_at"]) <= issue for r in rows)
        available_features = []
        for key, feature_rows in sorted(grouped.items(), key=lambda pair: tuple(str(v or "") for v in pair[0])):
            eligible = [r for r in feature_rows if stamp(r["valid_time"]) <= issue and stamp(r["retrieved_at"]) <= issue]
            if eligible:
                available_features.append({"source":key[0], "station_id":key[1], "parameter_code":key[2],
                                           "variable":key[3], "latest_valid_time":max(r["valid_time"] for r in eligible)})
        availability.append({"issue_time":issue.isoformat().replace("+00:00", "Z"), "available_receipts":available,
                             "total_receipts":len(rows), "available_series":len(available_features),
                             "available_features":available_features})
    return {"schema_version":"archive-completeness-1", "status":"Research / Shadow Evaluation / Not Operational",
            "receipt_count":len(rows), "series_count":len(series), "series":series, "issue_availability":availability}


def render_summary(report):
    """Render bounded Actions markdown rather than embedding issue-by-issue JSON."""
    lines=["## Archive completeness (Research / Shadow Evaluation / Not Operational)",
           f"\nReceipts: {report['receipt_count']} · series: {report['series_count']} · audited issues: {len(report['issue_availability'])}",
           "\n| Station | Variable | Unique times | Median cadence | Max gap | Median latency | Max latency | Repeated | Revisions | Recovered | Prospective |",
           "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    def fmt(seconds):
        return "—" if seconds is None else f"{seconds/60:.1f} min" if seconds < 3600 else f"{seconds/3600:.2f} h"
    for item in report["series"]:
        latency=item["latency_seconds"]
        lines.append(f"| {item['station_id']} | {item['variable']} | {item['unique_valid_timestamps']} | "
                     f"{fmt(item['cadence_seconds_median'])} | {fmt(item['max_gap_seconds'])} | "
                     f"{fmt(latency['median'])} | {fmt(latency['max'])} | {item['repeated_value_transitions']} | "
                     f"{item['revision_valid_times']} | {item['delayed_recovery_records']} | {item['prospective_records']} |")
    issues=report["issue_availability"]
    feature_counts=defaultdict(int)
    available_series=[]
    for issue in issues:
        for feature in issue["available_features"]:
            key=(feature["station_id"], feature["parameter_code"], feature["variable"])
            feature_counts[key]+=1
        available_series.append(issue["available_series"])
    lines.extend(["\n### Feature availability at issues", "",
                  f"{len(issues)} issue times checked using both valid_time and actual retrieved_at no later than issue time."])
    if issues:
        lines.append(f"Available series per issue: min {min(available_series)}/{report['series_count']}, "
                     f"median {statistics.median(available_series):g}/{report['series_count']}, "
                     f"max {max(available_series)}/{report['series_count']}.")
        lines.extend(["", "| Station | Parameter | Variable | Issues available |", "|---|---|---|---:|"])
        for (station, parameter, variable), count in sorted(feature_counts.items(), key=lambda item:tuple(str(x or "") for x in item[0])):
            lines.append(f"| {station} | {parameter or '—'} | {variable} | {count}/{len(issues)} |")
    else:
        lines.append("No authentic issue timestamps were found.")
    return "\n".join(lines)+"\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--summary", action="store_true", help="append the report to GITHUB_STEP_SUMMARY")
    args = parser.parse_args()
    report = build_report(args.root)
    if args.summary:
        rendered=render_summary(report)
        print(rendered)
        import os
        path = os.environ.get("GITHUB_STEP_SUMMARY")
        if path:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write("\n"+rendered)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
