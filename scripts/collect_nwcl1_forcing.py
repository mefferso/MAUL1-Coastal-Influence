"""Collect prospective coastal forcing observations into an append-only archive.

Research / Shadow Evaluation / Not Operational. NOAA and USGS source payloads
are stored content-addressed; receipts record our actual retrieval time. No
forecast or historical availability is inferred by this program.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from validate_forcing_archive import validate

UTC = dt.timezone.utc
NOAA_API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
USGS_API = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items"
NOAA_STATION = "8761927"
SOURCES = {
    "NWCL1": {"provider": "NOAA CO-OPS", "station": NOAA_STATION, "products": ["wind", "water_level", "predictions"]},
    "DENL1": {"provider": "USGS", "station": "USGS-07378500", "parameters": ["00060", "00065"]},
    "MDLL1": {"provider": "USGS", "station": "USGS-301200090072400", "parameters": ["00065"]},
    "MAUL1": {"provider": "USGS", "station": "USGS-07380215", "parameters": ["00065", "63160"]},
}
USER_AGENT = "MAUL1-research-observation-archive/1.0 (nonoperational; public data research)"


def iso(stamp: dt.datetime) -> str:
    return stamp.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_noaa_time(value: str) -> dt.datetime:
    return dt.datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)


def noaa_url(product: str, date: str = "latest") -> str:
    query = {"product": product, "station": NOAA_STATION, "date": date,
             "units": "english", "time_zone": "gmt", "format": "json"}
    if product in {"water_level", "predictions"}:
        query["datum"] = "MLLW"
    return NOAA_API + "?" + urllib.parse.urlencode(query)


def noaa_records(product, payload, retrieved, digest, url, raw_path, provider_date=None):
    list_key = "predictions" if product == "predictions" else "data"
    if not isinstance(payload, dict) or "error" in payload or not isinstance(payload.get(list_key), list):
        raise ValueError(f"NOAA {product}: provider error or absent data list")
    out = []
    for entry in payload[list_key]:
        try:
            valid = parse_noaa_time(entry["t"])
            prediction = product == "predictions"
            if valid > retrieved and not prediction:
                continue
            if product == "wind":
                speed, direction = float(entry["s"]), float(entry["d"])
                if not math.isfinite(speed) or speed < 0 or not math.isfinite(direction) or not 0 <= direction <= 360:
                    continue
                # CO-OPS direction is the direction the wind is coming from.
                theta = math.radians(direction)
                values = [("wind_speed", speed, "knots", "not_applicable"),
                          ("wind_direction", direction, "degrees", "not_applicable"),
                          ("wind_u", -speed * math.sin(theta), "knots", "not_applicable"),
                          ("wind_v", -speed * math.cos(theta), "knots", "not_applicable")]
            else:
                value = float(entry["v"])
                if not math.isfinite(value):
                    continue
                values = [("tide_prediction" if prediction else "water_level", value, "ft", "MLLW")]
        except (KeyError, TypeError, ValueError):
            continue
        for variable, value, unit, datum in values:
            row = {"schema_version": "forcing-1", "record_type": "prediction" if prediction else "observation",
                   "station_id": "NWCL1", "source": "NOAA CO-OPS 8761927", "sensor_id": "8761927",
                   "variable": variable, "unit": unit, "datum": datum,
                   "valid_time": iso(valid), "retrieved_at": iso(retrieved),
                   "provider_http_date": provider_date, "value": value,
                   "status": "predicted" if prediction else "provisional",
                   "raw_id": f"coops:8761927:{product}:{entry['t']}:{variable}",
                   "qc_flags": [f"provider_flag:{entry['f']}"] if entry.get("f") not in (None, "", "0") else [],
                   "product": product, "provider_url": url, "raw_sha256": digest, "raw_path": raw_path,
                   "source_metadata": {"direction_convention": "degrees clockwise from true north, direction from",
                                       "water_level_datum": "MLLW" if product in {"water_level", "predictions"} else None}}
            validate(row)
            out.append(row)
    return out


def records_for_payload(product, payload, received, digest, url, raw_path):
    """Backward-compatible parser name from the original PR #60 prototype."""
    return noaa_records(product, payload, received, digest, url, raw_path)


