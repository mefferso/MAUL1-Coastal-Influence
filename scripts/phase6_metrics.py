"""Prospective summary metrics, including predefined rise thresholds."""
import math
THRESHOLDS = (.25, .50, 1.00)
def compute_metrics(rows):
    valid = [r for r in rows if r.get("forecast_change_ft") is not None and r.get("observed_change_ft") is not None]
    out = {"n": len(valid)}
    errors = [float(r["forecast_change_ft"])-float(r["observed_change_ft"]) for r in valid]
    rising=[i for i,r in enumerate(valid) if float(r["observed_change_ft"])>0]
    rapid=[i for i,r in enumerate(valid) if float(r["observed_change_ft"])>=1.0]
    quiet=[i for i,r in enumerate(valid) if float(r["observed_change_ft"])<=0]
    under=[-errors[i] for i in rising if errors[i]<0]
    out.update({"mae_ft": sum(abs(x) for x in errors)/len(errors) if errors else None,
                "rmse_ft": math.sqrt(sum(x*x for x in errors)/len(errors)) if errors else None,
                "bias_ft": sum(errors)/len(errors) if errors else None,
                "underforecast_frequency_during_rises":len(under)/len(rising) if rising else None,
                "mean_underforecast_magnitude_during_rises_ft":sum(under)/len(under) if under else None,
                "underforecast_p90_ft": sorted(under)[min(len(under)-1,int(.90*(len(under)-1)))] if under else None,
                "underforecast_max_ft":max(under) if under else None,
                "rapid_rise_n":len(rapid),"rapid_rise_mae_ft":sum(abs(errors[i]) for i in rapid)/len(rapid) if rapid else None,
                "quiet_or_falling_n":len(quiet),"quiet_or_falling_mae_ft":sum(abs(errors[i]) for i in quiet)/len(quiet) if quiet else None,
                "absolute_error_p90_ft":sorted(abs(x) for x in errors)[min(len(errors)-1,int(.90*(len(errors)-1)))] if errors else None,
                "absolute_error_p99_ft":sorted(abs(x) for x in errors)[min(len(errors)-1,int(.99*(len(errors)-1)))] if errors else None})
    paired=[r for r in valid if r.get("persistence_change_ft") is not None]
    persistence_mae=sum(abs(float(r["persistence_change_ft"])-float(r["observed_change_ft"])) for r in paired)/len(paired) if paired else None
    out["mae_persistence_ft"]=persistence_mae
    out["skill_vs_persistence"]=1-(out["mae_ft"]/persistence_mae) if out["mae_ft"] is not None and persistence_mae else None
    intervals=[r for r in valid if r.get("interval_lower_ft") is not None and r.get("interval_upper_ft") is not None]
    out["intervals"]={"n":len(intervals),"coverage":sum(bool(r.get("interval_covered")) for r in intervals)/len(intervals) if intervals else None,
        "upper_bound_exceedance_frequency":sum(bool(r.get("upper_bound_exceeded")) for r in intervals)/len(intervals) if intervals else None,
        "mean_width_ft":sum(float(r["interval_upper_ft"])-float(r["interval_lower_ft"]) for r in intervals)/len(intervals) if intervals else None,
        "coverage_during_rises":sum(bool(r.get("interval_covered")) for r in intervals if float(r["observed_change_ft"])>0)/sum(float(r["observed_change_ft"])>0 for r in intervals) if any(float(r["observed_change_ft"])>0 for r in intervals) else None}
    rises = {}
    for threshold in THRESHOLDS:
        hit = miss = false = correct = 0
        for row in valid:
            predicted = float(row["forecast_change_ft"]) >= threshold
            observed = float(row["observed_change_ft"]) >= threshold
            if predicted and observed: hit += 1
            elif observed: miss += 1
            elif predicted: false += 1
            else: correct += 1
        rises[f"{threshold:.2f}"] = {"hits": hit, "misses": miss, "false_alarms": false, "correct_negatives": correct,
            "probability_of_detection": hit/(hit+miss) if hit+miss else None,
            "false_alarm_ratio": false/(hit+false) if hit+false else None,
            "critical_success_index": hit/(hit+miss+false) if hit+miss+false else None,
            "base_event_frequency": (hit+miss)/len(valid) if valid else None}
    events = {r.get("event_id") for r in valid if r.get("event_id")}
    out["rises"] = rises
    out["events"] = {"count": len(events), "status": "computed" if len(events) >= 5 else "insufficient_independent_events"}
    return out

def summarize_qualifying_events(rows, threshold_ft=0.50, separation_hours=24):
    """Group outcome-qualified 24-hour rise windows; descriptive, not onset detection.

    Valid targets with >= threshold rise are merged when their target times are
    no more than 24 hours apart. Lead times refer to the first qualifying
    verification *target*, never to an independently observed threshold crossing.
    """
    import datetime as dt

    def utc(value):
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)

    eligible = sorted(
        (row for row in rows
         if row.get("observed_change_ft") is not None
         and row.get("valid_time_utc")
         and row.get("actual_issue_time_utc")),
        key=lambda row: utc(row["valid_time_utc"]),
    )
    qualifying = [row for row in eligible if float(row["observed_change_ft"]) >= threshold_ft]
    groups = []
    for row in qualifying:
        valid = utc(row["valid_time_utc"])
        if not groups or (valid - groups[-1][-1][0]).total_seconds() > separation_hours * 3600:
            groups.append([])
        groups[-1].append((valid, row))
    events = []
    for group in groups:
        first_target = group[0][0]
        # An alert must have been issued before the first qualifying target.
        hits = [row for _, row in group
                if row.get("forecast_change_ft") is not None
                and float(row["forecast_change_ft"]) >= threshold_ft
                and utc(row["actual_issue_time_utc"]) < first_target]
        first_issuance = min((utc(row["actual_issue_time_utc"]) for row in hits), default=None)
        events.append({
            "first_qualifying_target_utc": first_target.isoformat().replace("+00:00", "Z"),
            "last_qualifying_target_utc": group[-1][0].isoformat().replace("+00:00", "Z"),
            "qualified_window_count": len(group),
            "detected": bool(hits),
            "lead_to_first_qualifying_target_hours": (
                (first_target-first_issuance).total_seconds()/3600 if first_issuance else None
            ),
        })
    result = {
        "definition": "outcome-defined 24h rises of at least 0.50 ft; targets within 24h grouped",
        "interpretation": "lead relative to first qualifying verification target, NOT observed rise onset",
        "event_count": len(events),
        "status": "computed" if len(events) >= 5 else "insufficient_independent_events",
    }
    if len(events) >= 5:
        result["detected_events"] = sum(item["detected"] for item in events)
        result["missed_events"] = len(events) - result["detected_events"]
        result["events"] = events
    return result
