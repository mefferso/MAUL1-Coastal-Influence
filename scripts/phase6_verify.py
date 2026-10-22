"""Independent, append-only verification of already-issued forecast records."""
from __future__ import annotations
import datetime as dt

UTC = dt.timezone.utc
def parse(value):
    result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None: raise ValueError("timezone required")
    return result.astimezone(UTC)

def verify(record, observations, ingestion_time, previous=()):
    ingested = parse(ingestion_time)
    seen = {(x.get("issuance_id"), x.get("horizon_hours"), x.get("observation_valid_time_utc"), x.get("observed_native_stage_ft"),x.get("model")) for x in previous}
    result = []
    for horizon, forecast in record.get("forecasts", {}).items():
        valid = forecast["valid_time_utc"]
        if parse(valid) > ingested: continue
        target = parse(valid)
        candidates=[o for o in observations if o.get("value_ft") is not None and parse(o.get("ingested_utc", ingestion_time)) <= ingested
                    and abs((parse(o["valid_time_utc"])-target).total_seconds()) <= 1800]
        obs = min(candidates,key=lambda o:abs((parse(o["valid_time_utc"])-target).total_seconds())) if candidates else None
        if not obs: continue
        models = forecast.get("models", {})
        for model, item in models.items():
            if item.get("status") != "issued" or item.get("predicted_stage_native_ft") is None: continue
            key = (record["issuance_id"], int(horizon), obs["valid_time_utc"], obs["value_ft"], model)
            if key in seen: continue
            predicted, actual = float(item["predicted_stage_native_ft"]), float(obs["value_ft"])
            prior_same = [x for x in previous if x.get("issuance_id") == record["issuance_id"] and x.get("horizon_hours") == int(horizon) and x.get("model")==model]
            revision = len(prior_same) + 1
            result.append({"issuance_id": record["issuance_id"], "horizon_hours": int(horizon), "model": model,
                "forecast_valid_time_utc": valid, "observation_valid_time_utc": obs["valid_time_utc"],
                "observation_ingested_utc": obs.get("ingested_utc", ingestion_time),
                "observed_native_stage_ft": actual, "predicted_native_stage_ft": predicted,
                "interval_lower_ft":item.get("interval_lower_ft"),"interval_upper_ft":item.get("interval_upper_ft"),
                "interval_covered":item.get("interval_lower_ft") is not None and item.get("interval_upper_ft") is not None and float(item["interval_lower_ft"])<=actual<=float(item["interval_upper_ft"]),
                "upper_bound_exceeded":item.get("interval_upper_ft") is not None and actual>float(item["interval_upper_ft"]),
                "signed_error_ft": predicted-actual, "absolute_error_ft": abs(predicted-actual),
                "underforecast": predicted < actual, "revision": revision, "revision_created_utc": ingestion_time})
    return result
