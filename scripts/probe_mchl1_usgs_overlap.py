"""Read-only, historically anchored MCHL1 vs USGS stage overlap assessment."""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import statistics
import time
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError
import urllib.parse
import urllib.request

UTC=dt.timezone.utc
USGS="https://waterservices.usgs.gov/nwis/iv/"
HADS="https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py"
INTER_WINDOW_DELAY_SECONDS=65
HADS_MISSING_SENTINELS={9999999.0}

def usgs_query_date_bounds(start_date,end_exclusive):
    """Pad site-local USGS date bounds, then clip returned observations to UTC."""
    return (start_date-dt.timedelta(days=1)).isoformat(),end_exclusive.isoformat()

def retry_after_seconds(headers,attempt):
    """Return a bounded HADS 429 pause, preferring its Retry-After header."""
    try:
        value=float(headers.get("Retry-After"))
    except (TypeError,ValueError):
        value=60.0*(attempt+1)
    return max(1.0,min(180.0,value))

def timestamp(s):
    d=dt.datetime.fromisoformat(s.strip().replace("Z","+00:00"))
    return (d.replace(tzinfo=UTC) if d.tzinfo is None else d).astimezone(UTC)

def hads_rows(body):
    reader=csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    if not {"station","utc_valid","HGIRGZZ"}.issubset(reader.fieldnames or []):
        raise ValueError("unexpected HADS fields")
    out={}
    for row in reader:
        if row["station"]!="MCHL1":
            raise ValueError("unexpected HADS station")
        try:
            v=float(row["HGIRGZZ"])
            if math.isfinite(v) and v not in HADS_MISSING_SENTINELS:
                out[timestamp(row["utc_valid"])]=v
        except (TypeError,ValueError):
            continue
    return out

def hads_quality_metadata(body,window_start=None,window_end=None):
    reader=csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    fields=reader.fieldnames or []
    qualifier_fields=[name for name in fields if any(token in name.lower() for token in ("qc","qual","quality"))]
    counts={name:Counter() for name in qualifier_fields}
    rows=0;sentinels=0;window_sentinels=0;stamps=[]
    for row in reader:
        rows+=1
        try:
            value=float(row.get("HGIRGZZ", ""))
            if value in HADS_MISSING_SENTINELS:
                sentinels+=1
                stamp=timestamp(row["utc_valid"])
                if window_start is not None and window_end is not None and window_start<=stamp<window_end:
                    window_sentinels+=1
            else:
                stamps.append(timestamp(row["utc_valid"]))
        except (TypeError,ValueError,KeyError):
            pass
        for name in qualifier_fields:
            counts[name][row.get(name) or "<empty>"]+=1
    return {"raw_row_count":rows,"qualifier_fields":qualifier_fields,
            "qualifier_value_counts":{name:dict(sorted(count.items())) for name,count in counts.items()},
            "missing_sentinel_rows":sentinels,
            "missing_sentinel_rows_in_window":window_sentinels if window_start is not None else None,
            "duplicate_valid_time_rows":len(stamps)-len(set(stamps))}

def usgs_rows(body):
    doc=json.loads(body)
    series=[s for s in doc["value"]["timeSeries"]
            if s["sourceInfo"]["siteCode"][0]["value"]=="073802302"
            and s["variable"]["variableCode"][0]["value"]=="00065"]
    if len(series)!=1: raise ValueError("expected one USGS 073802302 / 00065 time series")
    out={}
    for group in series[0]["values"]:
        for row in group["value"]:
            try:
                v=float(row["value"])
                if math.isfinite(v): out[timestamp(row["dateTime"])]=v
            except (TypeError,ValueError):
                pass
    return out

def usgs_quality_metadata(body):
    doc=json.loads(body)
    counts=Counter();rows=0
    for series in doc["value"]["timeSeries"]:
        if series["sourceInfo"]["siteCode"][0]["value"]!="073802302" or series["variable"]["variableCode"][0]["value"]!="00065":
            continue
        for group in series.get("values",[]):
            for row in group.get("value",[]):
                rows+=1
                qualifiers=row.get("qualifiers") or ["<none reported>"]
                for qualifier in qualifiers: counts[str(qualifier)]+=1
    return {"raw_row_count":rows,"qualifier_value_counts":dict(sorted(counts.items()))}