def usgs_records(payload, retrieved, digest, url, raw_path, provider_date=None):
    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        raise ValueError("USGS: invalid OGC response or missing features")
    out = []
    for feature in payload["features"]:
        props = feature.get("properties") or {}
        station = props.get("monitoring_location_id")
        parameter = str(props.get("parameter_code", ""))
        # Common OGC latest-continuous properties use time and value; tolerate
        # advertised aliases while preserving the untouched feature in raw.
        t = props.get("time") or props.get("datetime") or props.get("observation_time")
        value = props.get("value")
        unit = props.get("unit_of_measure") or props.get("unit")
        if not station or not t or value is None or not unit:
            continue
        station_name = next((name for name, meta in SOURCES.items() if meta["station"] == station), None)
        if station_name is None:
            continue
        try:
            valid = dt.datetime.fromisoformat(str(t).replace("Z", "+00:00")).astimezone(UTC)
            number = float(value)
            if not math.isfinite(number) or valid > retrieved:
                continue
        except (TypeError, ValueError):
            continue
        variable = {"00060": "discharge", "00065": "gage_height", "63160": "water_level"}.get(parameter)
        if not variable:
            continue
        expected_units = {"discharge": {"ft3/s", "ft^3/s", "cfs"}, "gage_height": {"ft", "feet"}, "water_level": {"ft", "feet"}}
        normalized = "cfs" if unit in {"ft3/s", "ft^3/s", "cfs"} else "ft" if unit in {"ft", "feet"} else unit
        if normalized not in expected_units[variable]:
            continue
        status = "observed" if str(props.get("approval_status", "")).lower() in {"approved", "approved for publication"} else "provisional"
        datum = "NAVD88" if parameter == "63160" else f"native_gage_datum:{station}"
        flags = []
        for key in ("qualifiers", "approval_status", "grade", "method_id"):
            if props.get(key) not in (None, "", []):
                flags.append(f"{key}:{props[key]}")
        row = {"schema_version": "forcing-1", "record_type": "observation", "station_id": station_name,
               "source": f"USGS {station}", "sensor_id": props.get("time_series_id"),
               "variable": variable, "unit": normalized, "provider_unit": unit, "datum": datum,
               "valid_time": iso(valid), "retrieved_at": iso(retrieved), "provider_http_date": provider_date,
               "provider_updated_at": props.get("last_modified"), "value": number, "status": status,
               "raw_id": f"usgs:{station}:{parameter}:{t}:{props.get('time_series_id','')}",
               "qc_flags": flags, "parameter_code": parameter, "provider_url": url,
               "raw_sha256": digest, "raw_path": raw_path}
        validate(row)
        out.append(row)
    return out


def fetch(url, opener, retries=3, sleeper=time.sleep):
    last = None
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with opener(request, timeout=30) as response:
                body = response.read()
                received = dt.datetime.now(UTC)
                return body, received, response.headers.get("Date"), response.status, attempt
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and not 500 <= exc.code < 600:
                raise RuntimeError(f"non-retryable HTTP {exc.code}: {exc.reason}") from exc
            last = exc
            if attempt < retries:
                sleeper(min(2 ** (attempt - 1), 8))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt < retries:
                sleeper(min(2 ** (attempt - 1), 8))
    raise RuntimeError(f"request failed after {retries} attempts: {last}")


def usgs_url(station, parameters):
    # OGC API behavior for a comma-separated property filter is inconsistent;
    # request each parameter separately so one series cannot mask another.
    if isinstance(parameters, (tuple, list)):
        if len(parameters) != 1:
            raise ValueError("USGS requests must select exactly one parameter_code")
        parameters = parameters[0]
    query = {"monitoring_location_id": station, "parameter_code": parameters, "limit": "500", "f": "json"}
    return USGS_API + "?" + urllib.parse.urlencode(query)


