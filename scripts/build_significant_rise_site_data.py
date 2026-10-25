"""Build the compact, static payload used by the Model Lab rise investigation."""
from __future__ import annotations

import json
import argparse
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def build(root: pathlib.Path = ROOT) -> dict:
    root = pathlib.Path(root)
    audit = json.loads((root / "research/rise-failure-audit/analysis.json").read_text())
    timelines = json.loads((root / "research/rise-failure-audit/representative-timelines.json").read_text())
    fields = (
        "event_id", "selection", "failure_mechanism", "detected",
        "first_issue_time_utc", "last_issue_time_utc", "first_qualifying_target_utc",
        "last_qualifying_target_utc", "lead_to_first_qualifying_target_hours",
        "qualified_window_count", "max_observed_target_change_ft",
        "max_phase5b_coastal_tidal_target_change_ft", "overlapping_phase3b_response_event_ids",
        "interpretation", "timeline_rows",
    )
    events = [{field: event.get(field) for field in fields} for event in timelines]
    return {
        "schema": "maul1.significant-rise-model-lab.v1",
        "evidence_label": "Retrospective / Development Evidence",
        "source_schema": audit["schema"],
        "summary": audit,
        "representative_events": events,
    }


def main() -> None:
    payload = build()
    target = ROOT / "site/data/research/significant-rise.json"
    findings_target = ROOT / "site/data/research/significant-rise-findings.md"
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    findings = (ROOT / "research/rise-failure-audit/report.md").read_text()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when committed site outputs differ")
    args = parser.parse_args()
    if args.check:
        if target.read_text() != encoded or findings_target.read_text() != findings:
            raise SystemExit("significant-rise site artifacts are stale; rebuild without --check")
        print("Significant-rise site artifacts match the deterministic build.")
        return
    target.write_text(encoded)
    findings_target.write_text(findings)


if __name__ == "__main__":
    main()