def reporting_intervals(series,window_start=None,window_end=None):
    stamps=sorted(series)
    intervals=[(right-left).total_seconds()/60 for left,right in zip(stamps,stamps[1:])]
    changes=[(abs(series[right]-series[left]),(right-left).total_seconds()/60)
             for left,right in zip(stamps,stamps[1:])]
    counts=Counter(intervals)
    most_common=counts.most_common()
    dominant=most_common[0][0] if most_common and (len(most_common)==1 or most_common[0][1]>most_common[1][1]) else None
    expected=(round((stamps[-1]-stamps[0]).total_seconds()/60/dominant)+1) if dominant and len(stamps)>1 else None
    result={"reading_count":len(stamps),
      "first_valid_utc":stamps[0].isoformat() if stamps else None,
      "last_valid_utc":stamps[-1].isoformat() if stamps else None,
      "median_interval_minutes":statistics.median(intervals) if intervals else None,
      "dominant_interval_minutes":dominant,
      "interval_distribution_minutes":{str(k):v for k,v in sorted(counts.items())},
      "largest_gap_minutes":max(intervals) if intervals else None,
      "largest_adjacent_stage_change_ft":round(max((change for change,_ in changes),default=0),4) if changes else None,
      "interval_at_largest_adjacent_change_minutes":next((gap for change,gap in changes if change==max((x for x,_ in changes),default=None)),None) if changes else None,
      "estimated_missing_between_endpoints":max(0,expected-len(stamps)) if expected is not None else None}
    if window_start is not None and window_end is not None and dominant is not None:
        expected_window=math.ceil((window_end-window_start).total_seconds()/60/dominant)
        observed_window=sum(window_start<=stamp<window_end for stamp in stamps)
        result.update({"expected_window_readings":expected_window,
            "observed_window_readings":observed_window,
            "missing_window_readings":max(0,expected_window-observed_window),
            "window_coverage_percent":round(100*observed_window/expected_window,4) if expected_window else None})
    return result

def compare(hads,usgs,window_start=None,window_end=None):
    stamps=sorted(hads.keys()&usgs.keys())
    offsets=[hads[t]-usgs[t] for t in stamps]
    midpoint=len(offsets)//2
    half_shift=(statistics.median(offsets[midpoint:])-statistics.median(offsets[:midpoint])) if midpoint and len(offsets)>midpoint else None
    changes={}
    for hours in (6,24,72):
        d=dt.timedelta(hours=hours)
        pairs=[(hads[t]-hads[t-d],usgs[t]-usgs[t-d])
               for t in stamps if t-d in hads and t-d in usgs]
        diffs=[a-b for a,b in pairs]
        changes[str(hours)+"h"]={"matched_changes":len(pairs),
          "median_change_difference_ft":round(statistics.median(diffs),4) if diffs else None,
          "mean_absolute_change_difference_ft":round(statistics.mean(map(abs,diffs)),4) if diffs else None}
    return {"matched_exact_valid_times":len(stamps),
      "first_matched_utc":stamps[0].isoformat() if stamps else None,
      "last_matched_utc":stamps[-1].isoformat() if stamps else None,
      "median_native_stage_difference_ft":round(statistics.median(offsets),4) if offsets else None,
      "mean_native_stage_difference_ft":round(statistics.mean(offsets),4) if offsets else None,
      "native_stage_difference_range_ft":[round(min(offsets),4),round(max(offsets),4)] if offsets else None,
      "offset_half_window_shift_ft":round(half_shift,4) if half_shift is not None else None,
      "source_reporting":{"MCHL1":reporting_intervals(hads,window_start,window_end),
                          "USGS-073802302":reporting_intervals(usgs,window_start,window_end)},
      "stage_changes":changes}

def request(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"MAUL1-Coastal-Influence-research/1.0"}),timeout=50) as response:
                return response.read()
        except HTTPError as error:
            if error.code!=429 or attempt==2:
                raise
            time.sleep(retry_after_seconds(error.headers,attempt))
    raise RuntimeError("request retry loop exited unexpectedly")

