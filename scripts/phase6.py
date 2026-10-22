"""One prospective issue/verification cycle. Live source errors become audit data."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
import phase6_models, phase6_sources, phase6_forecast, phase6_verify, phase6_metrics
import phase5a, phase5b
UTC=dt.timezone.utc

def quality_is_usable(value):
    """Accept documented provisional/zero-valued quality codes, reject other flags.

    CO-OPS returns comma-separated per-field quality flags (e.g. 0,0,0,0).
    Retain source flags in the archived observations; normalize only for eligibility.
    """
    if value is None: return True
    if isinstance(value, str):
        flags = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple)):
        flags = [str(part).strip() for part in value]
    else:
        return False
    return all(flag in ("", "0", "P", "provisional") for flag in flags)

def latest_snapshot(snapshot, issued):
    obs=snapshot["observations"]
    def latest(station,param,datum=None):
        rows=[o for o in obs if o["station"]==station and o["parameter"]==param and (datum is None or o["datum"]==datum)
              and o["eligible_completed_hour"] and dt.datetime.fromisoformat(o["retrieved_utc"].replace("Z","+00:00"))<=issued
              and dt.datetime.fromisoformat(o["valid_time_utc"].replace("Z","+00:00"))<=issued
              and quality_is_usable(o.get("qc"))]
        return max(rows,key=lambda x:x["valid_time_utc"]) if rows else None
    target=latest("MAUL1","stage","gage height")
    feature={"maul1_stage_native_ft":float(target["value"]) if target else None}; status={}
    status["MAUL1_00065"]={"status":"eligible" if target else "missing_or_stale","observation":target}
    if target:
        age=(issued-dt.datetime.fromisoformat(target["valid_time_utc"].replace("Z","+00:00"))).total_seconds()/3600
        if age>2: status["MAUL1_00065"]["status"]="stale"
        status["MAUL1_00065"]["age_hours"]=age
    for key,station,param,datum in (("NWCL1","NWCL1","water_level","MLLW"),("DENL1","DENL1","discharge","native"),("MDLL1","MDLL1","stage","gage height"),("MCHL1","MCHL1","stage",None)):
        item=latest(station,param,datum)
        status[key]={"status":"eligible" if item else "missing","observation":item,"maximum_age_hours":3}
        if item:
            age=(issued-dt.datetime.fromisoformat(item["valid_time_utc"].replace("Z","+00:00"))).total_seconds()/3600
            status[key]["age_hours"]=age
            if age>3: status[key]["status"]="stale"
    return feature,status

def feature_snapshot(snapshot, issued):
    """Build causal Phase 5 feature rows from captured, completed hourly bins."""
    import collections
    groups=collections.defaultdict(list); predictions={}
    for o in snapshot["observations"]:
        if o["retrieved_utc"]>phase6_forecast.stamp(issued): continue
        if not quality_is_usable(o.get("qc")): continue
        valid=dt.datetime.fromisoformat(o["valid_time_utc"].replace("Z","+00:00"))
        start=valid.replace(minute=0,second=0,microsecond=0)
        if start+dt.timedelta(hours=1)>issued.replace(minute=0,second=0,microsecond=0): continue
        station,var=o["station"],o["parameter"]
        if o["datum"]=="NAVD88" or var=="elevation": continue
        if station=="NWCL1" and var=="water_level": var="water"
        if station=="NWCL1" and var=="predictions": var="prediction"
        if station=="NWCL1" and var not in ("water","prediction","wind_u","wind_v"): continue
        if var=="prediction": predictions[(station,start)]=float(o["value"])
        key=(station,var); groups[(key,start,o["units"],o["datum"])].append(o)
    index={}
    for (key,start,unit,datum),rows in groups.items():
        index.setdefault(key,{})[start]={"value":sum(float(r["value"]) for r in rows)/len(rows),"unit":unit,"datum":datum,
            "coverage":1.0,"missing":False,"retrieved_utc":max(r["retrieved_utc"] for r in rows)}
    for (station,start),_ in predictions.items():
        water=index.get((station,"water"),{}).get(start); prediction=index.get((station,"prediction"),{}).get(start)
        if water and prediction:
            index.setdefault((station,"residual"),{})[start]={**water,"value":water["value"]-prediction["value"],"unit":"ft","datum":"MLLW"}
    grid_issue=issued.replace(minute=0,second=0,microsecond=0)
    features=phase5a.issue_features(index,grid_issue)
    features.update(phase5b.harmonic_features(issued))
    return features,index

def feature_availability(features, index, issued):
    """Explain eligible station data versus values actually available to frozen models."""
    anchor = issued.replace(minute=0, second=0, microsecond=0)
    expected = anchor - dt.timedelta(hours=1)
    result = {"model_anchor_utc": phase6_forecast.stamp(anchor),
              "expected_latest_bin_utc": phase6_forecast.stamp(expected),
              "stations": {}, "missing_features": {}}
    for station, variable, label in (
        ("MAUL1", "stage", "MAUL1"), ("NWCL1", "water", "NWCL1"),
        ("NWCL1", "residual", "NWCL1_residual"),
        ("NWCL1", "wind_u", "NWCL1_wind_u"),
        ("NWCL1", "wind_v", "NWCL1_wind_v"),
        ("MDLL1", "stage", "MDLL1"), ("DENL1", "discharge", "DENL1")):
        bins = index.get((station, variable), {})
        available = sorted(bins)
        last = available[-1] if available else None
        result["stations"][label] = {
            "expected_bin_present": expected in bins,
            "latest_eligible_bin_utc": phase6_forecast.stamp(last) if last else None,
            "lag_from_expected_hours": (expected-last).total_seconds()/3600 if last else None,
        }
    groups = {
        "coastal": ("nwcl1_", "mdll1_"),
        "river": ("denl1_", "mchl1_"),
        "target": ("maul1_",),
    }
    for name, prefixes in groups.items():
        missing = sorted(k for k,v in features.items()
                         if k.startswith(prefixes) and v is None)
        result["missing_features"][name] = missing
    return result


def issue(simulated=False,run_id="",scheduled=False):
    started=dt.datetime.now(UTC).replace(microsecond=0)
    nominal=started.replace(minute=17,second=0,microsecond=0) if scheduled else started
    if scheduled and nominal>started: nominal-=dt.timedelta(hours=1)
    snap=phase6_sources.fetch_snapshot(started)
    actual=dt.datetime.now(UTC).replace(microsecond=0)
    features,index=feature_snapshot(snap,actual)
    latest,status=latest_snapshot(snap,actual)
    status["MAUL1_00065"]["model_feature_available"]=features.get("maul1_stage_native_ft") is not None
    feature_diagnostics=feature_availability(features,index,actual)
    artifact_path=ROOT/"site/data/prospective/model-artifacts.json"
    if not artifact_path.exists():
        artifact=phase6_models.freeze_models(ROOT); artifact_path.parent.mkdir(parents=True,exist_ok=True); artifact_path.write_text(json.dumps(artifact,indent=2)+"\n")
    artifacts=phase6_models.load_artifacts(artifact_path)
    byh={}
    eligible=status["MAUL1_00065"]["status"]=="eligible" and status["MAUL1_00065"]["model_feature_available"]
    for h in (6,12,24):
        byh[str(h)]={}
        if eligible:
            byh[str(h)]["persistence"]={"status":"issued","predicted_stage_native_ft":features["maul1_stage_native_ft"],"predicted_change_ft":0.0,"interval_lower_ft":None,"interval_upper_ft":None,"interval_status":"not_calibrated"}
        else: byh[str(h)]["persistence"]={"status":"abstained","reason":"MAUL1 00065 missing or older than 2 hours"}
        for name in phase6_models.FROZEN:
            model=artifacts["models"][name][str(h)]
            row=dict(features)
            for key in model["feature_names"]: row.setdefault(key,None)
            if not eligible:
                byh[str(h)][name]={"status":"abstained","reason":"eligible recent MAUL1 native stage unavailable"}; continue
            try:
                stage,missing=phase6_models.predict_frozen(artifacts,name,h,row)
                half=model["half_width_80_ft"]
                byh[str(h)][name]={"status":"issued","predicted_stage_native_ft":stage,"predicted_change_ft":stage-features["maul1_stage_native_ft"],
                    "interval_lower_ft":stage-half,"interval_upper_ft":stage+half,"imputed_feature_count":missing,"artifact_sha256":artifacts["artifact_sha256"]}
            except Exception as exc: byh[str(h)][name]={"status":"error","reason":str(exc)}
    record=phase6_forecast.make_record(actual,nominal,{"maul1_stage_native_ft":features.get("maul1_stage_native_ft"),"features":features,"source_snapshot":snap,"availability":status,"feature_diagnostics":feature_diagnostics,"model_artifact_sha256":artifacts["artifact_sha256"]},byh,simulated=simulated,run_id=run_id,model_anchor_time=actual.replace(minute=0,second=0,microsecond=0))
    record["forecast_snapshot_sha256"]=hashlib.sha256(json.dumps(record["snapshot"],sort_keys=True).encode()).hexdigest()
    phase6_forecast.write_immutable(record,ROOT/"site/data/prospective/archive")
    attempts=ROOT/"site/data/prospective/attempts"; attempts.mkdir(parents=True,exist_ok=True)
    (attempts/f"{record['issuance_id']}.json").write_text(json.dumps({"issuance_id":record["issuance_id"],"actual_issue_time_utc":phase6_forecast.stamp(actual),"sources":snap["sources"],"availability":status,"feature_diagnostics":feature_diagnostics,"mode":record["mode"]},indent=2)+"\n")
    return record

def update_site():
    base=ROOT/"site/data/prospective"; issues=base/"archive/issues"; verdir=base/"verification"; verdir.mkdir(parents=True,exist_ok=True)
    observation_dir=base/"archive/observations"; observation_dir.mkdir(parents=True,exist_ok=True)
    verification_capture=phase6_sources.fetch_snapshot(dt.datetime.now(UTC))
    capture_name=phase6_forecast.stamp(dt.datetime.now(UTC)).replace(":","")
    # Keep verification-source provenance, without committing another multi-MB plain JSON.
    # Existing .json records remain untouched and fully readable.
    import gzip
    capture_path=observation_dir/f"{capture_name}.json.gz"
    if not capture_path.exists():
        payload=(json.dumps(verification_capture,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
        with capture_path.open("xb") as stream:
            stream.write(gzip.compress(payload,compresslevel=9,mtime=0))
    observed=[{"valid_time_utc":x["valid_time_utc"],"ingested_utc":x["retrieved_utc"],"value_ft":float(x["value"])} for x in verification_capture["observations"] if x["station"]=="MAUL1" and x["parameter"]=="stage" and x["datum"]=="gage height"]
    forecasts=[json.loads(p.read_text()) for p in sorted(issues.glob("*.json"))]
    forecasts.sort(key=lambda x:x["actual_issue_time_utc"])
    records=[]
    for record in forecasts:
        prev=[]
        for p in sorted(verdir.glob(record["issuance_id"]+"-*.json")):
            prev.extend(json.loads(p.read_text()).get("revisions",[]))
        revisions=phase6_verify.verify(record,observed,dt.datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),prev)
        if revisions:
            path=verdir/f"{record['issuance_id']}-{len(prev)+1:04d}.json"
            path.write_text(json.dumps({"revisions":revisions},indent=2)+"\n")
        records.append(record)
    latest=records[-1] if records else None
    # Compact website projection: full source evidence remains immutable in archive/issues.
    if latest:
        projection={key:latest[key] for key in ("schema","issuance_id","mode","nominal_issue_time_utc","actual_issue_time_utc","latest_maul1_native_stage_ft","forecasts") if key in latest}
        projection["snapshot"]={"availability":{key:{"status":value.get("status"),"age_hours":value.get("age_hours")} for key,value in latest.get("snapshot",{}).get("availability",{}).items()}}
        projection["snapshot"]["feature_diagnostics"]=latest.get("snapshot",{}).get("feature_diagnostics",{})
        for key in ("model_anchor_time_utc","run_id"):
            if key in latest: projection[key]=latest[key]
    else: projection={"status":"no_authentic_issuance"}
    (base/"latest.json").write_text(json.dumps(projection,indent=2)+"\n")
    (base/"history/index.json").parent.mkdir(parents=True,exist_ok=True)
    all_v=[v for p in sorted(verdir.glob("*.json")) for v in json.loads(p.read_text()).get("revisions",[])]
    latest_v={}
    for v in all_v:
        key=(v["issuance_id"],v["horizon_hours"],v["model"])
        if key not in latest_v or v["revision"]>latest_v[key]["revision"]: latest_v[key]=v
    by_group={}
    for v in latest_v.values():
        rec=next((r for r in records if r["issuance_id"]==v["issuance_id"]),None)
        if not rec or rec.get("latest_maul1_native_stage_ft") is None: continue
        group=f"{v['model']}:{v['horizon_hours']}h"
        by_group.setdefault(group,[]).append({"valid_time_utc":v["forecast_valid_time_utc"],"actual_issue_time_utc":rec["actual_issue_time_utc"],"forecast_change_ft":v["predicted_native_stage_ft"]-rec["latest_maul1_native_stage_ft"],
            "observed_change_ft":v["observed_native_stage_ft"]-rec["latest_maul1_native_stage_ft"],
            "persistence_change_ft":0.0,
            "interval_lower_ft":v.get("interval_lower_ft"),"interval_upper_ft":v.get("interval_upper_ft"),
            "interval_covered":v.get("interval_covered"),"upper_bound_exceeded":v.get("upper_bound_exceeded")})
    summary={k:phase6_metrics.compute_metrics(v) for k,v in by_group.items()}
    for key,rows in by_group.items():
        if key.endswith(":24h"):
            summary[key]["qualifying_24h_events"]=phase6_metrics.summarize_qualifying_events(rows)
    (base/"history/index.json").write_text(json.dumps([{"issuance_id":r["issuance_id"],"actual_issue_time_utc":r["actual_issue_time_utc"],"mode":r["mode"],
        "forecast_file":f"../archive/issues/{r['issuance_id']}.json",
        "verification_files":[f"../verification/{p.name}" for p in sorted(verdir.glob(r["issuance_id"]+"-*.json"))]}
        for r in records],indent=2)+"\n")
    (base/"performance.json").write_text(json.dumps({"prospective_only":True,"model_horizon_metrics":summary,"verification_count":len(latest_v),"revision_count":len(all_v)},indent=2)+"\n")

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--simulate",action="store_true"); parser.add_argument("--run-id",default="manual"); parser.add_argument("--scheduled",action="store_true")
    args=parser.parse_args()
    rec=issue(args.simulate,args.run_id,args.scheduled); update_site(); print(json.dumps({"issuance_id":rec["issuance_id"],"mode":rec["mode"],"nominal_issue_time_utc":rec["nominal_issue_time_utc"],"actual_issue_time_utc":rec["actual_issue_time_utc"]}))
