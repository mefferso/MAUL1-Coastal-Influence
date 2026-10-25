"""Coverage and event-alignment diagnostics for raw USGS OGC GeoJSON features."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
import statistics


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def feature_time(feature: dict) -> datetime | None:
    raw = feature.get("properties", {}).get("time")
    if not raw:
        return None
    try:
        return parse_utc(raw)
    except (TypeError, ValueError):
        return None


def summarize_coverage(features: list[dict]) -> dict:
    """Summarize returned rows without inferring or filling missing observations."""
    times = sorted(t for feature in features if (t := feature_time(feature)) is not None)
    qc = {"approved": 0, "working_or_provisional": 0, "other_or_unstated": 0}
    invalid_value_count = 0
    for feature in features:
        props = feature.get("properties", {})
        status = props.get("approvals_status") or []
        if isinstance(status, str):
            status = [status]
        status = {str(item).lower() for item in status}
        if "approved" in status:
            qc["approved"] += 1
        elif "working" in status:
            qc["working_or_provisional"] += 1
        else:
            qc["other_or_unstated"] += 1
        try:
            if props.get("value") is None:
                raise ValueError
            if not math.isfinite(float(props["value"])):
                raise ValueError
        except (TypeError, ValueError):
            invalid_value_count += 1
    intervals = [(b - a).total_seconds() for a, b in zip(times, times[1:]) if b > a]
    median_interval_seconds = statistics.median(intervals) if intervals else None
    return {
        "feature_count": len(features),
        "timestamped_feature_count": len(times),
        "invalid_or_missing_timestamp_count": len(features) - len(times),
        "invalid_or_missing_value_count": invalid_value_count,
        "first_valid_time_utc": times[0].isoformat().replace("+00:00", "Z") if times else None,
        "last_valid_time_utc": times[-1].isoformat().replace("+00:00", "Z") if times else None,
        "median_observation_interval_seconds": median_interval_seconds,
        "largest_observation_gap_seconds": max(intervals) if intervals else None,
        "approval_status_counts": qc,
    }


def align_before_issue(features: list[dict], issue_time_utc: str, hours: int) -> list[dict]:
    """Return raw rows in [issue-hours, issue); never use post-issue observations."""
    issue_time = parse_utc(issue_time_utc)
    start = issue_time.timestamp() - hours * 3600
    selected = []
    for feature in features:
        observed_at = feature_time(feature)
        if observed_at and start <= observed_at.timestamp() < issue_time.timestamp():
            selected.append(feature)
    return sorted(selected, key=feature_time)


def event_coverage(events: list[dict], feature_series: list[dict], hours: int = 72) -> list[dict]:
    """Count issue-time-available rows per group; outcome target is context only."""
    output = []
    for event in events:
        issue_time = event["issue_time_utc"]
        target = event["first_qualifying_target_utc"]
        rows = align_before_issue(feature_series, issue_time, hours)
        output.append({
            "event_id": event["event_id"],
            "issue_time_utc": issue_time,
            "first_qualifying_target_utc": target,
            "window_start_utc": (parse_utc(issue_time) - timedelta(hours=hours)).isoformat().replace("+00:00", "Z"),
            "window_hours": hours,
            "available_row_count": len(rows),
            "latest_observation_time_utc": rows[-1].get("properties", {}).get("time") if rows else None,
            "observations": rows,
        })
    return output
