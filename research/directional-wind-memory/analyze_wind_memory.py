"""Fixed, issue-time NWCL1 wind-memory descriptors; research only."""
from __future__ import annotations

import csv
import gzip
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
WINDOWS = (3, 6, 12, 24, 48, 72)
THRESHOLDS_KT = {"10mph": 8.68976, "15mph": 13.03464, "20mph": 17.37952}


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_winds():
    result = {}
    for path in sorted((ROOT / "site/data/history/hourly").glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf8") as stream:
            month = json.load(stream)
        by_time = defaultdict(dict)
        for row in month["records"]:
            if row["station"] == "NWCL1" and row["variable"] in ("wind_u", "wind_v"):
                stamp = parse_time(row["time"])
                by_time[stamp][row["variable"]] = None if row["missing"] else row["value"]
        for stamp, vals in by_time.items():
            u, v = vals.get("wind_u"), vals.get("wind_v")
            result[stamp] = (u, v) if u is not None and v is not None else None
    return result


def descriptors(winds, issue):
    """Use only fully completed bins strictly before issue time; no gap filling."""
    issue = parse_time(issue) if isinstance(issue, str) else issue
    out = {}
    for hours in WINDOWS:
        vals = [winds.get(issue - timedelta(hours=i)) for i in range(1, hours + 1)]
        valid = [x for x in vals if x is not None]
        if len(valid) < math.ceil(0.8 * hours):
            continue
        us = np.array([x[0] for x in valid], dtype=float)
        vs = np.array([x[1] for x in valid], dtype=float)
        speed = np.hypot(us, vs)
        out[f"u_mean_{hours}h_kt"] = float(us.mean())
        out[f"v_mean_{hours}h_kt"] = float(vs.mean())
        out[f"westward_stress_proxy_mean_{hours}h_kt2"] = float((-us * speed).mean())
        out[f"westward_impulse_{hours}h_kt_h"] = float((-us).sum())
        for label, threshold in THRESHOLDS_KT.items():
            out[f"hours_ge_{label}_{hours}h"] = int(np.sum(speed >= threshold))
        out[f"coverage_{hours}h"] = len(valid) / hours
        # Signed negative-U runs are merely a directional diagnostic, not a
        # station-validated favorable-fetch threshold.
        run = best = 0
        for item in vals:
            if item is not None and item[0] < 0:
                run += 1
                best = max(best, run)
            else:
                run = 0
        out[f"longest_negative_u_run_{hours}h"] = best
        # Directional resultant (mean vector magnitude / mean speed).
        out[f"directional_persistence_{hours}h"] = float(np.hypot(us.mean(), vs.mean()) / speed.mean()) if speed.mean() else 0.0
    return out


def read_csv(path):
    with path.open(newline="", encoding="utf8") as stream:
        return list(csv.DictReader(stream))


def build_rows(winds):
    base = ROOT / "research/rise-failure-audit"
    items = []
    for row in read_csv(base / "event-diagnostics.csv"):
        issue = row["first_issue_time_utc"]
        items.append({"case_id": row["event_id"], "group": "rise_detected" if row["detected"] == "True" else "rise_missed", "issue_time_utc": issue, **descriptors(winds, issue)})
    for row in read_csv(base / "false-alert-clusters.csv"):
        if row["false_alarm"] == "True":
            issue = row["start_issue_utc"]
            items.append({"case_id": row["cluster_id"], "group": "false_alert", "issue_time_utc": issue, **descriptors(winds, issue)})
    for row in read_csv(ROOT / "site/data/history/phase3b/control-windows.csv"):
        if row["status"] == "eligible_control_candidate":
            issue = row["start_utc"]
            items.append({"case_id": row["control_candidate_id"], "group": "eligible_nonresponse_control", "issue_time_utc": issue, **descriptors(winds, issue)})
    return items


def summarize(rows):
    fields = sorted(set().union(*(r.keys() for r in rows)) - {"case_id", "group", "issue_time_utc"})
    summary = {}
    for group in sorted({r["group"] for r in rows}):
        subset = [r for r in rows if r["group"] == group]
        stats = {"n_groups": len(subset)}
        for field in fields:
            vals = [r[field] for r in subset if isinstance(r.get(field), (float, int))]
            if vals:
                stats[field] = {"n": len(vals), "median": float(np.median(vals)), "q25": float(np.quantile(vals, .25)), "q75": float(np.quantile(vals, .75))}
        summary[group] = stats
    return summary


def write_svg(summary):
    groups = ["eligible_nonresponse_control", "rise_detected", "rise_missed", "false_alert"]
    labels = ["Controls", "Detected rises", "Missed rises", "False alerts"]
    metrics = [("hours_ge_15mph_72h", "Hours ≥15 mph in prior 72h", "hours"),
               ("westward_stress_proxy_mean_24h_kt2", "Prior 24h signed U|V| proxy", "kt²")]
    width, height = 940, 390
    colors = ["#3478a8", "#2c8b57", "#ce8c24", "#ac4b4b"]
    chunks = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
              '<rect width="100%" height="100%" fill="white"/>',
              '<style>text{font-family:Arial,sans-serif;fill:#252525}.title{font-size:18px;font-weight:bold}.label{font-size:13px}.small{font-size:11px}</style>',
              '<text x="470" y="25" text-anchor="middle" class="title">NWCL1 wind history at archived issue times</text>',
              '<text x="470" y="44" text-anchor="middle" class="small">Median and interquartile range; descriptive, serially dependent cohorts</text>']
    for panel, (key, title, unit) in enumerate(metrics):
        x0, x1 = 70 + panel * 465, 470 + panel * 465
        y0, y1 = 90, 310
        allq = [summary[g][key][q] for g in groups if key in summary[g] for q in ("q25", "q75")]
        lo, hi = min(allq), max(allq)
        pad = (hi - lo) * .08 or 1
        lo -= pad; hi += pad
        sy = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
        chunks.extend([f'<text x="{(x0+x1)/2}" y="68" text-anchor="middle" class="label">{title} ({unit})</text>',
                       f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#777"/>',
                       f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="#777"/>'])
        for tick in range(5):
            value = lo + (hi - lo) * tick / 4
            yy = sy(value)
            chunks.extend([f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" stroke="#ddd"/>',
                           f'<text x="{x0-8}" y="{yy+4:.1f}" text-anchor="end" class="small">{value:.1f}</text>'])
        for i, (group, label) in enumerate(zip(groups, labels)):
            stats = summary[group].get(key)
            if not stats: continue
            xx = x0 + 48 + i * 91
            q1, med, q3 = (sy(stats[q]) for q in ("q25", "median", "q75"))
            chunks.extend([f'<line x1="{xx}" y1="{q1:.1f}" x2="{xx}" y2="{q3:.1f}" stroke="{colors[i]}" stroke-width="3"/>',
                           f'<line x1="{xx-8}" y1="{q1:.1f}" x2="{xx+8}" y2="{q1:.1f}" stroke="{colors[i]}"/>',
                           f'<line x1="{xx-8}" y1="{q3:.1f}" x2="{xx+8}" y2="{q3:.1f}" stroke="{colors[i]}"/>',
                           f'<circle cx="{xx}" cy="{med:.1f}" r="5" fill="{colors[i]}"/>',
                           f'<text x="{xx}" y="{y1+22}" text-anchor="middle" class="small">{label}</text>'])
    chunks.append('</svg>')
    (OUT / "wind_memory_groups.svg").write_text("\n".join(chunks) + "\n", encoding="utf8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = build_rows(load_winds())
    summary = summarize(rows)
    report = {
        "scope": "descriptive shadow diagnostics; no model fitting or performance claims",
        "candidate_windows_hours": list(WINDOWS),
        "thresholds": "10/15/20 mph converted to knots and counted in hourly mean vector speed; sensitivity descriptors only",
        "timestamp_rule": "issue timestamp minus 1 hour through minus window hours; bins must be observed; 80% completeness minimum for continuous summaries; missing bins break runs",
        "direction_rule": "NWCL1 U/V are toward-vector components; -U is reported as westward component proxy, without asserting favorable fetch or calibrated wind stress",
        "limitations": ["hourly retrospective archive has no receipt timestamps or QC qualifiers", "wind exposure/height history not represented in archive", "event groups, false alert clusters and controls are serially dependent and overlap", "controls are eligible Phase 3B candidates, not matched independent physical events", "stress proxy is not physical stress because height, drag coefficient and exposure are unknown"],
        "counts": {g: sum(r["group"] == g for r in rows) for g in sorted({r["group"] for r in rows})},
        "summary": summary,
    }
    (OUT / "wind_memory_summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf8")
    write_svg(summary)
    print(json.dumps(report["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
