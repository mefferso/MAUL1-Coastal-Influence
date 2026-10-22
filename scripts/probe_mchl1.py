"""Read-only MCHL1 candidate source probe. Never writes forecasts or authorizes data use."""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import io
import json
import urllib.parse
import urllib.request

UTC = dt.timezone.utc
ENDPOINT = "https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py"
STATION = "MCHL1"
IDENTITY = {"station": STATION, "dcp_id": "CE678A12",
            "description": "PASS MANCHAC NEAR HWY 51", "hads_parameter": "HG"}


def request_url(start, end):
    if not (start.tzinfo and end.tzinfo and end > start):
        raise ValueError("UTC-aware start and end required")
    args = {"stations": STATION, "sts": start.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ"),
            "ets": end.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ"),
            "what": "txt", "delim": "comma"}
    return ENDPOINT + "?" + urllib.parse.urlencode(args)


def assess_response(body):
    """Conservative metadata probe; intentionally never accepts observations for model use."""
    text = body.decode("utf-8-sig", errors="replace")
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    if not lines:
        return {"status": "empty", "approved_for_forecasting": False, "rows": 0}
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    fields = reader.fieldnames or []
    rows = list(reader)
    station_keys = [key for key in fields if key and key.lower() in ("station", "stid", "nwsli")]
    stage_keys = [key for key in fields if key and key.upper().startswith("HG")]
    time_keys = [key for key in fields if key and any(tag in key.lower() for tag in ("utc", "valid", "time"))]
    station_values = sorted({row.get(key, "").strip() for row in rows for key in station_keys if row.get(key)})
    # Describe observation freshness without promoting any record to forecast input.
    times = []
    numeric = 0
    invalid = 0
    for row in rows:
        try:
            if len(time_keys) != 1:
                raise ValueError("ambiguous time field")
            value = row.get(time_keys[0], "").strip()
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                if time_keys[0].lower() != "utc_valid":
                    raise ValueError("naive observation time without explicit UTC column")
                parsed = parsed.replace(tzinfo=UTC)
            times.append(parsed.astimezone(UTC))
        except (ValueError, TypeError, AttributeError):
            invalid += 1
        for key in stage_keys:
            try:
                import math
                if math.isfinite(float(row.get(key, ""))):
                    numeric += 1
            except (ValueError, TypeError):
                pass
    times.sort()
    first = times[0].isoformat().replace("+00:00", "Z") if times else None
    last = times[-1].isoformat().replace("+00:00", "Z") if times else None
    spacing = [(right-left).total_seconds()/60 for left,right in zip(times,times[1:])]
    return {"status": "candidate_needs_manual_validation", "approved_for_forecasting": False,
            "fields": fields, "rows": len(rows), "station_values": station_values,
            "stage_fields": stage_keys, "time_fields": time_keys,
            "station_id_matches": bool(station_values) and station_values == [STATION],
            "has_stage_column": bool(stage_keys), "has_time_column": bool(time_keys),
            "earliest_valid_utc": first, "latest_valid_utc": last,
            "valid_timestamp_count": len(times), "invalid_timestamp_count": invalid,
            "finite_stage_cell_count": numeric,
            "max_observed_gap_minutes": max(spacing) if spacing else None,
            "observation_span_hours": round((times[-1]-times[0]).total_seconds()/3600, 3) if len(times)>1 else 0,
            "note": "Source latency and native datum not validated; no forecasting approval"}



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=int, default=48)
    args = parser.parse_args()
    if not 1 <= args.hours <= 96:
        parser.error("hours must be between 1 and 96")
    end = dt.datetime.now(UTC).replace(second=0, microsecond=0)
    start = end - dt.timedelta(hours=args.hours)
    url = request_url(start, end)
    request = urllib.request.Request(url, headers={"User-Agent": "MAUL1-Coastal-Influence-research/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            report = assess_response(response.read())
            report["http_status"] = response.status
    except Exception as exc:
        report = {"status": "fetch_error", "approved_for_forecasting": False,
                  "error": str(exc)}
    if report.get("latest_valid_utc"):
        latest=dt.datetime.fromisoformat(report["latest_valid_utc"].replace("Z","+00:00"))
        report["latest_observation_age_minutes_at_probe"]=round((dt.datetime.now(UTC)-latest).total_seconds()/60,2)
    report.update({"station_identity": IDENTITY, "url": url,
                   "retrieved_utc": dt.datetime.now(UTC).isoformat()})
    print(json.dumps(report, indent=2))
    if report["status"] == "fetch_error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
