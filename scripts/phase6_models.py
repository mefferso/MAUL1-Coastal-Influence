"""Freeze and replay the calibration-only Phase 5A/5B estimators."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import numpy as np
import csv, gzip

HORIZONS = (6, 12, 24)
FROZEN = {"phase5a_maul1_only": ("phase5a", "maul1_only", "phase5a_maul1_only_ft"),
          "phase5a_coastal": ("phase5a", "maul1_plus_coastal", "phase5a_coastal_ft"),
          "phase5b_coastal_tidal": ("phase5b", "maul1_coastal_tidal", "maul1_coastal_tidal"),
          "phase5b_full_multivariable": ("phase5b", "full_multivariable", "full_multivariable")}

def _git_blob_sha(path):
    data=Path(path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
def _canonical_sha(value):
    # Replay diagnostics can differ at floating-point roundoff across BLAS builds.
    # The artifact identity covers the frozen estimators, transforms, intervals,
    # and source/code versions, while replay residuals remain separately recorded.
    identity={k:v for k,v in value.items() if k not in {"holdout_replay","artifact_sha256"}}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def freeze_models(root):
    root = Path(root); sys.path.insert(0, str(root / "scripts"))
    import phase5a, phase5b
    a_path = root / "site/data/history/phase5a/models.json"
    b_path = root / "site/data/history/phase5b/models.json"
    uncertainty_a = json.loads((root / "site/data/history/phase5a/uncertainty.json").read_text())
    uncertainty_b = json.loads((root / "site/data/history/phase5b/uncertainty.json").read_text())
    a = json.loads(a_path.read_text())["final_holdout_fit"]
    table, _ = phase5b._load_table(root)
    models = {name: {} for name in FROZEN}
    replay = {}
    b_report = json.loads(b_path.read_text())
    for h in HORIZONS:
        for public, (family, key, pred_col) in FROZEN.items():
            if family == "phase5a":
                raw = a[str(h)]["parameters"]["models"][key]
                model = {k: raw[k] for k in ("feature_names", "medians", "means", "scales", "flag_means", "flag_scales", "active", "coefficients", "target_low", "target_high", "alpha", "target_clip_quantiles", "train_count")}
                model = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k,v in model.items()}
                half = uncertainty_a[str(h)][key]["half_width_ft"]
                published_col = "maul1_only_ft" if key == "maul1_only" else "maul1_plus_coastal_ft"
                with gzip.open(root / "site/data/history/phase5a/features.csv.gz", "rt", encoding="utf-8") as stream:
                    feature_rows = {r["issue_time_utc"]: r for r in csv.DictReader(stream)}
                with gzip.open(root / "site/data/history/phase5a/predictions.csv.gz", "rt", encoding="utf-8") as stream:
                    refs = [r for r in csv.DictReader(stream) if r["split"] == "holdout" and int(r["horizon_hours"]) == h and r.get(published_col) not in (None, "") and r.get("persistence_ft") not in (None, "")]
                matrix = np.asarray([[float(feature_rows[r["issue_time_utc"]][n]) if feature_rows[r["issue_time_utc"]].get(n) not in (None, "") else np.nan for n in model["feature_names"]] for r in refs])
                delta, _ = phase5a.predict_ridge(raw, matrix)
                expected = np.asarray([float(r[published_col]) for r in refs])
                actual_stage = np.asarray([float(r["persistence_ft"]) for r in refs])
                max_error = float(np.max(np.abs(expected-(actual_stage+delta)))) if len(refs) else 0.0
                if max_error > 1e-8: raise ValueError(f"Phase 5A replay mismatch {public} {h}: {max_error}")
                replay[f"{public}:{h}"] = {"n":len(refs),"max_abs_error_ft":max_error}
            else:
                spec = b_report[str(h)][key]
                features = spec["feature_names"]
                train_ix = [i for i,r in enumerate(table[h]) if r["split"] == "calibration" and r["actual"] is not None and r["target_time"] < phase5b.BOUNDARY-phase5a.dt.timedelta(hours=72) and r.get("maul1_stage_native_ft") is not None]
                hold_ix = [i for i,r in enumerate(table[h]) if r["split"] == "holdout" and r["actual"] is not None and r.get("maul1_stage_native_ft") is not None]
                _, _, reconstructed = phase5b._forecast_with_model(table[h], features, train_ix, hold_ix, spec["alpha"])
                # Coefficients, medians, and clipping bounds are published Phase 5B
                # state. Only the omitted normalization transforms are reconstructed.
                reconstructed["coefficients"] = np.asarray(spec["coefficients"], dtype=float)
                reconstructed["medians"] = np.asarray(spec["medians"], dtype=float)
                reconstructed["target_low"], reconstructed["target_high"] = map(float, spec["target_clip_ft"])
                model = {k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in reconstructed.items()}
                half = uncertainty_b[str(h)][key]["half_width_ft"]
                hold_rows=[table[h][i] for i in hold_ix]
                matrix=np.asarray([[r.get(n) if r.get(n) is not None else np.nan for n in features] for r in hold_rows],dtype=float)
                deltas,_=phase5a.predict_ridge(reconstructed,matrix)
                preds=np.asarray([float(r["maul1_stage_native_ft"])+d for r,d in zip(hold_rows,deltas)])
                max_error = 0.0
                # The archived forecast column is the published holdout reference.
                expected = []
                with __import__('gzip').open(root / "site/data/history/phase5b/predictions.csv.gz", "rt", encoding="utf-8") as stream:
                    for row in csv.DictReader(stream):
                        if row["split"] == "holdout" and int(row["horizon_hours"]) == h and row.get(pred_col): expected.append(float(row[pred_col]))
                if len(expected) != len(preds): raise ValueError(f"Phase 5B holdout count mismatch {public} {h}: {len(expected)} != {len(preds)}")
                max_error = float(np.max(np.abs(np.asarray(expected)-preds))) if expected else 0.0
                if max_error > 1e-8: raise ValueError(f"Phase 5B replay mismatch {public} {h}: {max_error}")
                replay[f"{public}:{h}"] = {"n":len(preds),"max_abs_error_ft":max_error}
            model.update({"horizon_hours":h,"model":public,"half_width_80_ft":float(half),"stage_is_native_maul1":True})
            models[public][str(h)] = model
    artifact = {"schema":"phase6.frozen-models.v1","version":"phase5-frozen-2026-10-22",
        "primary_model":"phase5a_coastal","horizons_hours":list(HORIZONS),"models":models,
        "calibration":{"archive_start_utc":phase5a.ARCHIVE_START.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "boundary_utc":phase5a.BOUNDARY.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "training_target_exclusive_utc":(phase5a.BOUNDARY-phase5a.dt.timedelta(hours=phase5a.EMBARGO_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "holdout_issue_start_inclusive_utc":(phase5a.BOUNDARY+phase5a.dt.timedelta(hours=phase5a.EMBARGO_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "embargo_hours":phase5a.EMBARGO_HOURS,"lookback_hours":phase5a.LOOKBACK_HOURS},
        "excluded":["gated_full","maul1_astro_retrospective"],
        "sources":{"phase5a_models_git_blob":_git_blob_sha(a_path),"phase5b_models_git_blob":_git_blob_sha(b_path),
                   "phase5a_uncertainty_git_blob":_git_blob_sha(root/"site/data/history/phase5a/uncertainty.json"),
                   "phase5b_uncertainty_git_blob":_git_blob_sha(root/"site/data/history/phase5b/uncertainty.json"),
                   "phase5a_feature_archive_git_blob":_git_blob_sha(root/"site/data/history/phase5a/features.csv.gz"),
                   "phase5a_prediction_archive_git_blob":_git_blob_sha(root/"site/data/history/phase5a/predictions.csv.gz"),
                   "phase5b_prediction_archive_git_blob":_git_blob_sha(root/"site/data/history/phase5b/predictions.csv.gz"),
                   "phase5a_code_git_blob":_git_blob_sha(root/"scripts/phase5a.py"),"phase5b_code_git_blob":_git_blob_sha(root/"scripts/phase5b.py")},
        "holdout_replay":replay,"tolerance_ft":1e-8}
    artifact["artifact_sha256"] = _canonical_sha(artifact)
    return artifact

def load_artifacts(path): return json.loads(Path(path).read_text())

def predict_frozen(artifact, model_name, horizon, features):
    model = artifact["models"][model_name][str(horizon)]
    values = np.asarray([[features.get(n, np.nan) for n in model["feature_names"]]], dtype=float)
    observed = np.isfinite(values); imp = np.where(observed, values, model["medians"])
    v = (imp-model["means"])/model["scales"]
    flags = (~observed).astype(float)
    f = (flags-model["flag_means"])/model["flag_scales"]
    active = np.asarray(model["active"], bool)
    delta = np.r_[1., np.concatenate((v,f),axis=1)[0,active]] @ np.asarray(model["coefficients"])
    stage = float(features["maul1_stage_native_ft"])
    return stage + float(np.clip(delta, model["target_low"], model["target_high"])), int((~observed).sum())

def verify_saved_artifact(root, artifact):
    """Replay the committed frozen state against every published eligible holdout row."""
    root=Path(root); sys.path.insert(0,str(root/"scripts")); import phase5a,phase5b,csv,gzip
    replay={}
    with gzip.open(root/"site/data/history/phase5a/features.csv.gz","rt",encoding="utf-8") as stream:
        feature_by_issue={r["issue_time_utc"]:r for r in csv.DictReader(stream)}
    with gzip.open(root/"site/data/history/phase5a/predictions.csv.gz","rt",encoding="utf-8") as stream:
        pa=[r for r in csv.DictReader(stream) if r["split"]=="holdout"]
    table,_=phase5b._load_table(root)
    with gzip.open(root/"site/data/history/phase5b/predictions.csv.gz","rt",encoding="utf-8") as stream:
        phase5b_refs={(r["issue_time_utc"],int(r["horizon_hours"])):r for r in csv.DictReader(stream) if r["split"]=="holdout"}
    for h in HORIZONS:
        for model,col in (("phase5a_maul1_only","maul1_only_ft"),("phase5a_coastal","maul1_plus_coastal_ft")):
            rows=[r for r in pa if int(r["horizon_hours"])==h and r.get(col) not in (None,"") and r.get("persistence_ft") not in (None,"")]
            errors=[]
            for r in rows:
                f=feature_by_issue[r["issue_time_utc"]]
                pred,_=predict_frozen(artifact,model,h,{k:(float(f[k]) if f.get(k) not in (None,"") else np.nan) for k in artifact["models"][model][str(h)]["feature_names"]} | {"maul1_stage_native_ft":float(r["persistence_ft"])})
                errors.append(abs(pred-float(r[col])))
            replay[f"{model}:{h}"]={"n":len(rows),"max_abs_error_ft":max(errors,default=0.0)}
        for model,col in (("phase5b_coastal_tidal","maul1_coastal_tidal"),("phase5b_full_multivariable","full_multivariable")):
            rows=[r for r in table[h] if r["split"]=="holdout" and r["actual"] is not None and r.get("maul1_stage_native_ft") is not None]
            errors=[]
            for r in rows:
                pred,_=predict_frozen(artifact,model,h,r)
                ref=phase5b_refs.get((r["issue_time"].strftime("%Y-%m-%dT%H:%M:%SZ"),h))
                if ref and ref.get(col) not in (None,""): errors.append(abs(pred-float(ref[col])))
            replay[f"{model}:{h}"]={"n":len(rows),"max_abs_error_ft":max(errors,default=0.0)}
    failures={k:v for k,v in replay.items() if v["max_abs_error_ft"]>artifact["tolerance_ft"]}
    if failures: raise ValueError(f"Frozen saved model holdout replay exceeds tolerance: {failures}")
    return replay

if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("--root",default="."); parser.add_argument("--output",default="site/data/prospective/model-artifacts.json"); parser.add_argument("--compare")
    args=parser.parse_args(); root=Path(args.root); output=root/args.output
    output.parent.mkdir(parents=True,exist_ok=True)
    artifact=freeze_models(root); output.write_text(json.dumps(artifact,indent=2)+"\n")
    if args.compare:
        expected=json.loads((root/args.compare).read_text())
        if expected.get("schema")!="phase6.frozen-models.v1": raise SystemExit("Unsupported committed frozen artifact schema")
        if expected.get("sources")!=artifact.get("sources"): raise SystemExit("Frozen artifact sources/code versions differ from current Phase 5 inputs")
        replay=verify_saved_artifact(root,expected)
        print(json.dumps({"committed_artifact_sha256":expected.get("artifact_sha256"),"committed_artifact_replay":replay},indent=2))
    print(json.dumps({"artifact_sha256":artifact["artifact_sha256"],"holdout_replay":artifact["holdout_replay"]},indent=2))
