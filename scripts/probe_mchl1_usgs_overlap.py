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
import urllib.parse
import urllib.request

UTC=dt.timezone.utc
USGS="https://waterservices.usgs.gov/nwis/iv/"
HADS="https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py"

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
            if math.isfinite(v): out[timestamp(row["utc_valid"])]=v
        except (TypeError,ValueError):
            continue
    return out

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

def compare(hads,usgs):
    stamps=sorted(hads.keys()&usgs.keys())
    offsets=[hads[t]-usgs[t] for t in stamps]
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
      "native_stage_difference_range_ft":[round(min(offsets),4),round(max(offsets),4)] if offsets else None,
      "stage_changes":changes}

def request(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"MAUL1-Coastal-Influence-research/1.0"}),timeout=50) as response:
        return response.read()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start",default="2026-09-01")
    parser.add_argument("--end",default="2026-09-05")
    args=parser.parse_args()
    start=dt.date.fromisoformat(args.start);end=dt.date.fromisoformat(args.end)
    if not 4<= (end-start).days <=8:
        parser.error("require 4–8 days of historical coverage (end exclusive)")
    hurl=HADS+"?"+urllib.parse.urlencode({"stations":"MCHL1","sts":start.isoformat()+"T00:00Z","ets":end.isoformat()+"T00:00Z","what":"txt","delim":"comma"})
    uurl=USGS+"?"+urllib.parse.urlencode({"format":"json","sites":"073802302","parameterCd":"00065","startDT":start.isoformat(),"endDT":end.isoformat()})
    report={"schema":"phase6.mchl1-usgs-overlap-probe.v1","forecast_eligible":False,
            "window_start_utc":start.isoformat(),"window_end_utc_exclusive":end.isoformat(),
            "sources":{"MCHL1":{"url":hurl},"USGS-073802302":{"url":uurl}},
            "note":"Compare two separate native gage-height series. Offset/correlation cannot establish common datum, sensor identity, or QC approval."}
    data={}
    for name,url,parse in (("MCHL1",hurl,hads_rows),("USGS-073802302",uurl,usgs_rows)):
        try:
            body=request(url)
            report["sources"][name]["sha256"]=hashlib.sha256(body).hexdigest()
            data[name]=parse(body)
            report["sources"][name]["valid_readings"]=len(data[name])
            report["sources"][name]["status"]="retrieved"
        except Exception as e:
            report["sources"][name]["status"]="error"
            report["sources"][name]["error"]=str(e)
    if len(data)==2:
        report["comparison"]=compare(data["MCHL1"],data["USGS-073802302"])
    report["retrieved_utc"]=dt.datetime.now(UTC).isoformat()
    print(json.dumps(report,indent=2))
    if len(data)!=2:
        raise SystemExit(1)

if __name__=="__main__":
    main()