def write_immutable_raw(raw_dir, body):
    digest = hashlib.sha256(body).hexdigest()
    path = raw_dir / f"{digest}.json"
    if not path.exists():
        path.write_bytes(body)
    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError("content-addressed raw payload integrity failure")
    return digest, "raw/" + path.name


def append_receipts(receipts_dir, rows):
    """Append new values only; a changed provider revision is retained as a new receipt."""
    receipts_dir.mkdir(parents=True, exist_ok=True)
    existing = set()
    for path in receipts_dir.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                existing.add((r.get("source"), r.get("station_id"), r.get("variable"), r.get("valid_time"), r.get("value"), tuple(r.get("qc_flags", []))))
            except json.JSONDecodeError:
                raise RuntimeError(f"corrupt existing archive file: {path}")
    new = []
    for row in rows:
        key = (row["source"], row["station_id"], row["variable"], row["valid_time"], row["value"], tuple(row["qc_flags"]))
        if key not in existing:
            new.append(row)
            existing.add(key)
    if not new:
        return None, 0
    path = receipts_dir / (dt.datetime.now(UTC).strftime("%Y%m%d") + ".jsonl")
    with path.open("a", encoding="utf-8") as stream:
        for row in new:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    return path, len(new)


def collect(out_dir, now=None, opener=None, sleeper=time.sleep):
    now = now or dt.datetime.now(UTC)
    opener = opener or urllib.request.urlopen
    out = pathlib.Path(out_dir)
    raw_dir = out / "raw"
    receipts_dir = out / "receipts"
    health_dir = out / "health"
    for directory in (raw_dir, receipts_dir, health_dir):
        directory.mkdir(parents=True, exist_ok=True)
    results = []
    all_rows = []
    for product in ("wind", "water_level", "predictions"):
        url = noaa_url(product)
        item = {"source": f"NOAA CO-OPS 8761927 {product}", "critical": True, "url": url}
        try:
            body, received, http_date, status, attempts = fetch(url, opener, sleeper=sleeper)
            digest, raw_path = write_immutable_raw(raw_dir, body)
            payload = json.loads(body)
            rows = noaa_records(product, payload, received, digest, url, raw_path, http_date)
            provider_items = len(payload.get("predictions" if product == "predictions" else "data", []))
            accepted_items = len(rows) // (4 if product == "wind" else 1)
            item_status = "success" if accepted_items == provider_items and accepted_items else (
                "partial" if accepted_items else "invalid" if provider_items else "empty")
            item.update(status=item_status, response_code=status, attempts=attempts, count=len(rows),
                        provider_item_count=provider_items, invalid_or_unmapped_item_count=max(0, provider_items - accepted_items),
                        retrieved_at=iso(received),
                        valid_time_min=min((r["valid_time"] for r in rows), default=None),
                        valid_time_max=max((r["valid_time"] for r in rows), default=None),
                        newest_valid_age_seconds=max(0, int((received - max(dt.datetime.fromisoformat(r["valid_time"].replace("Z", "+00:00")) for r in rows)).total_seconds())) if rows and product != "predictions" else None,
                        qc_flag_counts={flag: sum(flag in r["qc_flags"] for r in rows) for flag in sorted({f for r in rows for f in r["qc_flags"]})})
            all_rows.extend(rows)
        except Exception as exc:
            item.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        results.append(item)
    for name in ("DENL1", "MDLL1", "MAUL1"):
        meta = SOURCES[name]
        for parameter in meta["parameters"]:
            url = usgs_url(meta["station"], parameter)
            item = {"source": f"USGS {name} {meta['station']} parameter {parameter}",
                    "critical": not (name == "MAUL1" and parameter == "63160"), "url": url}
            try:
                body, received, http_date, status, attempts = fetch(url, opener, sleeper=sleeper)
                digest, raw_path = write_immutable_raw(raw_dir, body)
                rows = usgs_records(json.loads(body), received, digest, url, raw_path, http_date)
                rows = [row for row in rows if row["station_id"] == name and row["parameter_code"] == parameter]
                provider_items = len(json.loads(body).get("features", []))
                item_status = "success" if len(rows) == provider_items and rows else (
                    "partial" if rows else "invalid" if provider_items else "empty")
                item.update(status=item_status, response_code=status, attempts=attempts,
                            count=len(rows), provider_item_count=provider_items,
                            invalid_or_unmapped_item_count=max(0, provider_items - len(rows)),
                            parameters_returned=sorted({r["parameter_code"] for r in rows}),
                            retrieved_at=iso(received),
                            valid_time_min=min((r["valid_time"] for r in rows), default=None),
                            valid_time_max=max((r["valid_time"] for r in rows), default=None),
                            newest_valid_age_seconds=max(0, int((received - dt.datetime.fromisoformat(max(r["valid_time"] for r in rows).replace("Z", "+00:00"))).total_seconds())) if rows else None,
                            qc_flag_counts={flag: sum(flag in r["qc_flags"] for r in rows) for flag in sorted({f for r in rows for f in r["qc_flags"]})})
                all_rows.extend(rows)
            except Exception as exc:
                item.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            results.append(item)
    receipt_file, added = append_receipts(receipts_dir, all_rows)
    run_id = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    report = {"schema_version": "forcing-run-1", "run_id": run_id, "started_at": iso(now),
              "completed_at": iso(dt.datetime.now(UTC)), "sources": results,
              "records_seen": len(all_rows), "records_added": added,
              "receipt_file": str(receipt_file) if receipt_file else None,
              "critical_failures": [r["source"] for r in results if r["critical"] and r["status"] != "success"]}
    health_path = health_dir / f"{run_id}.json"
    with health_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=pathlib.Path, default=pathlib.Path("research/prospective-forcing-archive"))
    parser.add_argument("--live-smoke", action="store_true", help="retrieve official NOAA and USGS current feeds without saving archive")
    args = parser.parse_args()
    if args.live_smoke:
        for product in ("wind", "water_level", "predictions"):
            url = noaa_url(product)
            body, received, date, status, attempts = fetch(url, urllib.request.urlopen)
            parsed = json.loads(body)
            digest = hashlib.sha256(body).hexdigest()
            rows = noaa_records(product, parsed, received, digest, url, f"raw/{digest}.json", date)
            if status != 200 or not rows:
                raise RuntimeError(f"live NOAA smoke failed: {url} HTTP {status}, parsed receipts={len(rows)}")
            print(json.dumps({"source": f"NOAA CO-OPS 8761927 {product}", "http_status": status,
                              "parsed_receipts": len(rows), "retrieved_at": iso(received), "http_date": date}))
        for name in ("DENL1", "MDLL1", "MAUL1"):
            meta = SOURCES[name]
            for parameter in meta["parameters"]:
                url = usgs_url(meta["station"], parameter)
                body, received, date, status, attempts = fetch(url, urllib.request.urlopen)
                parsed = json.loads(body)
                digest = hashlib.sha256(body).hexdigest()
                rows = usgs_records(parsed, received, digest, url, f"raw/{digest}.json", date)
                rows = [r for r in rows if r["station_id"] == name and r["parameter_code"] == parameter]
                optional_direct_datum = name == "MAUL1" and parameter == "63160"
                if status != 200 or (not rows and not optional_direct_datum):
                    sample_props = (parsed.get("features") or [{}])[0].get("properties", {}) if isinstance(parsed, dict) else {}
                    raise RuntimeError(f"live USGS smoke failed: {name} parameter {parameter} HTTP {status}, "
                                       f"parsed receipts={len(rows)}, sample_properties={json.dumps(sample_props, sort_keys=True)[:1200]}")
                print(json.dumps({"source": f"USGS {name} {meta['station']} parameter {parameter}", "http_status": status,
                                  "parsed_receipts": len(rows), "retrieved_at": iso(received), "http_date": date,
                                  "optional_unavailable": optional_direct_datum and not rows}))
        return
    report = collect(args.out_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["critical_failures"]:
        raise SystemExit("critical acquisition failures or empty feeds; see health/ run report")


if __name__ == "__main__":
    main()
