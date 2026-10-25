"""Reproducible native-station context for source-separated 2024 case windows."""
from __future__ import annotations

import gzip
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
WINDOWS = [
    {"id": "alberto_chart_antecedent", "start": "2024-06-12T00:00:00Z", "end": "2024-06-15T00:00:00Z", "interpretation": "72h antecedent to first date shown on user WeatherFlow/CO-OPS chart; not a storm-onset label"},
    {"id": "alberto_presentation_wind_claim_context", "start": "2024-06-15T00:00:00Z", "end": "2024-06-19T12:00:00Z", "interpretation": "pre-named disturbed-weather context; WeatherFlow chart indicates sustained winds but raw series and exact threshold interval unavailable"},
    {"id": "alberto_nhc_named_tropical_storm", "start": "2024-06-19T12:00:00Z", "end": "2024-06-20T09:00:00Z", "interpretation": "NHC formation through reported landfall near Tampico; exact best-track event window, not assumed local forcing onset"},
    {"id": "alberto_post_landfall_recession", "start": "2024-06-20T09:00:00Z", "end": "2024-06-27T00:00:00Z", "interpretation": "post-landfall local water-level recession window shown on deck chart"},
    {"id": "unattributed_transition_pulse", "start": "2024-06-27T00:00:00Z", "end": "2024-07-01T00:00:00Z", "interpretation": "contains the 29-30 June local rise; kept separate from Alberto recession and from Beryl Gulf influence"},
    {"id": "beryl_remote_antecedent", "start": "2024-07-01T00:00:00Z", "end": "2024-07-05T00:00:00Z", "interpretation": "Beryl Caribbean/Yucatan period before entry into Gulf; also begins the deck's July 1-10 CO-OPS context chart"},
    {"id": "beryl_gulf_to_landfall", "start": "2024-07-05T00:00:00Z", "end": "2024-07-09T00:00:00Z", "interpretation": "Yucatan crossing/Gulf transit through 8 July 08:40 UTC Texas landfall; local influence plausible, not presumed"},
    {"id": "beryl_post_landfall", "start": "2024-07-09T00:00:00Z", "end": "2024-07-12T00:00:00Z", "interpretation": "72h post-landfall local water-level follow-up"},
]


def dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def read_archive():
    rows = defaultdict(dict)
    for path in sorted((ROOT / "site/data/history/hourly").glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf8") as f:
            data = json.load(f)
        for row in data["records"]:
            if row.get("station") not in {"NWCL1", "MDLL1", "MAUL1", "DENL1"}:
                continue
            if row.get("variable") not in {"wind_u", "wind_v", "water", "prediction", "stage", "discharge"}:
                continue
            stamp = dt(row["time"])
            rows[stamp][(row["station"], row["variable"])] = None if row["missing"] else row.get("value")
    return rows


def series_summary(rows, start, end, station, variable):
    stamps = [t for t in sorted(rows) if start <= t < end]
    items = [(t, rows[t].get((station, variable))) for t in stamps]
    valid = [(t, float(v)) for t, v in items if v is not None]
    if not valid:
        return {"valid_hours": 0, "expected_hours": int((end-start).total_seconds()/3600), "start": None, "end": None, "change": None, "min": None, "max": None, "median": None}
    first_t, first = valid[0]; last_t, last = valid[-1]
    return {"valid_hours": len(valid), "expected_hours": int((end-start).total_seconds()/3600), "start": {"time": first_t.isoformat().replace("+00:00", "Z"), "value": first}, "end": {"time": last_t.isoformat().replace("+00:00", "Z"), "value": last}, "change": last-first, "min": min(v for _,v in valid), "max": max(v for _,v in valid), "median": float(np.median([v for _,v in valid]))}


def max_24h_change(rows, start, end, station, variable, transform=lambda x: x):
    vals = {t: transform(float(row[(station, variable)])) for t, row in rows.items()
            if row.get((station, variable)) is not None}
    changes = [(t, vals[t] - vals[t-timedelta(hours=24)]) for t in vals
               if start <= t < end and t-timedelta(hours=24) in vals]
    if not changes:
        return {"n_pairs": 0, "max_increase": None, "time_of_max_increase": None, "min_change": None}
    best_t, best = max(changes, key=lambda x:x[1])
    return {"n_pairs": len(changes), "max_increase": best, "time_of_max_increase": best_t.isoformat().replace("+00:00", "Z"), "min_change": min(v for _,v in changes)}


def analyze(rows):
    result = []
    for window in WINDOWS:
        start, end = dt(window["start"]), dt(window["end"])
        selected = {t: v for t, v in rows.items() if start <= t < end}
        wind = []
        for v in selected.values():
            u, north = v.get(("NWCL1", "wind_u")), v.get(("NWCL1", "wind_v"))
            if u is not None and north is not None:
                wind.append(math.hypot(float(u), float(north)) * 1.15077945)  # knots to mph
        paired_resid = []
        for v in selected.values():
            obs, pred = v.get(("NWCL1", "water")), v.get(("NWCL1", "prediction"))
            if obs is not None and pred is not None:
                paired_resid.append(float(obs) - float(pred))
        item = {**window, "nwcl1_vector_wind_mph": {"valid_hours": len(wind), "expected_hours": int((end-start).total_seconds()/3600), "max": max(wind) if wind else None, "mean": float(np.mean(wind)) if wind else None, "hours_ge_15": sum(x >= 15 for x in wind)},
                "nwcl1_same_station_mllw_residual_ft": {"valid_hours": len(paired_resid), "median": float(np.median(paired_resid)) if paired_resid else None, "min": min(paired_resid) if paired_resid else None, "max": max(paired_resid) if paired_resid else None},
                "mdll1_native_stage_ft": series_summary(rows, start, end, "MDLL1", "stage"),
                "maul1_00065_native_gage_height_ft": series_summary(rows, start, end, "MAUL1", "stage"),
                "denl1_discharge_cfs": series_summary(rows, start, end, "DENL1", "discharge")}
        residual = {}
        for t, v in rows.items():
            obs,pred=v.get(("NWCL1","water")),v.get(("NWCL1","prediction"))
            if obs is not None and pred is not None: residual[t]=float(obs)-float(pred)
        changes=[(t,residual[t]-residual[t-timedelta(hours=24)]) for t in residual if start<=t<end and t-timedelta(hours=24) in residual]
        item["nwcl1_residual_max_24h_change_ft"]={"n_pairs":len(changes),"max_increase":max((x[1] for x in changes),default=None),"time_of_max_increase":max(changes,key=lambda x:x[1])[0].isoformat().replace("+00:00","Z") if changes else None}
        item["mdll1_native_stage_max_24h_change_ft"]=max_24h_change(rows,start,end,"MDLL1","stage")
        item["maul1_00065_native_gage_height_max_24h_change_ft"]=max_24h_change(rows,start,end,"MAUL1","stage")
        item["denl1_discharge_max_24h_change_cfs"]=max_24h_change(rows,start,end,"DENL1","discharge")
        result.append(item)
    return result


def main():
    result = {"time_basis": "UTC, half-open periods [start,end)", "water_level_rule": "all level summaries are within-station only; NWCL1 water-minus-prediction is MLLW residual; MDLL1 and MAUL1 native gage heights are not cross-subtracted", "wind_rule": "NWCL1 archive vectors only, converted knots to mph; not a substitute for WeatherFlow XPTN/Mid-Lake", "event_windows": analyze(read_archive())}
    (OUT / "event_period_diagnostics.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf8")
    for w in result["event_windows"]:
        print(w["id"], w["nwcl1_vector_wind_mph"]["hours_ge_15"], w["nwcl1_same_station_mllw_residual_ft"]["median"], w["maul1_00065_native_gage_height_ft"]["change"], w["denl1_discharge_cfs"]["change"])


if __name__ == "__main__":
    main()
