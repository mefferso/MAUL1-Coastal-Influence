"""Daily archive health and weekly scientific-readiness assessment.

All results are Research / Shadow Evaluation / Not Operational. Readiness is
evidence about data availability, not a claim that a model is valid.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import pathlib
import statistics
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

UTC = dt.timezone.utc
RECOVERY_MERGE_SHA = "10e29d09ac47c2e31ea66d8898bcc654bc6aa148"
RECOVERY_MERGED_AT = dt.datetime(2026, 10, 31, 23, 53, 43, tzinfo=UTC)
WINDOW_COVERAGE_THRESHOLD = 0.80
ISSUE_WINDOW_PASS_THRESHOLD = 0.80
MAX_GAP_MULTIPLIER = 3
PROVISIONAL_INDEPENDENT_RISES_FOR_REVIEW = 3

# NOAA CO-OPS NWCL1 wind and water-level products report six-minute observations.
# KNEW METAR is hourly with occasional special reports. USGS OGC continuous
# stations do not expose a single network-wide cadence; 15 minutes is a
# provisional check based on these configured continuous series and must remain
# labeled provisional until station metadata is archived.
CADENCE_POLICY = {
    "NWCL1": {"default_seconds": 360, "basis": "NOAA CO-OPS six-minute observations", "provisional": False},
    "KNEW": {"default_seconds": 3600, "basis": "METAR hourly routine reports; specials may occur", "provisional": False},
    "DENL1": {"default_seconds": 900, "basis": "USGS continuous series; provisional 15-minute criterion", "provisional": True},
    "MDLL1": {"default_seconds": 900, "basis": "USGS continuous series; provisional 15-minute criterion", "provisional": True},
    "MAUL1": {"default_seconds": 900, "basis": "USGS continuous series; provisional 15-minute criterion", "provisional": True},
    "MCHL1-USGS": {"default_seconds": 900, "basis": "USGS continuous series; provisional 15-minute criterion", "provisional": True},
    "USGS-301828090363100": {"default_seconds": 900, "basis": "USGS precipitation series; provisional 15-minute criterion", "provisional": True},
    "USGS-07379960": {"default_seconds": 900, "basis": "USGS continuous series; provisional 15-minute criterion", "provisional": True},
    "USGS-07378810": {"default_seconds": 900, "basis": "USGS continuous series; provisional 15-minute criterion", "provisional": True},
    "USGS-07378746": {"default_seconds": 900, "basis": "USGS continuous series; provisional 15-minute criterion", "provisional": True},
}
CONTEXT_PARAMETER_POLICY = {
    ("NWCL1","water_level"): (None,"MLLW"),
    ("DENL1","discharge"): ("00060",None), ("DENL1","gage_height"): ("00065",None),
    ("MDLL1","gage_height"): ("00065",None), ("MAUL1","gage_height"): ("00065",None),
    ("MAUL1","water_level"): ("63160","NAVD88"),
    ("MCHL1-USGS","gage_height"): ("00065",None),
    ("USGS-301828090363100","precipitation"): ("00045",None),
    ("USGS-07379960","precipitation"): ("00045",None), ("USGS-07379960","gage_height"): ("00065",None),
    ("USGS-07378810","precipitation"): ("00045",None), ("USGS-07378810","gage_height"): ("00065",None),
    ("USGS-07378746","precipitation"): ("00045",None), ("USGS-07378746","gage_height"): ("00065",None),
}


def parse_time(value: str | dt.datetime) -> dt.datetime:
    parsed = value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


def iso(value: dt.datetime) -> str:
    return parse_time(value).isoformat().replace("+00:00", "Z")


def _finite_value(row: dict) -> bool:
    value = row.get("value")
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _usable_value(row: dict) -> bool:
    if not _finite_value(row):
        return False
    if str(row.get("status","")).lower() in {"invalid","rejected","bad","missing","failed"}:
        return False
    rejected=("invalid","rejected","bad_value","missing_value")
    return not any(str(flag).lower().startswith(rejected) for flag in row.get("qc_flags",[]))


def read_receipts(root: pathlib.Path, include_predictions: bool = True) -> list[dict]:
    base = root / "research/prospective-forcing-archive/receipts"
    rows = []
    for path in sorted(base.glob("*.jsonl")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON receipt") from exc
            if include_predictions or row.get("record_type", "observation") == "observation":
                rows.append(row)
    return rows


def read_issues(root: pathlib.Path) -> list[dt.datetime]:
    output = []
    for path in sorted((root / "site/data/prospective/attempts").glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("actual_issue_time_utc"):
                output.append(parse_time(record["actual_issue_time_utc"]))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return sorted(set(output))


def read_verifications(root: pathlib.Path) -> list[dict]:
    rows = []
    for path in sorted((root / "site/data/prospective/verification").glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.extend(payload.get("revisions", []))
    return rows


def available_rows_at_issue(rows: list[dict], issue_time: str | dt.datetime) -> list[dict]:
    issue = parse_time(issue_time)
    return [row for row in rows if parse_time(row["valid_time"]) <= issue
            and parse_time(row["retrieved_at"]) <= issue]


def _expected_schedule_slots(start: dt.datetime, end: dt.datetime, minute: int = 43) -> int:
    cursor = start.replace(minute=minute, second=0, microsecond=0)
    if cursor < start:
        cursor += dt.timedelta(hours=1)
    count = 0
    while cursor <= end:
        count += 1
        cursor += dt.timedelta(hours=1)
    return count


def build_schedule_report(runs: list[dict], now: dt.datetime, lookback_hours: int = 24 * 7) -> dict:
    end = parse_time(now)
    start = end - dt.timedelta(hours=lookback_hours)
    scheduled, excluded = [], 0
    for run in runs:
        try:
            created = parse_time(run["created_at"])
        except (KeyError, ValueError, TypeError):
            continue
        if not start <= created <= end:
            continue
        if run.get("event") != "schedule":
            excluded += 1
            continue
        scheduled.append(run)
    raw_conclusions = Counter()
    starts = []
    durations = []
    successful_starts = []
    for run in scheduled:
        conclusion = run.get("conclusion") or run.get("status") or "unknown"
        raw_conclusions[conclusion] += 1
        try:
            created = parse_time(run["created_at"])
            if run.get("run_started_at"):
                started = parse_time(run["run_started_at"])
                starts.append(max(0.0, (started-created).total_seconds()))
                if run.get("conclusion")=="success":
                    successful_starts.append(started)
            if run.get("run_started_at") and run.get("updated_at") and run.get("status") == "completed":
                durations.append(max(0.0, (parse_time(run["updated_at"])-parse_time(run["run_started_at"])).total_seconds()))
        except (KeyError, ValueError, TypeError):
            pass
    expected = _expected_schedule_slots(start, end)
    failure_names={"failure","timed_out","action_required","startup_failure","stale"}
    conclusions={
        "success":raw_conclusions["success"],
        "failure":sum(raw_conclusions[name] for name in failure_names),
        "cancelled":raw_conclusions["cancelled"],
        "skipped":raw_conclusions["skipped"],
        "in_progress":raw_conclusions["in_progress"],
        "queued":raw_conclusions["queued"],
        "unknown":sum(count for name,count in raw_conclusions.items() if name not in failure_names|{"success","cancelled","skipped","in_progress","queued"}),
    }
    return {
        "window_start": iso(start), "window_end": iso(end), "expected_hourly_slots": expected,
        "actual_scheduled_runs": len(scheduled),
        "nominal_slots_without_run_record": max(0, expected-len(scheduled)),
        "slot_matching_note": "Run records have no scheduled-for timestamp; this is a count comparison, not exact slot assignment.",
        "conclusions": conclusions,"raw_conclusions":dict(sorted(raw_conclusions.items())),
        "non_schedule_runs_excluded": excluded,
        "start_delay_seconds_median": statistics.median(starts) if starts else None,
        "start_delay_seconds_max": max(starts) if starts else None,
        "workflow_duration_seconds_median": statistics.median(durations) if durations else None,
        "max_gap_between_successful_run_starts_seconds": max(((b-a).total_seconds() for a,b in zip(sorted(successful_starts),sorted(successful_starts)[1:])),default=None),
    }


def fetch_scheduled_runs(repository: str, token: str, now: dt.datetime, lookback_days: int = 7) -> list[dict]:
    """Read recent run metadata with the workflow-scoped Actions API endpoint."""
    start = parse_time(now)-dt.timedelta(days=lookback_days)
    query = urllib.parse.urlencode({"created": f">={start.date().isoformat()}", "per_page": 100, "page": 1})
    base = f"https://api.github.com/repos/{repository}/actions/workflows/forcing-archive.yml/runs"
    result, page, total = [], 1, None
    while total is None or len(result) < total:
        query = urllib.parse.urlencode({"created": f">={start.date().isoformat()}", "per_page": 100, "page": page})
        request = urllib.request.Request(base+"?"+query, headers={
            "Accept":"application/vnd.github+json", "Authorization":f"Bearer {token}",
            "X-GitHub-Api-Version":"2022-11-28", "User-Agent":"MAUL1-archive-monitor"})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
        total = int(payload.get("total_count", 0))
        batch = payload.get("workflow_runs", [])
        result.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return result


def _series_values(rows: list[dict], station: str, variable: str, issue: dt.datetime,
                   parameter_code: str | None = None, datum: str | None = None) -> dict[dt.datetime, list[dict]]:
    result = defaultdict(list)
    for row in rows:
        if row.get("record_type", "observation") != "observation":
            continue
        if row.get("station_id") != station or row.get("variable") != variable:
            continue
        if parameter_code is not None and row.get("parameter_code") != parameter_code:
            continue
        if datum is not None and row.get("datum") != datum:
            continue
        valid, retrieved = parse_time(row["valid_time"]), parse_time(row["retrieved_at"])
        if valid <= issue and retrieved <= issue:
            result[valid].append(row)
    for revisions in result.values():
        revisions.sort(key=lambda row:parse_time(row["retrieved_at"]))
    return result


def assess_window(rows: list[dict], station: str, variables: tuple[str, str], issue_time: str | dt.datetime,
                  duration_hours: int, cadence_seconds: int = 360, coverage_threshold: float = WINDOW_COVERAGE_THRESHOLD) -> dict:
    issue = parse_time(issue_time)
    start = issue-dt.timedelta(hours=duration_hours)
    var_rows = {name:_series_values(rows, station, name, issue) for name in variables}
    valid_times = set(var_rows[variables[0]]) | set(var_rows[variables[1]])
    invalid_times = 0
    paired = []
    for when in sorted(valid_times):
        left, right = var_rows[variables[0]].get(when, []), var_rows[variables[1]].get(when, [])
        if not left or not right:
            continue
        a, b = left[-1], right[-1]
        if not _usable_value(a) or not _usable_value(b):
            invalid_times += 1
            continue
        if start <= when <= issue:
            paired.append(when)
    expected = int((duration_hours*3600)/cadence_seconds)+1
    interval_edges = [start]+paired+[issue]
    gaps = [(right-left).total_seconds() for left, right in zip(interval_edges, interval_edges[1:])]
    max_gap = max(gaps) if gaps else duration_hours*3600
    coverage = min(1.0, len(paired)/expected)
    fresh = bool(paired) and (issue-paired[-1]).total_seconds() <= MAX_GAP_MULTIPLIER*cadence_seconds
    ready = coverage >= coverage_threshold and max_gap <= MAX_GAP_MULTIPLIER*cadence_seconds and fresh
    return {"station":station, "variables":list(variables), "window_hours":duration_hours,
            "expected_observation_times":expected, "available_paired_observation_times":len(paired),
            "coverage_fraction":coverage, "coverage_threshold":coverage_threshold,
            "max_gap_seconds":max_gap, "max_gap_allowed_seconds":MAX_GAP_MULTIPLIER*cadence_seconds,
            "fresh_at_issue":fresh, "invalid_vector_times":invalid_times,
            "interpolated_points":0, "ready":ready,
            "availability_cutoff":"valid_time and actual retrieved_at must both be no later than issue time"}


def assess_context(rows: list[dict], station: str, variables: list[str], issue_time: str | dt.datetime,
                   duration_hours: int = 24, parameter_code: str | None = None, datum: str | None = None) -> dict:
    issue = parse_time(issue_time)
    start = issue-dt.timedelta(hours=duration_hours)
    output=[]
    for variable in variables:
        matching = []
        for row in rows:
            if row.get("record_type", "observation") != "observation" or row.get("station_id") != station or row.get("variable") != variable:
                continue
            if parameter_code is not None and row.get("parameter_code") != parameter_code:
                continue
            if datum is not None and row.get("datum") != datum:
                continue
            valid, retrieved = parse_time(row["valid_time"]), parse_time(row["retrieved_at"])
            if start <= valid <= issue and retrieved <= issue and _usable_value(row):
                matching.append(row)
        times=sorted({parse_time(r["valid_time"]) for r in matching})
        policy=CADENCE_POLICY.get(station,{"default_seconds":900,"basis":"unverified provisional 15-minute criterion","provisional":True})
        cadence=policy["default_seconds"]
        expected=int(duration_hours*3600/cadence)+1
        gaps=[(b-a).total_seconds() for a,b in zip([start]+times,times+[issue])] if times else [duration_hours*3600]
        coverage=min(1.0,len(times)/expected) if expected else 0
        fresh=bool(times) and (issue-times[-1]).total_seconds()<=MAX_GAP_MULTIPLIER*cadence
        ready=coverage>=WINDOW_COVERAGE_THRESHOLD and max(gaps)<=MAX_GAP_MULTIPLIER*cadence and fresh
        if matching:
            output.append({"station":station,"variable":variable,"unique_valid_times":len(times),
                           "latest_valid_time":iso(times[-1]),
                           "latest_retrieved_at":max(r["retrieved_at"] for r in matching),
                           "parameter_code":parameter_code or "source-native","datum":datum or "source-defined",
                           "expected_cadence_seconds":cadence,"cadence_basis":policy["basis"],
                           "cadence_provisional":policy.get("provisional",True),"expected_times":expected,
                           "coverage_fraction":coverage,"max_gap_seconds":max(gaps),"fresh_at_issue":fresh,"ready":ready})
    available = [item["variable"] for item in output]
    ready_count=sum(item["ready"] for item in output)
    status="missing" if not available else ("sufficient observed coverage" if ready_count==len(variables) else ("partial coverage" if ready_count or output else "insufficient coverage"))
    return {"station":station,"window_hours":duration_hours,"status":status,
            "requested_variables":variables,"available_variables":available,"features":output,
            "ready_variables":[item["variable"] for item in output if item["ready"]],
            "interpolation":False,"availability_cutoff":"valid_time and actual retrieved_at must both be no later than issue time"}


def significant_rise_episodes(rows: list[dict], threshold_ft: float = 0.50, window_hours: int = 24,
                              cadence_seconds: int = 900, coverage_threshold: float = WINDOW_COVERAGE_THRESHOLD) -> list[dict]:
    """Group overlapping MAUL1 native-stage rise windows with sufficient coverage."""
    issue = max((parse_time(row["retrieved_at"]) for row in rows), default=dt.datetime.min.replace(tzinfo=UTC))
    grouped = _series_values(rows, "MAUL1", "gage_height", issue, parameter_code="00065")
    points=[]
    for when, revisions in sorted(grouped.items()):
        valid = [row for row in revisions if _usable_value(row) and row.get("unit") in ("ft","feet")
                 and str(row.get("datum", "")).startswith("native_gage_datum:")]
        if valid:
            points.append((when, float(valid[-1]["value"])))
    candidates=[]
    duration=dt.timedelta(hours=window_hours)
    expected=int(window_hours*3600/cadence_seconds)+1
    for i, (start, baseline) in enumerate(points):
        possible=[]
        for end, value in points[i+1:]:
            elapsed=end-start
            if elapsed > duration:
                break
            if elapsed >= duration-dt.timedelta(seconds=cadence_seconds*2) and value-baseline >= threshold_ft:
                segment=[(time,level) for time,level in points if start <= time <= end]
                gaps=[(b[0]-a[0]).total_seconds() for a,b in zip(segment,segment[1:])]
                coverage=min(1.0,len(segment)/expected)
                if coverage >= coverage_threshold and (not gaps or max(gaps) <= cadence_seconds*MAX_GAP_MULTIPLIER):
                    possible.append((end,value,coverage,len(segment)))
        if possible:
            end,value,coverage,count=max(possible,key=lambda x:x[1])
            candidates.append({"start_valid_time":iso(start),"end_valid_time":iso(end),
                               "rise_ft":round(value-baseline,4),"coverage_fraction":coverage,
                               "observation_count":count})
    episodes=[]
    for candidate in candidates:
        if episodes and parse_time(candidate["start_valid_time"]) <= parse_time(episodes[-1]["end_valid_time"]):
            prior=episodes[-1]
            prior["overlapping_windows_merged"] += 1
            if candidate["rise_ft"] > prior["rise_ft"]:
                prior["rise_ft"] = candidate["rise_ft"]
                prior["end_valid_time"] = candidate["end_valid_time"]
            prior["coverage_fraction"] = min(prior["coverage_fraction"],candidate["coverage_fraction"])
            prior["observation_count"] = max(prior["observation_count"],candidate["observation_count"])
        else:
            episodes.append({**candidate,"overlapping_windows_merged":1,
                             "evidence":"MAUL1 native 00065 only; no datum conversion"})
    return episodes


def match_verified_events(events: list[dict], verifications: list[dict], as_of: dt.datetime | None = None) -> list[dict]:
    """Keep only stage episodes containing at least one matured prospective target."""
    verified_times=[]
    for row in verifications:
        try:
            if row.get("observation_ingested_utc") and _finite_value({"value":row.get("observed_native_stage_ft")}):
                if as_of is None or parse_time(row["observation_ingested_utc"]) <= parse_time(as_of):
                    verified_times.append(parse_time(row["observation_valid_time_utc"]))
        except (KeyError,ValueError,TypeError):
            continue
    output=[]
    for event in events:
        start,end=parse_time(event["start_valid_time"]),parse_time(event["end_valid_time"])
        matched=sum(start <= when <= end for when in set(verified_times))
        if matched:
            output.append({**event,"prospective_verification_targets":matched,
                           "evidence":"matched to matured Phase 6 prospective verification observations"})
    return output


def significant_fall_count(rows: list[dict], threshold_ft: float = 0.50, window_hours: int = 24,
                           cadence_seconds: int = 900, coverage_threshold: float = WINDOW_COVERAGE_THRESHOLD) -> int:
    falling = []
    copied=[]
    for row in rows:
        if row.get("station_id") == "MAUL1" and row.get("variable") == "gage_height" and row.get("parameter_code") == "00065" and _finite_value(row):
            copied.append({**row,"value":-float(row["value"])})
    # Reuse the same non-interpolating event grouping on negated stage.
    return len(significant_rise_episodes(copied, threshold_ft, window_hours, cadence_seconds, coverage_threshold))


def _matured_targets(verifications: list[dict], as_of: dt.datetime | None = None) -> dict[int,int]:
    targets=defaultdict(set)
    for row in verifications:
        try:
            horizon=int(row["horizon_hours"])
            if horizon not in (6,12,24) or not row.get("observation_ingested_utc"):
                continue
            if as_of is not None and parse_time(row["observation_ingested_utc"]) > parse_time(as_of):
                continue
            if parse_time(row["observation_valid_time_utc"]) < parse_time(row["forecast_valid_time_utc"]):
                continue
            targets[horizon].add((row.get("issuance_id"), row.get("forecast_valid_time_utc"), row.get("observation_valid_time_utc")))
        except (KeyError, ValueError, TypeError):
            continue
    return {hours:len(targets[hours]) for hours in (6,12,24)}


def assess_validation_readiness(matured_targets: dict[int,int], rise_episodes: list[dict], forcing_periods: int,
                                provisional_minimum_independent_rises: int = PROVISIONAL_INDEPENDENT_RISES_FOR_REVIEW) -> dict:
    count=len(rise_episodes)
    if count >= provisional_minimum_independent_rises:
        status="Candidate for review"
    elif count > 0:
        status="Evidence accumulating"
    else:
        status="Insufficient independent events"
    return {"status":status,"matured_forecast_targets":{"6h":matured_targets.get(6,0),"12h":matured_targets.get(12,0),"24h":matured_targets.get(24,0)},
            "significant_rise_episodes_0_50_ft_in_24h":count,"significant_fall_episodes_0_50_ft_in_24h":0,
            "sufficiently_observed_coastal_forcing_periods":forcing_periods,
            "provisional_review_threshold_independent_rises":provisional_minimum_independent_rises,
            "threshold_note":"Provisional research review criterion only; not a statistically justified minimum and not validation.",
            "model_validated":False}


def _health_files(root: pathlib.Path) -> list[tuple[pathlib.Path,dict]]:
    items=[]
    for path in sorted((root/"research/prospective-forcing-archive/health").glob("*.json")):
        try:
            items.append((path,json.loads(path.read_text(encoding="utf-8"))))
        except (OSError,json.JSONDecodeError):
            continue
    return items


def _read_merge_time(root: pathlib.Path) -> dt.datetime:
    try:
        raw=subprocess.check_output(["git","show","-s","--format=%cI",RECOVERY_MERGE_SHA],cwd=root,text=True).strip()
        return parse_time(raw)
    except (OSError,subprocess.CalledProcessError,ValueError):
        return RECOVERY_MERGED_AT


def _storage_report(root: pathlib.Path) -> dict:
    try:
        sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
        import archive_growth
        tracked=archive_growth.git(root,"ls-files","--cached","--others","--exclude-standard","-z").split("\0")
        tracked=[p for p in tracked if p]
        archive_paths=[p for p in tracked if p.startswith("research/prospective-forcing-archive/")]
        archive_bytes=archive_growth.bytes_of(root,archive_paths)
        working_bytes=archive_growth.bytes_of(root,tracked)
        pack_bytes=0
        for line in archive_growth.git(root,"count-objects","-v").splitlines():
            if line.startswith("size-pack: "):
                pack_bytes=int(line.split(":",1)[1].strip())*1024
        growth_7d, _=archive_growth.history_growth(root,7)
        return {"working_tree_bytes":working_bytes,"archive_files_bytes":archive_bytes,
                "git_pack_bytes":pack_bytes,"new_unique_data_blob_bytes_7d":growth_7d,
                "measurement":"working Git checkout; pack and payload are distinct measures"}
    except (OSError,subprocess.CalledProcessError,ValueError):
        return {"status":"unavailable","reason":"Git storage measurements could not be read"}


def _source_health_summary(health: list[tuple[pathlib.Path,dict]], now: dt.datetime) -> dict:
    cutoff=now-dt.timedelta(days=7)
    recent=[]
    failures=Counter()
    core_failures=[]
    by_source=defaultdict(list)
    for path, report in health:
        try:
            completed=parse_time(report.get("completed_at") or report.get("started_at"))
        except (ValueError,TypeError):
            continue
        if completed < cutoff:
            continue
        recent.append((completed,report))
        for source in report.get("sources",[]):
            retrieved=source.get("retrieved_at") or report.get("completed_at")
            try:
                attempted_at=parse_time(retrieved)
            except (ValueError,TypeError):
                attempted_at=completed
            by_source[source.get("source","unknown")].append((attempted_at,source.get("status"),bool(source.get("critical"))))
            if source.get("status") not in ("success",):
                failures[source.get("source","unknown")]+=1
                if source.get("critical"):
                    core_failures.append({"source":source.get("source"),"status":source.get("status"),"retrieved_at":source.get("retrieved_at")})
    latest=max(recent,key=lambda pair:pair[0]) if recent else None
    if latest:
        latest_time,latest_report=latest
        latest_age=max(0,(now-latest_time).total_seconds())
        latest_critical_failures=[{"source":s.get("source"),"status":s.get("status")} for s in latest_report.get("sources",[]) if s.get("critical") and s.get("status")!="success"]
        latest_run_ok=not latest_report.get("critical_failures") and not latest_critical_failures
    else:
        latest_time,latest_age,latest_run_ok,latest_critical_failures=None,None,False,[]
    source_summary={}
    for name,attempts in sorted(by_source.items()):
        attempts.sort(key=lambda item:item[0])
        successes=[when for when,status,_ in attempts if status=="success"]
        source_summary[name]={"latest_attempt_at":iso(attempts[-1][0]),"latest_status":attempts[-1][1],
            "failures_last_7d":sum(status!="success" for _,status,_ in attempts),
            "latest_success_at":iso(successes[-1]) if successes else None,
            "age_since_latest_success_seconds":max(0,(now-successes[-1]).total_seconds()) if successes else None,
            "max_gap_between_successes_seconds":max(((b-a).total_seconds() for a,b in zip(successes,successes[1:])),default=None),
            "critical_source":any(critical for _,_,critical in attempts)}
    return {"health_reports_last_7d":len(recent),"source_failure_counts_last_7d":dict(sorted(failures.items())),
            "sources":source_summary,
            "critical_source_failure_count_last_7d":len(core_failures),"latest_collection_completed_at":iso(latest_time) if latest_time else None,
            "latest_collection_age_seconds":latest_age,"latest_collection_critical_feeds_ok":latest_run_ok,
            "latest_collection_critical_failures":latest_critical_failures}


def _recovery_deployment_report(root: pathlib.Path, rows: list[dict], runs: list[dict], merge_time: dt.datetime) -> dict:
    after=[run for run in runs if run.get("event")=="schedule" and run.get("created_at") and parse_time(run["created_at"]) >= merge_time]
    repaired=[]
    for run in after:
        sha=run.get("head_sha")
        if not sha:
            continue
        try:
            subprocess.run(["git","merge-base","--is-ancestor",RECOVERY_MERGE_SHA,sha],cwd=root,
                           check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            repaired.append(run)
        except (OSError,subprocess.CalledProcessError):
            continue
    successful=[run for run in repaired if run.get("conclusion")=="success" and run.get("run_started_at") and run.get("updated_at")]
    recovered=[]
    for row in rows:
        if row.get("acquisition_mode")!="delayed_recovery":
            continue
        retrieved=parse_time(row["retrieved_at"])
        if any(parse_time(run["run_started_at"]) <= retrieved <= parse_time(run["updated_at"]) for run in successful):
            recovered.append(row)
    return {"repair_merge_commit":RECOVERY_MERGE_SHA,"repair_merged_at":iso(merge_time),
            "post_merge_scheduled_runs":len(after),"latest_post_merge_scheduled_run":max(after,key=lambda x:x["created_at"]).get("html_url") if after else None,
            "repaired_code_scheduled_runs":len(repaired),
            "successful_post_merge_scheduled_runs":len(successful),
            "delayed_recovery_receipts_acquired_after_merge":len(recovered),
            "production_recovery_observed":bool(successful and recovered),
            "verification_state":"production scheduled recovery observed" if successful and recovered else
                ("repaired code has run on schedule; delayed recovery not yet observed" if successful else "awaiting first successful post-merge scheduled collection of the merged SHA")}


def _decorate_coverage(completeness: dict, rows: list[dict]) -> list[dict]:
    output=[]
    for item in completeness["series"]:
        station=item.get("station_id")
        matching=[row for row in rows if row.get("source")==item.get("source")
                  and row.get("station_id")==station and row.get("variable")==item.get("variable")
                  and row.get("parameter_code")==item.get("parameter_code")
                  and row.get("record_type","observation")=="observation"]
        policy=CADENCE_POLICY.get(station)
        if not policy:
            output.append({**item,"expected_cadence_seconds":None,"coverage_fraction":None,
                           "cadence_basis":"not configured; coverage threshold not inferred",
                           "invalid_value_receipts":sum(not _usable_value(r) for r in matching),
                           "receipt_with_qc_flags":sum(bool(r.get("qc_flags")) for r in matching),
                           "latest_valid_time":max((r["valid_time"] for r in matching),default=None),
                           "latest_retrieved_at":max((r["retrieved_at"] for r in matching),default=None)})
            continue
        cadence=policy["default_seconds"]
        count=item["unique_valid_timestamps"]
        first,last=item.get("valid_time_min"),item.get("valid_time_max")
        span=(parse_time(last)-parse_time(first)).total_seconds() if first and last else 0
        expected=int(span/cadence)+1 if span else count
        output.append({**item,"expected_cadence_seconds":cadence,
                       "expected_intervals":expected,"coverage_fraction":min(1.0,count/expected) if expected else 0,
                       "cadence_basis":policy["basis"],"cadence_provisional":policy["provisional"],
                       "invalid_value_receipts":sum(not _usable_value(row) for row in matching),
                       "receipt_with_qc_flags":sum(bool(row.get("qc_flags")) for row in matching),
                       "latest_valid_time":max((r["valid_time"] for r in matching),default=None),
                       "latest_retrieved_at":max((r["retrieved_at"] for r in matching),default=None)})
    return output


def _archive_health_status(source: dict, schedule: dict, series: list[dict]) -> tuple[str,list[str]]:
    reasons=[]
    age=source.get("latest_collection_age_seconds")
    expected=schedule["expected_hourly_slots"]
    actual=schedule["actual_scheduled_runs"]
    if source["health_reports_last_7d"] == 0 or expected == 0:
        return "Insufficient evidence",["No recent source-health or scheduled-run evidence was available."]
    if age is None or age > 24*3600 or not source["latest_collection_critical_feeds_ok"]:
        reasons.append("No recent successful collection of all critical feeds.")
        return "Critical",reasons
    if source["critical_source_failure_count_last_7d"]:
        reasons.append("One or more critical source failures occurred in the last seven days.")
    if actual < 0.75*expected:
        reasons.append("Recorded scheduled-run count is below 75% of nominal hourly slots; exact slot matching is unavailable.")
    if any((s.get("max_gap_seconds") or 0) > 6*3600 for s in series if s.get("station_id") in ("NWCL1","DENL1","MDLL1","MAUL1")):
        reasons.append("A core-series observation gap exceeds six hours.")
    if reasons:
        return "Degraded",reasons
    return "Healthy",["Recent critical feeds succeeded and provisional cadence checks were within configured bounds."]


def build_daily_report(root: pathlib.Path, now: dt.datetime, runs: list[dict]) -> dict:
    import archive_completeness
    now=parse_time(now)
    rows=read_receipts(root)
    schedule=build_schedule_report(runs,now)
    source=_source_health_summary(_health_files(root),now)
    completeness=archive_completeness.build_report(root)
    series=_decorate_coverage(completeness,rows)
    health_status,reasons=_archive_health_status(source,schedule,series)
    recovery=_recovery_deployment_report(root,rows,runs,_read_merge_time(root))
    return {"schema_version":"archive-health-1","as_of":iso(now),"status":"Research / Shadow Evaluation / Not Operational",
            "archive_health":{"assessment":health_status,"reasons":reasons,"thresholds":{
                "recent_critical_collection_max_age_hours":24,"critical_source_failure_lookback_days":7,
                "minimum_scheduled_run_fraction_for_healthy":0.75,"maximum_core_gap_hours":6,
                "note":"Cadence coverage is source-policy-based; exact scheduled slots are not observable in run metadata."}},
            "collection":{"actions_schedule":schedule,"source_health":source,"repair_deployment":recovery},
            "coverage":{"receipt_count":len(rows),"unique_series_count":len(series),"series":series,
                        "issue_availability_count":len(completeness["issue_availability"]),
                        "issue_availability_cutoff":"both valid_time and actual retrieved_at <= authentic issue_time"},
            "storage":_storage_report(root)}


def _wind_readiness(rows: list[dict], issues: list[dt.datetime]) -> dict:
    features={}
    for hours in (6,12,24,48,72):
        outcomes=[assess_window(rows,"NWCL1",("wind_u","wind_v"),issue,hours,360) for issue in issues]
        ready=sum(result["ready"] for result in outcomes)
        features[f"{hours}h_wind_forcing"]={"issue_windows_assessed":len(outcomes),"ready_issue_windows":ready,
            "ready_fraction":ready/len(outcomes) if outcomes else 0,
            "assessment":"Sufficient observed coverage" if outcomes and ready/len(outcomes)>=ISSUE_WINDOW_PASS_THRESHOLD else ("Partial coverage" if ready else "Insufficient coverage"),
            "source":"NWCL1 NOAA CO-OPS paired wind_u and wind_v","expected_cadence_seconds":360,
            "coverage_threshold":WINDOW_COVERAGE_THRESHOLD,"maximum_gap_multiplier":MAX_GAP_MULTIPLIER,
            "provisional":True}
    return features


def _tide_residual_pairs(rows: list[dict], issue: dt.datetime, window_hours: int = 24) -> dict:
    start=issue-dt.timedelta(hours=window_hours)
    obs=defaultdict(list); predictions=defaultdict(list)
    for row in rows:
        if row.get("station_id")!="NWCL1":
            continue
        valid,retrieved=parse_time(row["valid_time"]),parse_time(row["retrieved_at"])
        if not start <= valid <= issue or retrieved > issue:
            continue
        if row.get("record_type")=="observation" and row.get("variable")=="water_level" and row.get("datum")=="MLLW" and _usable_value(row):
            obs[valid].append(row)
        if row.get("record_type")=="prediction" and row.get("variable")=="tide_prediction" and row.get("datum")=="MLLW" and _usable_value(row):
            predictions[valid].append(row)
    for revisions in (*obs.values(),*predictions.values()):
        revisions.sort(key=lambda row:parse_time(row["retrieved_at"]))
    times=sorted(set(obs)&set(predictions))
    residuals=[float(obs[t][-1]["value"])-float(predictions[t][-1]["value"]) for t in times]
    expected=int(window_hours*3600/360)+1
    coverage=min(1.0,len(times)/expected)
    gaps=[(b-a).total_seconds() for a,b in zip([start]+times,times+[issue])] if times else [window_hours*3600]
    ready=coverage>=WINDOW_COVERAGE_THRESHOLD and max(gaps)<=3*360
    return {"window_hours":window_hours,"datum":"MLLW","matched_exact_valid_times":len(times),
            "mean_residual_ft":statistics.mean(residuals) if residuals else None,
            "coverage_fraction":coverage,"max_gap_seconds":max(gaps),"ready":ready,
            "status":"sufficient observed coverage" if ready else ("partial coverage" if times else "missing matched observations/predictions"),
            "method":"exact valid-time matches only; no datum conversion or temporal interpolation"}


def _aggregate_context(rows: list[dict], issues: list[dt.datetime], station: str, variable: str,
                       duration_hours: int, parameter_code: str | None = None, datum: str | None = None) -> dict:
    results=[assess_context(rows,station,[variable],issue,duration_hours,parameter_code,datum)["features"] for issue in issues]
    values=[group[0] for group in results if group]
    ready=sum(bool(item["ready"]) for item in values)
    return {"station":station,"variable":variable,"parameter_code":parameter_code or "source-native",
            "datum":datum or "source-defined","window_hours":duration_hours,
            "issue_windows_assessed":len(issues),"windows_with_observations":len(values),
            "ready_issue_windows":ready,"ready_fraction":ready/len(issues) if issues else 0,
            "median_coverage_fraction":statistics.median([item["coverage_fraction"] for item in values]) if values else 0,
            "latest_valid_time_at_last_issue":values[-1]["latest_valid_time"] if values else None,
            "assessment":"Sufficient observed coverage" if issues and ready/len(issues)>=ISSUE_WINDOW_PASS_THRESHOLD else
                ("Partial coverage" if ready or values else "Insufficient coverage")}


def build_weekly_report(root: pathlib.Path, now: dt.datetime, runs: list[dict] | None = None) -> dict:
    now=parse_time(now)
    rows=read_receipts(root,include_predictions=True)
    issues=read_issues(root)
    verifications=read_verifications(root)
    wind=_wind_readiness([r for r in rows if r.get("record_type","observation")=="observation"],issues)
    requested={"NWCL1":["water_level"],"DENL1":["discharge","gage_height"],"MDLL1":["gage_height"],
               "MAUL1":["gage_height","water_level"],"KNEW":["wind_speed","wind_direction"],
               "MCHL1-USGS":["gage_height"],"USGS-301828090363100":["precipitation"],
               "USGS-07379960":["precipitation","gage_height"],"USGS-07378810":["precipitation","gage_height"],
               "USGS-07378746":["precipitation","gage_height"]}
    issue_context=[]
    durations=(24,72)
    for station,variables in requested.items():
        for variable in variables:
            for duration in durations:
                parameter,datum=CONTEXT_PARAMETER_POLICY.get((station,variable),(None,None))
                issue_context.append(_aggregate_context(rows,issues,station,variable,duration,parameter,datum))
    latest_issue=issues[-1] if issues else now
    residual=_tide_residual_pairs(rows,latest_issue)
    residual_issue_windows=[_tide_residual_pairs(rows,issue,24) for issue in issues]
    residual_ready=sum(item["ready"] for item in residual_issue_windows)
    residual_summary={"issue_windows_assessed":len(residual_issue_windows),"ready_issue_windows":residual_ready,
                      "ready_fraction":residual_ready/len(residual_issue_windows) if residual_issue_windows else 0,
                      "latest_issue":residual}
    rise_candidates=significant_rise_episodes(rows)
    rises=match_verified_events(rise_candidates,verifications,now)
    falls=significant_fall_count(rows)
    # Count passing issue windows, not statistically independent episodes.
    forced_periods=wind.get("24h_wind_forcing",{}).get("ready_issue_windows",0)
    validation=assess_validation_readiness(_matured_targets(verifications,now),rises,forced_periods)
    recovery=_recovery_deployment_report(root,rows,runs or [],_read_merge_time(root))
    assessments=[item["assessment"] for item in wind.values()]
    assessments.append("Sufficient observed coverage" if residual_summary["ready_fraction"]>=ISSUE_WINDOW_PASS_THRESHOLD and issues else ("Partial coverage" if residual_summary["ready_issue_windows"] else "Insufficient coverage"))
    core_context=[item for item in issue_context if item["station"] in ("MDLL1","DENL1","MAUL1") and item["window_hours"]==24]
    assessments.extend(item["assessment"] for item in core_context)
    if assessments and all(value=="Sufficient observed coverage" for value in assessments):
        feature_status="Sufficient observed coverage"
    elif any(value in ("Sufficient observed coverage","Partial coverage") for value in assessments):
        feature_status="Partial coverage"
    else:
        feature_status="Insufficient coverage"
    return {"schema_version":"scientific-readiness-1","as_of":iso(now),"status":"Research / Shadow Evaluation / Not Operational",
            "feature_engineering_readiness":{"assessment":feature_status,"wind_history":wind,
                "nwcl1_water_level_residual_latest_issue":residual_summary,
                "time_dependent_context_features":issue_context,
                "issue_time_context_availability":issue_context,
                "criteria":{"window_coverage_fraction":WINDOW_COVERAGE_THRESHOLD,"maximum_gap_multiplier":MAX_GAP_MULTIPLIER,
                    "issue_windows_that_must_pass_fraction":ISSUE_WINDOW_PASS_THRESHOLD,
                    "wind_cadence_seconds":360,"issue_cutoff":"valid_time and actual retrieved_at no later than issue time",
                    "long_gap_policy":"do not interpolate; a gap above threshold makes the window insufficient"}},
            "independent_forecast_validation":{**validation,"significant_fall_episodes_0_50_ft_in_24h":falls,
                "matured_target_count_method":"unique issuance, forecast-valid-time, observation-valid-time per horizon; revisions and overlapping model rows are deduplicated",
                "rise_episode_method":"MAUL1 native USGS 00065 only; 24-hour windows require at least 80% of the provisional 15-minute slots and no gap over 45 minutes; overlapping windows are merged; an event is counted only when its interval includes a matured Phase 6 prospective verification target",
                "observed_rise_candidates_without_matured_verification":len(rise_candidates)-len(rises)},
            "repair_deployment":recovery,
            "next_phase_gate":{"status":"not cleared" if feature_status!="Sufficient observed coverage" or validation["status"]!="Candidate for review" else "candidate for human review",
                "blockers":["post-merge scheduled recovery has not yet been demonstrated in production" if not recovery["production_recovery_observed"] else "",
                            "wind history, residual, or core stage/discharge windows do not yet meet provisional issue-time coverage/freshness gates" if feature_status!="Sufficient observed coverage" else "",
                            "fewer than the provisional three distinct grouped significant-rise episodes" if validation["status"]!="Candidate for review" else ""],
                "most_useful_next_action":"allow repaired scheduled collections to accumulate, then review coverage and issue-time availability before proposing a challenger experiment"}}


def render_daily(report: dict) -> str:
    health=report["archive_health"]
    schedule=report["collection"]["actions_schedule"]
    source=report["collection"]["source_health"]
    recovery=report["collection"]["repair_deployment"]
    storage=report["storage"]
    lines=["# Daily archive health","","**Research / Shadow Evaluation / Not Operational**","",
           f"As of: `{report['as_of']}`","",f"## Archive health: {health['assessment']}"]
    lines.extend(f"- {reason}" for reason in health["reasons"])
    lines.extend(["", "## Collection", "",
        f"- Scheduled workflow runs: {schedule['actual_scheduled_runs']}/{schedule['expected_hourly_slots']} nominal hourly slots in the trailing window; "
        f"success {schedule['conclusions']['success']}, failed {schedule['conclusions']['failure']}, cancelled {schedule['conclusions']['cancelled']}, skipped {schedule['conclusions']['skipped']}, "
        f"other non-schedule runs excluded {schedule['non_schedule_runs_excluded']}.",
        f"- Latest source-health report: {source['latest_collection_completed_at'] or 'none'}; critical feeds OK: {source['latest_collection_critical_feeds_ok']}.",
        f"- PR #77 repair: {recovery['verification_state']}; post-merge scheduled runs {recovery['post_merge_scheduled_runs']}; delayed recovery receipts after merge {recovery['delayed_recovery_receipts_acquired_after_merge']}.",
        "- Schedule counts compare run records to nominal slots; exact missed slots cannot be identified from GitHub run metadata.",
        f"- Longest interval between successful scheduled run starts: {schedule['max_gap_between_successful_run_starts_seconds'] if schedule['max_gap_between_successful_run_starts_seconds'] is not None else 'unknown'} seconds.",
        "", "## Provider source health", "",
        "| Source | Latest status | Latest successful retrieval | Age | Failures (7d) | Largest successful gap |",
        "|---|---|---|---:|---:|---:|"])
    for name,item in source["sources"].items():
        age="—" if item["age_since_latest_success_seconds"] is None else f"{item['age_since_latest_success_seconds']/3600:.2f} h"
        largest="—" if item["max_gap_between_successes_seconds"] is None else f"{item['max_gap_between_successes_seconds']/3600:.2f} h"
        lines.append(f"| {name} | {item['latest_status']} | {item['latest_success_at'] or 'none'} | {age} | {item['failures_last_7d']} | {largest} |")
    lines.extend(["", "## Storage", ""])
    if storage.get("status")=="unavailable":
        lines.append("Git storage measurement unavailable.")
    else:
        lines.append(f"Working checkout {storage['working_tree_bytes']} bytes; archive files {storage['archive_files_bytes']} bytes; Git pack {storage['git_pack_bytes']} bytes; trailing seven-day new data blobs {storage['new_unique_data_blob_bytes_7d']} bytes.")
    lines.extend(["", "## Series coverage", "", "| Station | Variable | Unique times | Expected times | Expected cadence | Coverage | Maximum gap | Latest valid | Latest retrieved | Revisions | Delayed recovery | Invalid | QC flagged |", "|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|"])
    for item in report["coverage"]["series"]:
        cadence="—" if item.get("expected_cadence_seconds") is None else f"{item['expected_cadence_seconds']/60:g} min"+ (" provisional" if item.get("cadence_provisional") else "")
        coverage="—" if item.get("coverage_fraction") is None else f"{item['coverage_fraction']:.1%}"
        gap="—" if item.get("max_gap_seconds") is None else f"{item['max_gap_seconds']/3600:.2f} h"
        lines.append(f"| {item['station_id']} | {item['variable']} | {item['unique_valid_timestamps']} | {item.get('expected_intervals','—')} | {cadence} | {coverage} | {gap} | {item.get('latest_valid_time') or '—'} | {item.get('latest_retrieved_at') or '—'} | {item['revision_valid_times']} | {item['delayed_recovery_records']} | {item['invalid_value_receipts']} | {item['receipt_with_qc_flags']} |")
    return "\n".join(lines)+"\n"


def render_weekly(report: dict) -> str:
    feature=report["feature_engineering_readiness"]
    validation=report["independent_forecast_validation"]
    gate=report["next_phase_gate"]
    lines=["# Weekly scientific-readiness assessment","","**Research / Shadow Evaluation / Not Operational**","",
           f"As of: `{report['as_of']}`","",f"## Feature engineering: {feature['assessment']}","",
           "| Wind history | Ready issue windows | Assessed issues | Status |", "|---|---:|---:|---|"]
    for name,item in feature["wind_history"].items():
        lines.append(f"| {name} | {item['ready_issue_windows']} | {item['issue_windows_assessed']} | {item['assessment']} |")
    residual=feature["nwcl1_water_level_residual_latest_issue"]
    latest_residual=residual["latest_issue"]
    lines.extend(["",f"NWCL1 observed-minus-predicted MLLW residual: {latest_residual['status']}; exact matched times {latest_residual['matched_exact_valid_times']}; issue windows ready {residual['ready_issue_windows']}/{residual['issue_windows_assessed']}.",
                  "", "| Context feature | Window | Ready issue windows | Assessed | Status |", "|---|---:|---:|---:|---|"])
    for item in feature["time_dependent_context_features"]:
        lines.append(f"| {item['station']} {item['variable']} | {item['window_hours']}h | {item['ready_issue_windows']} | {item['issue_windows_assessed']} | {item['assessment']} |")
    lines.extend([
                  "Issue-time context requires both valid and actual retrieval times at or before each authentic issuance; later receipts are excluded.",
                  f"PR #77 production verification: {report['repair_deployment']['verification_state']} (successful repaired-code schedules: {report['repair_deployment'].get('successful_post_merge_scheduled_runs',0)}; delayed receipts acquired within those runs: {report['repair_deployment']['delayed_recovery_receipts_acquired_after_merge']}).",
                  "",f"## Independent forecast evidence: {validation['status']}","",
                  f"Matured targets: 6h {validation['matured_forecast_targets']['6h']}, 12h {validation['matured_forecast_targets']['12h']}, 24h {validation['matured_forecast_targets']['24h']}.",
                  f"MAUL1 ≥0.50-ft rise episodes: {validation['significant_rise_episodes_0_50_ft_in_24h']}; significant falls: {validation['significant_fall_episodes_0_50_ft_in_24h']}.",
                  f"Sufficiently observed coastal-forcing issue windows: {validation['sufficiently_observed_coastal_forcing_periods']}.",
                  f"Provisional review criterion: {validation['provisional_review_threshold_independent_rises']} independent rise episodes; this is not a statistical sufficiency claim. Model validated: {validation['model_validated']}.",
                  "",f"## Next-phase gate: {gate['status']}"])
    lines.extend(f"- {blocker}" for blocker in gate["blockers"] if blocker)
    lines.extend([f"- Next action: {gate['most_useful_next_action']}","",
                  "No long gaps are interpolated. Rise windows use MAUL1 native 00065; absolute gradients across station datums are not calculated."])
    return "\n".join(lines)+"\n"


def write_json_if_changed(path: pathlib.Path, data: dict) -> bool:
    path=pathlib.Path(path)
    text=json.dumps(data,indent=2,sort_keys=True)+"\n"
    if path.exists() and path.read_text(encoding="utf-8")==text:
        return False
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding="utf-8")
    return True


def write_text_if_changed(path: pathlib.Path, text: str) -> bool:
    path=pathlib.Path(path)
    if path.exists() and path.read_text(encoding="utf-8")==text:
        return False
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding="utf-8")
    return True


def append_step_summary(text: str) -> None:
    print(text)
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as stream:
            stream.write("\n"+text)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=pathlib.Path,default=pathlib.Path("."))
    parser.add_argument("--period",choices=("daily","weekly"),required=True)
    parser.add_argument("--now",help="fixed timezone-aware evaluation time for reproducible local runs")
    parser.add_argument("--repository",default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--github-token",default=os.environ.get("GITHUB_TOKEN"))
    args=parser.parse_args()
    now=parse_time(args.now) if args.now else dt.datetime.now(UTC)
    runs=[]
    error=None
    if args.repository and args.github_token:
        try:
            runs=fetch_scheduled_runs(args.repository,args.github_token,now)
        except (OSError,ValueError,urllib.error.URLError,json.JSONDecodeError) as exc:
            error=f"GitHub Actions run history unavailable: {type(exc).__name__}: {exc}"
    else:
        error="GitHub Actions run history unavailable: repository and GITHUB_TOKEN context are required"
    if args.period=="daily":
        report=build_daily_report(args.root.resolve(),now,runs)
        if error:
            report["collection"]["actions_schedule"]["history_error"]=error
            report["archive_health"]["assessment"]="Insufficient evidence"
            report["archive_health"]["reasons"].append(error)
        out=args.root/"research/prospective-forcing-archive/monitoring/daily"/f"{now.date().isoformat()}"
        write_json_if_changed(out.with_suffix(".json"),report)
        text=render_daily(report)
        write_text_if_changed(out.with_suffix(".md"),text)
    else:
        report=build_weekly_report(args.root.resolve(),now,runs)
        if error:
            report["repair_deployment"]["actions_history_error"]=error
            report["repair_deployment"]["verification_state"]="schedule history unavailable; production execution unverified"
            report["next_phase_gate"]["blockers"].append(error)
        out=args.root/"research/prospective-forcing-archive/monitoring/weekly"/f"{now.date().isoformat()}"
        write_json_if_changed(out.with_suffix(".json"),report)
        text=render_weekly(report)
        write_text_if_changed(out.with_suffix(".md"),text)
    append_step_summary(text)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
