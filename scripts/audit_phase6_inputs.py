"""Audit repeated authentic Phase 6 issuance input availability without rewriting archives."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def summarize(attempts):
    records=[]
    for attempt in attempts:
        if attempt.get("mode") != "authentic":
            continue
        diagnostic=attempt.get("feature_diagnostics") or {}
        stations=diagnostic.get("stations") or {}
        mchl=next((source for source in attempt.get("sources",[])
                   if source.get("station")=="MCHL1"),{})
        nwcl=stations.get("NWCL1",{})
        residual=stations.get("NWCL1_residual",{})
        records.append({
            "issuance_id":attempt.get("issuance_id"),
            "actual_issue_time_utc":attempt.get("actual_issue_time_utc"),
            "mchl1_source_status":mchl.get("status","not_reported"),
            "mchl1_observation_count":mchl.get("observation_count"),
            "mchl1_forecast_eligible":bool(mchl.get("forecast_eligible",False)),
            "nwcl1_expected_bin_present":nwcl.get("expected_bin_present"),
            "nwcl1_water_lag_hours":nwcl.get("lag_from_expected_hours"),
            "nwcl1_residual_expected_bin_present":residual.get("expected_bin_present"),
            "nwcl1_residual_lag_hours":residual.get("lag_from_expected_hours"),
            "missing_coastal_features":diagnostic.get("missing_features",{}).get("coastal",[]),
            "missing_mchl1_features":[k for k in diagnostic.get("missing_features",{}).get("river",[])
                                      if k.startswith("mchl1_")],
        })
    records.sort(key=lambda x:(x["actual_issue_time_utc"] or "",x["issuance_id"] or ""))
    recent=records[-12:]
    return {
        "schema":"phase6.input-continuity.v1",
        "authentic_issuance_count":len(records),
        "recent_issuances":recent,
        "mchl1_retrieved_unverified_count":sum(x["mchl1_source_status"]=="retrieved_unverified" for x in records),
        "nwcl1_water_missing_expected_bin_count":sum(x["nwcl1_expected_bin_present"] is False for x in records),
        "nwcl1_residual_missing_expected_bin_count":sum(x["nwcl1_residual_expected_bin_present"] is False for x in records),
        "note":"Counts are overlapping issuance diagnostics, not independent events or source reliability estimates."
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts-dir",type=Path,default=Path("site/data/prospective/attempts"))
    args=parser.parse_args()
    attempts=[json.loads(p.read_text()) for p in sorted(args.attempts_dir.glob("*.json"))]
    print(json.dumps(summarize(attempts),indent=2))

if __name__=="__main__":
    main()