def run_window(start_text,end_text,raw_dir=None,raw_input_dir=None):
    start=dt.date.fromisoformat(start_text);end=dt.date.fromisoformat(end_text)
    if not 4<= (end-start).days <=8:
        raise ValueError("require 4–8 days of historical coverage (end exclusive)")
    hurl=HADS+"?"+urllib.parse.urlencode({"stations":"MCHL1","sts":start.isoformat()+"T00:00Z","ets":end.isoformat()+"T00:00Z","what":"txt","delim":"comma"})
    usgs_start,usgs_end=usgs_query_date_bounds(start,end)
    uurl=USGS+"?"+urllib.parse.urlencode({"format":"json","sites":"073802302","parameterCd":"00065","startDT":usgs_start,"endDT":usgs_end})
    report={"schema":"phase6.mchl1-usgs-overlap-probe.v1","forecast_eligible":False,
            "window_start_utc":start.isoformat(),"window_end_utc_exclusive":end.isoformat(),
            "sources":{"MCHL1":{"url":hurl},"USGS-073802302":{"url":uurl}},
            "note":"Compare two separate native gage-height series. Offset/correlation cannot establish common datum, sensor identity, or QC approval."}
    data={}
    for name,url,parse,quality in (("MCHL1",hurl,hads_rows,hads_quality_metadata),
                                   ("USGS-073802302",uurl,usgs_rows,usgs_quality_metadata)):
        try:
            suffix="mchl1.csv" if name=="MCHL1" else "usgs_073802302.json"
            raw_name=f"{start.isoformat()}_{end.isoformat()}_{suffix}"
            body=(Path(raw_input_dir)/raw_name).read_bytes() if raw_input_dir else request(url)
            report["sources"][name]["sha256"]=hashlib.sha256(body).hexdigest()
            if raw_dir:
                raw_path=Path(raw_dir)/f"{start.isoformat()}_{end.isoformat()}_{name.lower().replace('-','_')}.{'csv' if name=='MCHL1' else 'json'}"
                raw_path.parent.mkdir(parents=True,exist_ok=True)
                raw_path.write_bytes(body)
                report["sources"][name]["raw_file"]=str(raw_path)
            start_utc=dt.datetime.combine(start,dt.time.min,UTC)
            end_utc=dt.datetime.combine(end,dt.time.min,UTC)
            parsed=parse(body)
            data[name]={stamp:value for stamp,value in parsed.items() if start_utc<=stamp<end_utc}
            report["sources"][name]["raw_query_valid_readings"]=len(parsed)
            report["sources"][name]["valid_readings"]=len(data[name])
            report["sources"][name]["quality_metadata"]=(
                quality(body,dt.datetime.combine(start,dt.time.min,UTC),dt.datetime.combine(end,dt.time.min,UTC))
                if name=="MCHL1" else quality(body)
            )
            report["sources"][name]["status"]="retrieved"
        except Exception as e:
            report["sources"][name]["status"]="error"
            report["sources"][name]["error"]=str(e)
    if len(data)==2:
        report["comparison"]=compare(data["MCHL1"],data["USGS-073802302"],
            dt.datetime.combine(start,dt.time.min,UTC),dt.datetime.combine(end,dt.time.min,UTC))
    report["retrieved_utc"]=dt.datetime.now(UTC).isoformat()
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--window",action="append",nargs=2,metavar=("START","END"),help="append one inclusive-start, exclusive-end UTC window")
    parser.add_argument("--raw-dir",type=Path,help="save exact response bodies for provenance")
    parser.add_argument("--raw-input-dir",type=Path,help="reanalyze archived response bodies without agency requests")
    args=parser.parse_args()
    if args.window and (args.start or args.end): parser.error("use --window or --start/--end, not both")
    windows=args.window or [[args.start or "2026-09-01",args.end or "2026-09-05"]]
    try:
        periods=[]
        for index,(start,end) in enumerate(windows):
            if index and not args.raw_input_dir:
                time.sleep(INTER_WINDOW_DELAY_SECONDS)
            periods.append(run_window(start,end,args.raw_dir,args.raw_input_dir))
    except ValueError as error:
        parser.error(str(error))
    report={"schema":"phase6.mchl1-usgs-overlap-multiwindow.v1","forecast_eligible":False,
            "periods":periods,"period_count":len(periods),
            "note":f"Compare separate native gage-height series. USGS end dates are adjusted to the shared exclusive boundary; {INTER_WINDOW_DELAY_SECONDS}s separates requests to respect HADS throttling. Exact agreement cannot establish common datum, sensor identity, independence, or provider QC approval."}
    print(json.dumps(report,indent=2))
    if any(len(period["sources"])!=2 or any(source.get("status")!="retrieved" for source in period["sources"].values()) for period in periods):
        raise SystemExit(1)

if __name__=="__main__":
    main()
