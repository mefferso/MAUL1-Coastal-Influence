"""Recent, provenance-preserving source acquisition for prospective cycles."""
from __future__ import annotations
import datetime as dt, hashlib, json, math, urllib.parse, urllib.request
from build import parse_usgs, parse_coops, parse_wind, parse_hads

UTC=dt.timezone.utc
def _get(url):
    request=urllib.request.Request(url,headers={"User-Agent":"MAUL1-research/1.0 (public research)"})
    with urllib.request.urlopen(request,timeout=30) as response:
        raw=response.read(); return raw,response.headers.get("Date")

def _query(url, params): return url+"?"+urllib.parse.urlencode(params)
def _obs(row, retrieved, request_url, raw_hash):
    return {"station":row["station"],"source":row["source"],"parameter":row["variable"],"value":row["value"],
        "units":row["unit"],"datum":row["datum"],"valid_time_utc":row["time"],"retrieved_utc":retrieved,
        "original_source_time":row["time"],"qc":row.get("quality"),"provenance_url":request_url,"response_sha256":raw_hash}

def fetch_snapshot(now_utc, fetcher=_get):
    now=dt.datetime.fromisoformat(now_utc.replace("Z","+00:00")) if isinstance(now_utc,str) else now_utc
    now=now.astimezone(UTC); retrieved=now.replace(microsecond=0).isoformat().replace("+00:00","Z")
    specs=[("MAUL1","07380215","00065,63160"),("DENL1","07378500","00060,00065"),("MDLL1","301200090072400","00065")]
    sources=[]; observations=[]
    for station,site,params in specs:
        url=_query("https://waterservices.usgs.gov/nwis/iv/",{"format":"json","sites":site,"parameterCd":params,"period":"P3D","siteStatus":"all"})
        try:
            raw,date=fetcher(url); retrieved=dt.datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"); payload=json.loads(raw); rows=parse_usgs(payload,station); digest=hashlib.sha256(raw).hexdigest()
            observations += [_obs(r,retrieved,url,digest) for r in rows]
            sources.append({"station":station,"status":"retrieved" if rows else "empty","retrieved_utc":retrieved,"url":url,"response_sha256":digest,"server_date":date})
        except Exception as exc: sources.append({"station":station,"status":"error","retrieved_utc":retrieved,"url":url,"error":str(exc)})
    for product,datum in (("water_level","MLLW"),("predictions","MLLW"),("wind","")):
        base="https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        params={"station":"8761927","begin_date":(now-dt.timedelta(days=3)).strftime("%Y%m%d"),"end_date":now.strftime("%Y%m%d"),"time_zone":"gmt","units":"english","format":"json","application":"MAUL1-research"}
        if product=="wind": params.update({"product":"wind"})
        else: params.update({"product":"water_level" if product=="water_level" else "predictions","datum":datum,"interval":"h"} if product=="water_level" else {"product":"predictions","datum":datum,"interval":"h"})
        url=_query(base,params)
        try:
            raw,date=fetcher(url); retrieved=dt.datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"); payload=json.loads(raw); digest=hashlib.sha256(raw).hexdigest()
            rows=parse_wind(payload) if product=="wind" else parse_coops(payload,product,datum)
            observations += [_obs(r,retrieved,url,digest) for r in rows]
            sources.append({"station":"NWCL1","product":product,"status":"retrieved" if rows else "empty","retrieved_utc":retrieved,"url":url,"response_sha256":digest,"server_date":date})
        except Exception as exc: sources.append({"station":"NWCL1","product":product,"status":"error","retrieved_utc":retrieved,"url":url,"error":str(exc)})
    # HADS archive is not treated as a live feed. Its live availability is explicitly unknown.
    sources.append({"station":"MCHL1","status":"unavailable","source":"NWS HADS live endpoint not established","retrieved_utc":retrieved})
    acquired=dt.datetime.now(UTC)
    for observation in observations:
        valid=dt.datetime.fromisoformat(observation["valid_time_utc"].replace("Z","+00:00"))
        received=dt.datetime.fromisoformat(observation["retrieved_utc"].replace("Z","+00:00"))
        observation["age_seconds_at_retrieval"]=(received-valid).total_seconds()
        observation["eligible_completed_hour"]=(valid.replace(minute=0,second=0,microsecond=0)+dt.timedelta(hours=1)<=received.replace(minute=0,second=0,microsecond=0))
    return {"retrieved_utc":retrieved,"observations":observations,"sources":sources,
        "station_roles":{"MAUL1":"target; 00065 native gage height; 63160 NAVD88 separate","DENL1":"upstream river","NWCL1":"coastal level/wind","MDLL1":"independent lake response","MCHL1":"supporting HADS propagation indicator"},
        "mchl1_substitution":"prohibited; USACE 85420 excluded"}

def live_smoke():
    snapshot=fetch_snapshot(dt.datetime.now(UTC))
    print(json.dumps({"retrieved_utc":snapshot["retrieved_utc"],"sources":snapshot["sources"],"observation_count":len(snapshot["observations"])},indent=2))
    return any(x["status"]=="retrieved" for x in snapshot["sources"])
