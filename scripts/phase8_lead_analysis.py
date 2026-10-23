"""Retrospective, valid-time causal evidence screening for MAUL1 response events.

This is an observational evidence study, not a forecast. It reuses Phase 4's
fixed physical screens at each UTC decision time; each screen only evaluates
completed bins and its coastal/lake/wind conditions require a complete six-hour
window. Historical receipt times are unavailable, so leads are idealized
valid-time diagnostics and cannot be presented as operational warning time.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import statistics
import sys
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import evidence
import phase4

UTC = dt.timezone.utc
HOUR = dt.timedelta(hours=1)
ARCHIVE_START = dt.datetime(2016, 1, 1, tzinfo=UTC)
SCHEMA = "phase8.lead-analysis.v1"
SIGNALS = ("river", "coastal", "residual", "wind", "lake", "pass_context")
PATHWAYS = ("river", "coastal")
SENSITIVITY_FACTORS = (0.75, 1.0, 1.25)
LAG_WINDOWS = (3, 6, 12, 24, 36)


def stamp(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def iso(value: dt.datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def quantile(values, p):
    values = sorted(float(x) for x in values)
    if not values:
        return None
    position = (len(values) - 1) * p
    low, high = math.floor(position), math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def signal_episodes(screen_rows, signal):
    """Return starts of present runs; unknown/gaps break a run."""
    episodes = []
    previous = None
    previous_time = None
    for issue, row in sorted(screen_rows.items()):
        if previous_time is not None and issue - previous_time != HOUR:
            previous = None
        state = row["flags"].get(signal, "unknown")
        if state == "present" and previous != "present":
            episodes.append(issue)
        previous = state
        previous_time = issue
    return episodes


def nearest_upcoming_event(detection_time, events, max_lead_hours=72):
    """Assign a detector episode to at most one nearest future MAUL1 onset."""
    candidates = []
    for event in events:
        onset = event.get("_onset")
        if onset is None or onset < detection_time:
            continue
        lead = (onset - detection_time).total_seconds() / 3600
        if lead <= max_lead_hours:
            candidates.append((lead, event["event_id"]))
    return min(candidates)[1] if candidates else None


def first_confirmation(screen_rows, signal, start, end, ordered_issues=None):
    """First issue-time confirmation; Phase 4 rows are already complete-bin screens."""
    ordered_issues = ordered_issues or sorted(screen_rows)
    left = bisect.bisect_left(ordered_issues, start)
    right = bisect.bisect_right(ordered_issues, end)
    for issue in ordered_issues[left:right]:
        if screen_rows[issue]["flags"].get(signal, "unknown") == "present":
            return issue
    return None


def clean_mchl1_context_row(row):
    """Apply only the documented Phase 7 sentinel-contamination gate to MCHL1."""
    value = row.get("value")
    if (row.get("station") == "MCHL1" and row.get("variable") == "stage"
            and isinstance(value, (int, float)) and math.isfinite(value) and abs(value) >= 1_000_000):
        cleaned = dict(row, value=None, missing=True,
                       phase8_cleaning_reason="phase7_documented_hads_sentinel_or_contamination")
        return cleaned, True
    return dict(row), False


def expanding_discharge_thresholds(index, issues):
    """Exact Phase 4 expanding q90 thresholds using a Fenwick order-statistic tree.

    This matches phase4.replay_thresholds while avoiding quadratic sorted-list
    insertion when evaluating every historical hour.
    """
    cutoff = phase4.BOUNDARY - HOUR * 72
    samples = sorted((time, float(row["value"])) for time, row in index.get(("DENL1", "discharge"), {}).items()
                     if ARCHIVE_START <= time < cutoff and evidence.valid(row, "cfs"))
    ordered_values = sorted({value for _, value in samples})
    coordinates = {value: pos for pos, value in enumerate(ordered_values)}
    tree = [0] * (len(ordered_values) + 1)

    def add(pos):
        i = pos + 1
        while i < len(tree):
            tree[i] += 1
            i += i & -i

    def kth(rank):
        # rank is zero-based; return the value at that order statistic.
        target = rank + 1
        index_in_tree = 0
        bit = 1 << (len(ordered_values).bit_length() - 1) if ordered_values else 0
        while bit:
            candidate = index_in_tree + bit
            if candidate < len(tree) and tree[candidate] < target:
                target -= tree[candidate]
                index_in_tree = candidate
            bit >>= 1
        return ordered_values[index_in_tree]

    result = {}
    cursor = count = 0
    cutoff_values = sorted(issues)
    for issue in cutoff_values:
        end = min(issue, cutoff)
        while cursor < len(samples) and samples[cursor][0] + HOUR <= end:
            add(coordinates[samples[cursor][1]])
            count += 1
            cursor += 1
        if count >= 1000:
            position = (count - 1) * .9
            low, high = math.floor(position), math.ceil(position)
            q90 = kth(low) + (kth(high) - kth(low)) * (position - low)
        else:
            q90 = evidence.DEFAULTS["discharge_high_cfs"]
        result[issue] = {"discharge_high_cfs": q90}
    return result


def forward_response_status(detection_time, horizon_hours, events, archive_end):
    """Classify response follow-up without turning unknown onset into a miss."""
    horizon_end = detection_time + HOUR * horizon_hours
    if archive_end < horizon_end:
        return "right_censored"
    for event in events:
        onset = event.get("_onset")
        if onset is not None and detection_time < onset <= horizon_end:
            return "response"
    for event in events:
        if event.get("onset_known"):
            continue
        left, right = event.get("_trough"), event.get("_peak")
        if left is not None and right is not None and left <= horizon_end and right > detection_time:
            return "onset_uncertain"
    return "no_catalog_response"


def load_events(path):
    events = []
    with pathlib.Path(path).open(newline="", encoding="utf-8") as stream:
        for source in csv.DictReader(stream):
            row = dict(source)
            row["onset_known"] = source.get("onset_known", "").lower() == "true"
            row["_onset"] = stamp(source["onset_utc"]) if row["onset_known"] and source.get("onset_utc") else None
            row["_trough"] = stamp(source["trough_utc"]) if source.get("trough_utc") else None
            row["_peak"] = stamp(source["peak_utc"]) if source.get("peak_utc") else None
            events.append(row)
    return events


def load_controls(path):
    with pathlib.Path(path).open(newline="", encoding="utf-8") as stream:
        rows = [dict(row) for row in csv.DictReader(stream)]
    return [row for row in rows if row.get("status") == "eligible_control_candidate"]


def load_classifications(path):
    if not pathlib.Path(path).exists():
        return {}
    with pathlib.Path(path).open(newline="", encoding="utf-8") as stream:
        return {row["record_id"]: row["category"] for row in csv.DictReader(stream)
                if row.get("sample_type") == "response_event"}


def _screen_summary(issues, rows, signal):
    eligible = [rows[t]["flags"].get(signal, "unknown") for t in issues]
    known = [state for state in eligible if state != "unknown"]
    return {"assessment_hours": len(issues), "eligible_hours": len(known),
            "unknown_hours": len(eligible) - len(known),
            "eligible_fraction": round(len(known) / len(eligible), 4) if eligible else None,
            "present_hours": sum(state == "present" for state in known),
            "absent_hours": sum(state == "absent" for state in known)}


def build_analysis(root, output):
    root = pathlib.Path(root).resolve()
    history = root / "site/data/history"
    output = pathlib.Path(output).resolve()
    if output == history or history in output.parents:
        raise ValueError("Phase 8 output cannot overwrite or be nested inside the source archive")

    event_path = history / "phase3b/response-events.csv"
    control_path = history / "phase3b/control-windows.csv"
    class_path = history / "phase4/classifications.csv"
    events, controls = load_events(event_path), load_controls(control_path)
    classifications = load_classifications(class_path)

    index = phase4.load_inputs(history, quality_mode="causal")
    # Keep MCHL1 contextual and shadow-only; remove the documented HADS sentinel
    # and sentinel-contaminated hourly averages from this optional stream.
    mchl1_removed = 0
    for row in index.get(("MCHL1", "stage"), {}).values():
        cleaned, removed = clean_mchl1_context_row(row)
        row.update(cleaned)
        mchl1_removed += removed

    valid_times = [time for series in index.values() for time, row in series.items()
                   if evidence.valid(row, row.get("unit"))]
    if not valid_times:
        raise ValueError("no valid hourly observations found")
    archive_start = min(valid_times)
    # Forecast follow-up/censoring is determined by observed target stages,
    # never by a future-valid predictor product such as a tide prediction.
    target_times = [time for time, row in index.get(("MAUL1", "stage"), {}).items()
                    if evidence.valid(row, "ft") and row.get("datum") == "gage height"]
    if not target_times:
        raise ValueError("no valid MAUL1 target observations found")
    archive_end = max(target_times) + HOUR
    # Evaluate only the event/control assessment periods plus one preceding
    # decision hour for carry-in state. Features still read their full causal
    # 72-hour history from the archive. This avoids screening unrelated hours.
    needed_issues = set()
    for event in events:
        onset = event.get("_onset")
        if onset is not None:
            left, right = max(archive_start, onset - 73 * HOUR), min(archive_end, onset + 24 * HOUR)
            time = left
            while time <= right:
                needed_issues.add(time)
                time += HOUR
    for control in controls:
        left = max(archive_start, stamp(control["start_utc"]) - HOUR)
        right = min(archive_end, stamp(control["end_utc"]))
        time = left
        while time < right:
            needed_issues.add(time)
            time += HOUR
    issues = sorted(needed_issues)

    calibration = phase4.calibrate(index)
    dynamic_thresholds = expanding_discharge_thresholds(index, issues)
    # Compute each completed-bin metrics bundle once, then apply the frozen
    # primary screen and two predeclared magnitude sensitivities.
    screen_rows = {}
    variant_rows = {factor: {} for factor in SENSITIVITY_FACTORS}
    for issue in issues:
        metrics = evidence.metrics(index, issue)
        base = evidence.DEFAULTS | {"discharge_high_cfs": dynamic_thresholds[issue]["discharge_high_cfs"]}
        for factor in SENSITIVITY_FACTORS:
            thresholds = dict(base)
            for name in ("discharge_rise_cfs", "residual_ft", "residual_rise_ft",
                         "lake_rise_ft", "wind_projection_knots"):
                thresholds[name] *= factor
            assessment = evidence.decide(metrics, issue, thresholds)
            compact = {"flags": assessment["flags"], "coverage": assessment["coverage"],
                       "missing": assessment["missing"],
                       "target_change_native_ft": assessment["metrics"]["target_change_native_ft"]}
            variant_rows[factor][issue] = compact
            if factor == 1.0:
                screen_rows[issue] = compact

    known_events = [event for event in events if event.get("_onset") is not None]
    response_episodes = []
    for signal in SIGNALS:
        for detection in signal_episodes(screen_rows, signal):
            assigned = nearest_upcoming_event(detection, known_events)
            response_episodes.append({"signal": signal, "detection": detection, "event_id": assigned})

    assigned_by_signal_event = defaultdict(list)
    for episode in response_episodes:
        if episode["event_id"]:
            assigned_by_signal_event[(episode["signal"], episode["event_id"])].append(episode["detection"])

    event_rows = []
    signal_stats = {signal: {"confirmed_before": 0, "confirmed_during": 0, "confirmed_after": 0,
                             "local_pre_onset_candidates": 0,
                             "unique_credited_pre_onset": 0, "leads_h": [], "within_horizon": Counter(),
                             "unknown_fraction": []} for signal in SIGNALS}
    for event in events:
        onset = event.get("_onset")
        if onset is None:
            event_rows.append({"event_id": event["event_id"], "onset_utc": event.get("onset_utc") or None,
                               "onset_known": False, "classification_screen": classifications.get(event["event_id"], "Indeterminate"),
                               "status": "onset_uncertain", "signals": {},
                               "uncertainty": ["Retrospective onset is not precise enough to calculate lead time."]})
            continue
        start, end = onset - HOUR * 72, onset + HOUR * 24
        pre_issues = [t for t in issues if start <= t < onset]
        signals = {}
        for signal in SIGNALS:
            first_local = first_confirmation(screen_rows, signal, start, end, issues)
            credited = sorted(t for t in assigned_by_signal_event[(signal, event["event_id"])] if start <= t <= end)
            first_credited = min(credited) if credited else None
            lead = ((onset - first_local).total_seconds() / 3600) if first_local else None
            status = "not_detected" if first_local is None else ("before" if lead > 0 else "during" if lead == 0 else "after")
            credited_lead = ((onset - first_credited).total_seconds() / 3600) if first_credited else None
            left_censored = bool(first_local == start and start - HOUR in screen_rows and
                                 screen_rows[start - HOUR]["flags"].get(signal) == "present")
            unknown_fraction = _screen_summary(pre_issues, screen_rows, signal)["unknown_hours"] / max(1, len(pre_issues))
            signals[signal] = {"first_screen_confirmation_utc": iso(first_local) if first_local else None,
                               "first_local_confirmation_utc": iso(first_local) if first_local else None,
                               "first_unique_event_credit_utc": iso(first_credited) if first_credited else None,
                               "unique_event_credit_lead_hours": credited_lead,
                               "unique_event_credit": first_credited is not None,
                               "lookback_left_censored": left_censored,
                               "timing": status, "retrospective_lead_hours": lead,
                               "pre_onset_missing_fraction": round(unknown_fraction, 4),
                               "pre_onset_screen_coverage": _screen_summary(pre_issues, screen_rows, signal)}
            stats = signal_stats[signal]
            if first_local:
                stats[f"confirmed_{status}"] += 1
                if lead > 0:
                    stats["local_pre_onset_candidates"] += 1
            if first_credited is not None:
                if credited_lead > 0:
                    stats["unique_credited_pre_onset"] += 1
                    stats["leads_h"].append(credited_lead)
                    for horizon in (6, 12, 24):
                        if credited_lead <= horizon:
                            stats["within_horizon"][str(horizon)] += 1
            stats["unknown_fraction"].append(unknown_fraction)
        primary_candidates = [signals[name] for name in PATHWAYS if signals[name]["timing"] == "before"]
        first_any = min(primary_candidates, key=lambda row: row["retrospective_lead_hours"], default=None)
        event_rows.append({"event_id": event["event_id"], "onset_utc": iso(onset), "onset_known": True,
                           "rise_native_ft": _number(event.get("rise_native_gage_height")),
                           "peak_utc": event.get("peak_utc"), "uncertainty_flags": event.get("uncertainty_flags"),
                           "classification_screen": classifications.get(event["event_id"], "Indeterminate"),
                           "classification_is_causal_truth": False,
                           "first_confirmed_pathway": ("river" if first_any is signals.get("river") else "coastal") if first_any else None,
                           "assessment_window_utc": {"start": iso(start), "end_exclusive": iso(end + HOUR)},
                           "event_overlap_assignment": "Each screen-present episode is credited to the nearest upcoming known MAUL1 onset within 72 hours; no episode is credited to multiple events.",
                           "signals": signals,
                           "onset_uncertainty_hours": 1,
                           "uncertainty": ["Lead time is based on hourly valid time; source receipt/forecaster availability timestamps are absent.",
                                           "The Phase 4 screens are observational consistency rules, not verified causal labels or forecast alarms."]})

    lead_summary = {}
    for signal, stats in signal_stats.items():
        leads = stats["leads_h"]
        lead_summary[signal] = {"events_detected_before": stats["unique_credited_pre_onset"],
                                "local_pre_onset_candidates_before_unique_assignment": stats["local_pre_onset_candidates"],
                                "events_detected_during": stats["confirmed_during"],
                                "events_detected_after": stats["confirmed_after"],
                                "events_without_screen": sum(1 for row in event_rows if row.get("onset_known") and row["signals"].get(signal, {}).get("timing") == "not_detected"),
                                "uniquely_credited_pre_onset_events": stats["unique_credited_pre_onset"],
                                "pre_onset_lead_hours": {"n": len(leads), "min": min(leads) if leads else None,
                                    "p10": quantile(leads, .1), "median": quantile(leads, .5),
                                    "p90": quantile(leads, .9), "max": max(leads) if leads else None},
                                "pre_onset_events_within_hours": {str(h): stats["within_horizon"][str(h)] for h in (6, 12, 24)},
                                "mean_pre_onset_unknown_fraction": round(statistics.mean(stats["unknown_fraction"]), 4) if stats["unknown_fraction"] else None,
                                "interpretation": "Retrospective valid-time screen timing; not actual operational warning lead."}

    control_rows, control_summary = analyze_controls(controls, screen_rows, response_episodes, events, archive_end)
    propagation = analyze_propagation(event_rows)
    sensitivity = analyze_sensitivity(events, issues, variant_rows)
    cases = representative_cases(event_rows)

    archive_files = sorted((history / "hourly").glob("*.json.gz"))
    input_hashes = {str(path.relative_to(root)): _sha256(path) for path in archive_files}
    for path in (event_path, control_path, class_path):
        if path.exists():
            input_hashes[str(path.relative_to(root))] = _sha256(path)
    source_hashes = {name: _sha256(HERE / name) for name in ("evidence.py", "phase4.py", "phase8_lead_analysis.py")}
    provenance = {"schema": SCHEMA, "mode": "retrospective_valid_time_only_screening",
                  "forecast_eligible": False, "causal_quality_mode": "Phase 4 causal fixed-jump replay; future-dependent monthly QC exclusions are not used",
                  "quality_policy": "MCHL1 sentinel-contaminated rows are excluded using the documented Phase 7 numeric gate; other station values are accepted only by Phase 4 finite/unit/datum/coverage checks.",
                  "primary_screen": "Frozen Phase 4 physical evidence screen. Coastal residual, MDLL1 lake, and NWCL1 wind use complete six-hour current windows. Detection time is the first decision time at which the complete six-hour evidence window can be evaluated; no earlier point in that window is credited.",
                  "threshold_method": "Phase 4 defaults; DENL1 elevated-discharge threshold is an expanding prior calibration-era 90th percentile, as of each issue; fixed magnitude sensitivity factors 0.75, 1.0, 1.25.",
                  "issue_contract": "Evidence at UTC issue time uses only completed hourly bins in [issue-6h, issue) and antecedent windows ending before issue. No future bins or event labels enter a screen.",
                  "lead_interpretation": "Valid-time retrospective lead only. Historical source retrieval/receipt times are unavailable, so these values are not operational lead time.",
                  "event_overlap_rule": "Each detected screen episode is assigned to at most one nearest upcoming known MAUL1 onset within 72 hours; controls and event windows are not treated as independent hourly samples.",
                  "mchl1_removed_hourly_values": mchl1_removed,
                  "catalog_counts": {"response_events": len(events), "known_onset": sum(e.get("_onset") is not None for e in events),
                                     "uncertain_onset": sum(e.get("_onset") is None for e in events), "eligible_selected_controls": len(controls)},
                  "source_hashes_sha256": source_hashes, "input_hashes_sha256": input_hashes,
                  "phase4_calibration": calibration, "assessment_hour_count": len(screen_rows),
                  "archive_first_valid_utc": iso(archive_start), "archive_last_valid_utc": iso(archive_end - HOUR)}

    summary = {"schema": SCHEMA, "study": "Retrospective precursor timing, propagation consistency and selected-control screens",
               "forecast_eligible": False, "catalog": provenance["catalog_counts"],
               "event_level_signal_summary": lead_summary, "selected_control_summary": control_summary,
               "propagation": propagation, "threshold_sensitivity": sensitivity,
               "classification_screen_counts": dict(Counter(row["classification_screen"] for row in event_rows)),
               "classification_screen_counts_known_onset_only": dict(Counter(row["classification_screen"] for row in event_rows if row.get("onset_known"))),
               "representative_cases": cases,
               "scientific_conclusion": "These calculations measure when archived station evidence met frozen observational screens relative to retrospective MAUL1 event onsets. They do not establish causal attribution, forecasts, actual receipt-time lead, or operational false-alarm rates.",
               "limitations": ["Response events are selected from a retrospective native-stage catalog; 10 have uncertain onset.",
                               "Controls are preselected 7-day windows, not randomly sampled background exposure; control alarm fractions are descriptive only.",
                               "Hourly valid timestamps do not establish when data reached forecasters; true operational lead can be shorter or absent.",
                               "NWCL1, MDLL1, DENL1 and MCHL1 do not share one verified vertical datum; analysis uses within-station changes and NWCL1 same-datum residual only.",
                               "Phase 4 categories are evidence-screen classifications, not independent causal labels; downstream rainfall and local tributary forcing are not observed.",
                               "MCHL1 is optional cleaned context only; no MCHL1 predictor is activated and no cross-station stage comparison is made.",
                               "Retrospective onset time has approximately hourly resolution; event thresholds and evidence screens have their own selection sensitivity."]}
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "event-leads.json", {"schema": SCHEMA, "provenance": provenance, "events": event_rows})
    _write_json(output / "control-alarms.json", {"schema": SCHEMA, "provenance": provenance, "controls": control_rows})
    _write_json(output / "propagation.json", {"schema": SCHEMA, "provenance": provenance, **propagation})
    _write_json(output / "case-studies.json", {"schema": SCHEMA, "cases": cases})
    _write_json(output / "summary.json", summary)
    _write_json(output / "provenance.json", provenance)
    return summary


def analyze_controls(controls, rows, episodes, events, archive_end):
    controls_out = []
    episode_by_signal = defaultdict(list)
    for item in episodes:
        episode_by_signal[item["signal"]].append(item["detection"])
    summary = {signal: {"selected_control_count": len(controls), "controls_with_signal": 0,
                        "screen_present_control_hours": 0, "signal_episode_count": 0,
                        "horizons": {str(h): Counter() for h in (6, 12, 24)}} for signal in SIGNALS}
    for control in controls:
        start, end = stamp(control["start_utc"]), stamp(control["end_utc"])
        window_issues = [t for t in rows if start <= t < end]
        item = {"control_id": control["control_candidate_id"], "start_utc": iso(start), "end_utc_exclusive": iso(end),
                "source_categories": json.loads(control.get("categories", "[]")), "signals": {}}
        for signal in SIGNALS:
            present = [t for t in window_issues if rows[t]["flags"].get(signal) == "present"]
            unknown = sum(rows[t]["flags"].get(signal, "unknown") == "unknown" for t in window_issues)
            starts = [t for t in episode_by_signal[signal] if start <= t < end]
            active_at_start = bool(window_issues and rows[window_issues[0]]["flags"].get(signal) == "present")
            trigger_time = min(starts) if starts else (window_issues[0] if active_at_start and window_issues else None)
            follow = {}
            if trigger_time:
                for horizon in (6, 12, 24):
                    state = forward_response_status(trigger_time, horizon, events, archive_end)
                    follow[str(horizon)] = state
                    summary[signal]["horizons"][str(horizon)][state] += 1
            item["signals"][signal] = {"screen_present_hours": len(present), "unknown_hours": unknown,
                                       "eligible_hours": len(window_issues) - unknown,
                                       "present_in_window": bool(present), "active_at_window_start": active_at_start,
                                       "signal_episode_starts_in_window": [iso(t) for t in starts],
                                       "first_trigger_utc": iso(trigger_time) if trigger_time else None,
                                       "forward_catalog_response_status": follow,
                                       "caveat": "Selected control windows are not an unbiased operational false-alarm sample."}
            summary[signal]["screen_present_control_hours"] += len(present)
            summary[signal]["signal_episode_count"] += len(starts)
            summary[signal]["controls_with_signal"] += bool(present)
        controls_out.append(item)
    for signal in SIGNALS:
        for horizon, counts in summary[signal]["horizons"].items():
            summary[signal]["horizons"][horizon] = dict(counts)
    return controls_out, summary


def analyze_propagation(event_rows):
    pairs = (("residual", "lake"), ("lake", "pass_context"), ("pass_context", "maul1_onset"),
             ("residual", "maul1_onset"), ("lake", "maul1_onset"), ("wind", "maul1_onset"))
    pair_stats = {f"{a}_to_{b}": [] for a, b in pairs}
    event_sequences = []
    for event in event_rows:
        if not event.get("onset_known"):
            continue
        onset = stamp(event["onset_utc"])
        times = {name: (stamp(event["signals"][name]["first_unique_event_credit_utc"])
                        if event["signals"].get(name, {}).get("first_unique_event_credit_utc") else None)
                 for name in SIGNALS}
        times["maul1_onset"] = onset
        order = [name for name in ("residual", "lake", "pass_context", "maul1_onset") if times.get(name)]
        ordered_times = [times[name] for name in order]
        sequence = len(order) >= 3 and all(left < right for left, right in zip(ordered_times, ordered_times[1:]))
        event_sequences.append({"event_id": event["event_id"], "ordered_detected_stations": order,
                                "strictly_in_order": sequence,
                                "interpretation": "Screen timing order only; not proof of water propagation."})
        for a, b in pairs:
            left = onset if a == "maul1_onset" else times.get(a)
            right = onset if b == "maul1_onset" else times.get(b)
            if left and right:
                pair_stats[f"{a}_to_{b}"].append((right - left).total_seconds() / 3600)
    output = {"pairwise_screen_lags_hours": {}, "candidate_strict_sequences": event_sequences,
              "positive_lag_sensitivity": {str(window): {} for window in LAG_WINDOWS},
              "causal_claim": False}
    for name, lags in pair_stats.items():
        positive = [lag for lag in lags if lag > 0]
        output["pairwise_screen_lags_hours"][name] = {"paired_events": len(lags), "positive_lag_events": len(positive),
            "median_positive_lag_h": quantile(positive, .5), "p10_positive_lag_h": quantile(positive, .1),
            "p90_positive_lag_h": quantile(positive, .9), "minimum_lag_h": min(positive) if positive else None,
            "maximum_lag_h": max(positive) if positive else None,
            "same_or_reverse_order_events": sum(lag <= 0 for lag in lags)}
        for window in LAG_WINDOWS:
            output["positive_lag_sensitivity"][str(window)][name] = sum(0 < lag <= window for lag in lags)
    output["strict_order_event_count"] = sum(row["strictly_in_order"] for row in event_sequences)
    output["evaluated_known_onset_events"] = len(event_sequences)
    output["interpretation"] = "Lags compare first confirmed six-hour evidence-screen times, not raw physical wave arrival. Same-hour/rolling windows blur onset; coincidence or order alone is not propagation evidence. MCHL1 is frequently missing/quality-limited and never a model input."
    return output


def analyze_sensitivity(events, issues, variant_rows):
    result = {}
    known = [event for event in events if event.get("_onset") is not None]
    ordered_issues = sorted(issues)
    for factor, rows in variant_rows.items():
        family = {}
        for signal in PATHWAYS:
            credited = defaultdict(list)
            for detection in signal_episodes(rows, signal):
                event_id = nearest_upcoming_event(detection, known)
                if event_id:
                    credited[event_id].append(detection)
            leads = []
            for event in known:
                candidates = [time for time in credited[event["event_id"]]
                              if time < event["_onset"] and event["_onset"] - time <= 72 * HOUR]
                if candidates:
                    leads.append((event["_onset"] - min(candidates)).total_seconds() / 3600)
            n_pre = len(leads)
            family[signal] = {"events_with_pre_onset_screen": n_pre, "lead_n": len(leads),
                              "median_lead_h": quantile(leads, .5), "p10_lead_h": quantile(leads, .1),
                              "p90_lead_h": quantile(leads, .9)}
        result[str(factor)] = family
    result["method"] = "Exploratory threshold sensitivity on the same historical event catalog; no factor is selected or treated as independent validation. Factors scale fixed physical magnitude thresholds; the expanding discharge high-flow quantile is unchanged."
    return result


def representative_cases(event_rows):
    cases = []
    def eligible(row, signal):
        result = row["signals"].get(signal, {})
        lead = result.get("unique_event_credit_lead_hours")
        return (result.get("unique_event_credit") is True and
                not result.get("lookback_left_censored") and
                isinstance(lead, (int, float)) and 0 < lead < 72)

    for signal in ("coastal", "river"):
        candidates = [row for row in event_rows if row.get("onset_known") and
                      eligible(row, signal)]
        if candidates:
            selected = max(candidates, key=lambda row: row["signals"][signal]["unique_event_credit_lead_hours"])
            cases.append({"selection": f"largest observed {signal} screen lead", "event_id": selected["event_id"],
                          "onset_utc": selected["onset_utc"], "phase4_screen_category": selected["classification_screen"],
                          "credited_lead_hours": selected["signals"][signal]["unique_event_credit_lead_hours"],
                          "signals": selected["signals"], "interpretation": "Outcome-selected illustration with unique positive episode credit; not independent validation or a verified causal event."})
    both = [row for row in event_rows if row.get("onset_known") and
            eligible(row, "river") and eligible(row, "coastal")]
    if both:
        selected = both[0]
        cases.append({"selection": "first event with both river and coastal screens before onset",
                      "event_id": selected["event_id"], "onset_utc": selected["onset_utc"],
                      "phase4_screen_category": selected["classification_screen"], "signals": selected["signals"],
                      "interpretation": "Coincident pathway consistency screens do not establish compound causality or percentage contribution."})
    return cases


def _number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _sha256(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=HERE.parent)
    parser.add_argument("--output", type=pathlib.Path, default=HERE.parent / "work/phase8")
    args = parser.parse_args(argv)
    result = build_analysis(args.root, args.output)
    print(json.dumps({"output": str(args.output), "catalog": result["catalog"],
                      "signals": result["event_level_signal_summary"],
                      "controls": result["selected_control_summary"]}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
