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
AWC_API = "https://aviationweather.gov/api/data/metar"
USGS_API = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/continuous/items"
NOAA_STATION = "8761927"
AWC_STATION = "KNEW"
SOURCES = {
    "NWCL1": {"provider": "NOAA CO-OPS", "station": NOAA_STATION, "products": ["wind", "water_level", "predictions"], "category": "core"},
    "KNEW": {"provider": "NOAA Aviation Weather Center", "station": AWC_STATION, "products": ["METAR wind"], "category": "shadow"},
    "DENL1": {"provider": "USGS", "station": "USGS-07378500", "parameters": ["00060", "00065"], "category": "core"},
    "MDLL1": {"provider": "USGS", "station": "USGS-301200090072400", "parameters": ["00065"], "category": "core"},
    "MAUL1": {"provider": "USGS", "station": "USGS-07380215", "parameters": ["00065", "63160"], "category": "core"},
    "MCHL1-USGS": {"provider": "USGS", "station": "USGS-073802302", "parameters": ["00065"], "category": "shadow"},
    # Candidate local rainfall and tributary context. These are optional feeds:
    # operational 00045 precip may be temporary and site-stage feeds can lapse.
    "USGS-301828090363100": {"provider": "USGS", "station": "USGS-301828090363100",
                              "parameters": ["00045"], "critical": False, "category": "shadow",
                              "site_name": "Precip at Amite River at Maurepas, Louisiana",
                              "hydrologic_role": "point precipitation near the MAUL1 lower-basin outlet"},
    "USGS-07379960": {"provider": "USGS", "station": "USGS-07379960",
                      "parameters": ["00045", "00065"], "critical": False, "category": "shadow",
                      "site_name": "Dawson Creek at Bluebonnet Blvd near Baton Rouge, Louisiana",
                      "hydrologic_role": "urban tributary stage and temporary point precipitation"},
    "USGS-07378810": {"provider": "USGS", "station": "USGS-07378810",
                      "parameters": ["00045", "00065"], "critical": False, "category": "shadow",
                      "site_name": "Bayou Fountain at Bluebonnet Blvd near Baton Rouge, Louisiana",
                      "hydrologic_role": "tributary stage and temporary point precipitation"},
    "USGS-07378746": {"provider": "USGS", "station": "USGS-07378746",
                      "parameters": ["00045", "00065"], "critical": False, "category": "shadow",
                      "site_name": "Bayou Manchac at Alligator Bayou near Kleinpeter, Louisiana",
                      "hydrologic_role": "downstream boundary/backwater stage and temporary point precipitation"},
}
USER_AGENT = "MAUL1-research-observation-archive/1.0 (nonoperational; public data research)"


def iso(stamp: dt.datetime) -> str:
    return stamp.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_noaa_time(value: str) -> dt.datetime:
    return dt.datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)


def noaa_url(product: str, date: str = "latest", begin=None, end=None) -> str:
    query = {"product": product, "station": NOAA_STATION,
             "units": "english", "time_zone": "gmt", "format": "json"}
    if begin is None or end is None:
        query["date"] = date
    else:
        query["begin_date"] = begin.astimezone(UTC).strftime("%Y%m%d %H:%M")
        query["end_date"] = end.astimezone(UTC).strftime("%Y%m%d %H:%M")
    if product in {"water_level", "predictions"}:
        query["datum"] = "MLLW"
    return NOAA_API + "?" + urllib.parse.urlencode(query)


def awc_url(hours=2):
    return AWC_API + "?" + urllib.parse.urlencode({"ids": AWC_STATION, "format": "json", "hours": str(hours)})


def awc_wind_records(payload, retrieved, digest, url, raw_path, provider_date=None):
    """Parse official AWC METAR JSON; METAR wind uses knots and direction-from."""
    if not isinstance(payload, list):
        raise ValueError("AWC METAR: expected a JSON array")
    station_reports = [r for r in payload if isinstance(r, dict) and r.get("icaoId") == AWC_STATION]
    if not station_reports:
        raise ValueError("AWC METAR: no KNEW report in response")
    out = []
    for report in station_reports:
        try:
            valid = dt.datetime.fromtimestamp(int(report["obsTime"]), UTC)
            if valid > retrieved:
                continue
            speed = float(report["wspd"])
            if not math.isfinite(speed) or speed < 0:
                continue
            direction = report.get("wdir")
            values = [("wind_speed", speed, "knots")]
            if direction is not None and int(direction) != 0x7fffffff:
                direction = float(direction)
                if not math.isfinite(direction) or not 0 <= direction <= 360:
                    continue
                theta = math.radians(direction)
                values.extend([("wind_direction", direction, "degrees"),
                               ("wind_u", -speed * math.sin(theta), "knots"),
                               ("wind_v", -speed * math.cos(theta), "knots")])
            gust = report.get("wgst")
            if gust is not None:
                gust = float(gust)
                if math.isfinite(gust) and gust >= speed:
                    values.append(("wind_gust", gust, "knots"))
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            continue
        for variable, value, unit in values:
            row = {"schema_version": "forcing-1", "record_type": "observation", "station_id": "KNEW",
                   "source": "NOAA AWC METAR KNEW", "sensor_id": "KNEW-ASOS", "source_category": "shadow",
                   "variable": variable, "unit": unit, "datum": "not_applicable", "valid_time": iso(valid),
                   "retrieved_at": iso(retrieved), "provider_http_date": provider_date, "value": value,
                   "acquisition_mode": "prospective",
                   "status": "observed", "raw_id": f"awc:KNEW:{report['obsTime']}:{variable}",
                   "qc_flags": [], "provider_report_time": report.get("reportTime"),
                   "provider_url": url, "raw_sha256": digest, "raw_path": raw_path,
                   "source_metadata": {"wind_direction_convention": "degrees clockwise from true north, direction from",
                                       "wind_average_period": "ASOS/METAR standard 2-minute average",
                                       "sensor_height_m": None, "exposure": "airport; not over-water",
                                       "station_latitude": report.get("lat"), "station_longitude": report.get("lon"),
                                       "station_elevation_m": report.get("elev"), "raw_metar": report.get("rawOb")}}
            validate(row)
            out.append(row)
    if not out:
        raise ValueError("AWC METAR: no valid wind values")
    return out


def noaa_records(product, payload, retrieved, digest, url, raw_path, provider_date=None, acquisition_mode=None):
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
                   "acquisition_mode": acquisition_mode or ("prospective" if prediction or (retrieved-valid) <= dt.timedelta(hours=2) else "delayed_recovery"),
                   "status": "predicted" if prediction else "provisional",
                   "raw_id": f"coops:8761927:{product}:{entry['t']}:{variable}",
                   "qc_flags": [f"provider_flag:{flag}" for flag in str(entry.get("f", "")).split(",")
                                if flag.strip() not in ("", "0")],
                   "product": product, "provider_url": url, "raw_sha256": digest, "raw_path": raw_path,
                   "source_category": "core",
                   "source_metadata": {"direction_convention": "degrees clockwise from true north, direction from",
                                       "water_level_datum": "MLLW" if product in {"water_level", "predictions"} else None}}
            validate(row)
            out.append(row)
    return out


def records_for_payload(product, payload, received, digest, url, raw_path):
    """Backward-compatible parser name from the original PR #60 prototype."""
    return noaa_records(product, payload, received, digest, url, raw_path)


def usgs_records(payload, retrieved, digest, url, raw_path, provider_date=None, acquisition_mode=None):
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
        station_name = next((name for name, meta in SOURCES.items() if meta.get("provider") == "USGS" and meta["station"] == station), None)
        if station_name is None:
            continue
        try:
            valid = dt.datetime.fromisoformat(str(t).replace("Z", "+00:00"))
            if valid.tzinfo is None:
                continue
            valid = valid.astimezone(UTC)
            number = float(value)
            if not math.isfinite(number) or valid > retrieved:
                continue
            # USGS operational precipitation uses negative sentinels for missing
            # or invalid accumulations; zero is a valid dry reading.
            if parameter == "00045" and number < 0:
                continue
        except (TypeError, ValueError):
            continue
        variable = {"00045": "precipitation", "00060": "discharge", "00065": "gage_height", "63160": "water_level"}.get(parameter)
        if not variable:
            continue
        expected_units = {"discharge": {"ft3/s", "ft^3/s", "cfs"}, "gage_height": {"ft", "feet"},
                          "water_level": {"ft", "feet"}, "precipitation": {"in", "inch", "inches", "mm", "millimeter", "millimeters", "millimetre", "millimetres"}}
        normalized = ("cfs" if unit in {"ft3/s", "ft^3/s", "cfs"} else
                      "ft" if unit in {"ft", "feet"} else
                      "in" if unit in {"in", "inch", "inches"} else
                      "mm" if unit in {"mm", "millimeter", "millimeters", "millimetre", "millimetres"} else unit)
        if normalized not in expected_units[variable]:
            continue
        status = "observed" if str(props.get("approval_status", "")).lower() in {"approved", "approved for publication"} else "provisional"
        datum = "NAVD88" if parameter == "63160" else f"native_gage_datum:{station}"
        flags = []
        for key in ("qualifier", "qualifiers", "approval_status", "grade", "method_id"):
            if props.get(key) not in (None, "", []):
                flags.append(f"{key}:{props[key]}")
        row = {"schema_version": "forcing-1", "record_type": "observation", "station_id": station_name,
               "source": f"USGS {station}", "sensor_id": props.get("time_series_id"),
               "variable": variable, "unit": normalized, "provider_unit": unit, "datum": datum,
               "valid_time": iso(valid), "retrieved_at": iso(retrieved), "provider_http_date": provider_date,
               "provider_updated_at": props.get("last_modified"), "value": number, "status": status,
               "acquisition_mode": acquisition_mode or ("prospective" if (retrieved-valid) <= dt.timedelta(hours=2) else "delayed_recovery"),
               "raw_id": f"usgs:{station}:{parameter}:{t}:{props.get('time_series_id','')}",
               "qc_flags": flags, "parameter_code": parameter, "provider_url": url,
               "source_category": SOURCES[station_name]["category"],
               "raw_sha256": digest, "raw_path": raw_path}
        if parameter == "00045":
            interval = props.get("accumulation_period_seconds")
            if not isinstance(interval, int) or isinstance(interval, bool) or interval <= 0:
                interval = None
            row.update(measurement_semantics="reported_accumulation",
                       accumulation_period_seconds=interval,
                       valid_time_semantics="provider observation timestamp; accumulation interval endpoint is not otherwise inferred")
        validate(row)
        out.append(row)
    return out


def fetch(url, opener, retries=3, sleeper=time.sleep, clock=None):
    last = None
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with opener(request, timeout=30) as response:
                body = response.read()
                received = (clock or (lambda: dt.datetime.now(UTC)))()
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


def usgs_url(station, parameters, begin=None, end=None):
    # OGC API behavior for a comma-separated property filter is inconsistent;
    # request each parameter separately so one series cannot mask another.
    if isinstance(parameters, (tuple, list)):
        if len(parameters) != 1:
            raise ValueError("USGS requests must select exactly one parameter_code")
        parameters = parameters[0]
    query = {"monitoring_location_id": station, "parameter_code": parameters, "limit": "10000", "f": "json"}
    if begin is not None and end is not None:
        query["time"] = f"{iso(begin)}/{iso(end)}"
    return USGS_API + "?" + urllib.parse.urlencode(query)


def noaa_windows(begin, end, max_days=31):
    """Split NOAA queries into intervals no longer than the documented limit."""
    windows, cursor, finish = [], begin.astimezone(UTC), end.astimezone(UTC)
    while cursor < finish:
        boundary = min(cursor + dt.timedelta(days=max_days), finish)
        windows.append((cursor, boundary))
        cursor = boundary
    return windows or [(finish, finish)]


def fetch_usgs_history(url, opener, sleeper=time.sleep, clock=None, max_pages=1000, on_page=None):
    """Fetch OGC continuous pages and preserve the bytes and request URL per page."""
    pages, next_url, seen = [], url, set()
    while next_url:
        if next_url in seen or len(pages) >= max_pages:
            raise RuntimeError("USGS pagination cycle or page limit exceeded")
        seen.add(next_url)
        body, retrieved, http_date, status, attempts = fetch(next_url, opener, sleeper=sleeper, clock=clock)
        payload = json.loads(body)
        page = (next_url, body, retrieved, http_date, status, attempts, payload)
        pages.append(page)
        if on_page:
            on_page(page)
        link = next((x for x in payload.get("links", []) if x.get("rel") == "next"), None)
        next_url = urllib.parse.urljoin(next_url, link["href"]) if link and link.get("href") else None
    return pages


def history_begin(receipts_dir, health_dir, source_name, now, receipt_station_id=None, parameter_code=None, receipt_product=None):
    """Resume from overlapping successful history, or bootstrap from earliest receipt."""
    for path in sorted(pathlib.Path(health_dir).glob("*.json"), reverse=True):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for source in report.get("sources", []):
            if source.get("source") == source_name and source.get("request_window") == "history" and source.get("status") == "success" and source.get("valid_time_max"):
                stamp = dt.datetime.fromisoformat(source["valid_time_max"].replace("Z", "+00:00")).astimezone(UTC)
                return stamp-dt.timedelta(hours=1)
    earliest = None
    for path in pathlib.Path(receipts_dir).glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                matches = (row.get("source") == source_name if receipt_station_id is None else
                           row.get("station_id") == receipt_station_id and
                           (parameter_code is None or str(row.get("parameter_code")) == str(parameter_code)) and
                           (receipt_product is None or row.get("product") == receipt_product))
                if matches and row.get("record_type", "observation") == "observation":
                    stamp = dt.datetime.fromisoformat(row["valid_time"].replace("Z", "+00:00")).astimezone(UTC)
                    earliest = stamp if earliest is None else min(earliest, stamp)
            except (ValueError, KeyError, json.JSONDecodeError):
                continue
    return earliest or now.astimezone(UTC)-dt.timedelta(hours=1)


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
                existing.add(_receipt_identity(r))
            except json.JSONDecodeError:
                raise RuntimeError(f"corrupt existing archive file: {path}")
    new = []
    for row in rows:
        key = _receipt_identity(row)
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


def _receipt_identity(row):
    """Keep separate provider series/sensors even when readings happen to match."""
    return (row.get("source"), row.get("station_id"), row.get("variable"), row.get("valid_time"),
            row.get("value"), tuple(row.get("qc_flags", [])), row.get("sensor_id"),
            row.get("parameter_code"), row.get("accumulation_period_seconds"), row.get("status"),
            row.get("provider_updated_at"), row.get("unit"), row.get("datum"),
            row.get("measurement_semantics"))


def noaa_recent_window_due(health_dir, product, now):
    """Fetch NOAA's larger recovery window at least daily; retry it until successful."""
    target = f"NOAA CO-OPS 8761927 {product}"
    for path in sorted(pathlib.Path(health_dir).glob("*.json"), reverse=True):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for source in report.get("sources", []):
            if source.get("source") != target or source.get("request_window") != "recent" or source.get("status") != "success":
                continue
            retrieved = source.get("retrieved_at")
            if retrieved:
                last = dt.datetime.fromisoformat(retrieved.replace("Z", "+00:00")).astimezone(UTC)
                return now.astimezone(UTC) - last >= dt.timedelta(hours=24)
    return True


def collect(out_dir, now=None, opener=None, sleeper=time.sleep, clock=None):
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
    # Airport METAR is useful regional context, but not a substitute for lake wind.
    url = awc_url()
    item = {"source": "NOAA AWC METAR KNEW", "critical": False, "category": "shadow", "url": url}
    try:
        body, received, http_date, status, attempts = fetch(url, opener, sleeper=sleeper, clock=clock)
        digest, raw_path = write_immutable_raw(raw_dir, body)
        payload = json.loads(body)
        rows = awc_wind_records(payload, received, digest, url, raw_path, http_date)
        newest = max(r["valid_time"] for r in rows)
        newest_stamp = dt.datetime.fromisoformat(newest.replace("Z", "+00:00"))
        age_seconds = max(0, int((received - newest_stamp).total_seconds()))
        item.update(status="success" if status == 200 and age_seconds <= 2 * 3600 else "stale",
                    response_code=status, attempts=attempts, count=len(rows),
                    provider_item_count=len(payload), retrieved_at=iso(received), valid_time_max=newest,
                    newest_valid_age_seconds=age_seconds, freshness_limit_seconds=2 * 3600)
        all_rows.extend(rows)
    except Exception as exc:
        item.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    results.append(item)
    for product in ("wind", "water_level", "predictions"):
        source_name = f"NOAA CO-OPS 8761927 {product}"
        if product == "predictions":
            requests = [("latest", noaa_url(product, "latest"))]
        else:
            begin = history_begin(receipts_dir, health_dir, source_name, now,
                                  receipt_station_id="NWCL1", receipt_product=product)
            requests = [("history", noaa_url(product, "history", start, end))
                        for start, end in noaa_windows(begin, now)]
        for window, url in requests:
            item = {"source": source_name, "request_window": window, "critical": True, "url": url}
            try:
                body, received, http_date, status, attempts = fetch(url, opener, sleeper=sleeper, clock=clock)
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
                            raw_responses=[{"url":url,"sha256":digest,"path":raw_path,
                                            "http_date":http_date,"response_code":status,
                                            "retrieved_at":iso(received),"attempts":attempts}],
                            window_begin=urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("begin_date", [None])[0],
                            window_end=urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("end_date", [None])[0],
                            valid_time_min=min((r["valid_time"] for r in rows), default=None),
                            valid_time_max=max((r["valid_time"] for r in rows), default=None),
                            newest_valid_age_seconds=max(0, int((received - max(dt.datetime.fromisoformat(r["valid_time"].replace("Z", "+00:00")) for r in rows)).total_seconds())) if rows and product != "predictions" else None,
                            qc_flag_counts={flag: sum(flag in r["qc_flags"] for r in rows) for flag in sorted({f for r in rows for f in r["qc_flags"]})})
                all_rows.extend(rows)
            except Exception as exc:
                item.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            results.append(item)
    for name, meta in SOURCES.items():
        if meta.get("provider") != "USGS":
            continue
        for parameter in meta["parameters"]:
            source_name = f"USGS {name} {meta['station']} parameter {parameter}"
            begin = history_begin(receipts_dir, health_dir, source_name, now, receipt_station_id=name, parameter_code=parameter)
            url = usgs_url(meta["station"], parameter, begin, now)
            item = {"source": f"USGS {name} {meta['station']} parameter {parameter}",
                    "request_window": "history", "window_begin": iso(begin), "window_end": iso(now),
                    "critical": meta.get("critical", meta["category"] == "core") and not (name == "MAUL1" and parameter == "63160"),
                    "category": meta["category"], "url": url,
                    "hydrologic_role": meta.get("hydrologic_role")}
            raw_responses, page_payloads = [], {}

            def preserve_page(page):
                page_url, body, page_received, page_date, page_status, page_attempts, _payload = page
                digest, raw_path = write_immutable_raw(raw_dir, body)
                raw_responses.append({"url":page_url,"sha256":digest,"path":raw_path,
                                      "http_date":page_date,"response_code":page_status,
                                      "retrieved_at":iso(page_received),"attempts":page_attempts})
                page_payloads[page_url] = (digest, raw_path)

            try:
                pages = fetch_usgs_history(url, opener, sleeper=sleeper, clock=clock, on_page=preserve_page)
                rows, provider_items = [], 0
                status, attempts, received, http_date = 200, 0, now, None
                for page_url, body, received, http_date, status, page_attempts, payload in pages:
                    digest, raw_path = page_payloads[page_url]
                    attempts += page_attempts
                    provider_items += len(payload.get("features", []))
                    page_rows = usgs_records(payload, received, digest, page_url, raw_path, http_date)
                    rows.extend(row for row in page_rows if row["station_id"] == name and row["parameter_code"] == parameter)
                item["raw_responses"] = raw_responses
                item["attempts"] = attempts
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
                if raw_responses:
                    item["raw_responses"] = raw_responses
                    item["attempts"] = sum(response["attempts"] for response in raw_responses)
                item.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            results.append(item)
    receipt_file, added = append_receipts(receipts_dir, all_rows)
    run_id = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    report = {"schema_version": "forcing-run-1", "run_id": run_id, "started_at": iso(now),
              "completed_at": iso(dt.datetime.now(UTC)), "sources": results,
              "records_seen": len(all_rows), "records_added": added,
              "receipt_file": str(receipt_file) if receipt_file else None,
              "critical_failures": [r["source"] for r in results if r["critical"] and r["status"] != "success"],
              "shadow_failures": [r["source"] for r in results if r.get("category") == "shadow" and r["status"] != "success"]}
    health_path = health_dir / f"{run_id}.json"
    with health_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=pathlib.Path, default=pathlib.Path("research/prospective-forcing-archive"))
    parser.add_argument("--live-smoke", action="store_true", help="retrieve current NOAA and USGS feeds without saving archive")
    args = parser.parse_args()
    if args.live_smoke:
        # KNEW is shadow context: report a stale/failed feed but keep checking
        # the core NWCL1 and USGS feeds regardless of its status.
        url = awc_url()
        try:
            body, received, date, status, attempts = fetch(url, urllib.request.urlopen)
            parsed = json.loads(body)
            digest = hashlib.sha256(body).hexdigest()
            rows = awc_wind_records(parsed, received, digest, url, f"raw/{digest}.json", date)
            newest = max(r["valid_time"] for r in rows)
            age = int((received - dt.datetime.fromisoformat(newest.replace("Z", "+00:00"))).total_seconds())
            station = next(r["source_metadata"] for r in rows if r["variable"] == "wind_speed")
            current = (status == 200 and age <= 2 * 3600 and station["station_latitude"] is not None
                       and station["station_longitude"] is not None)
            print(json.dumps({"source": "NOAA AWC METAR KNEW", "status": "success" if current else "stale_or_invalid",
                              "http_status": status, "parsed_receipts": len(rows), "newest_valid_time": newest,
                              "newest_valid_age_seconds": age, "retrieved_at": iso(received), "http_date": date,
                              "category": "shadow", "station_latitude": station["station_latitude"],
                              "station_longitude": station["station_longitude"], "station_elevation_m": station["station_elevation_m"]}))
        except Exception as exc:
            print(json.dumps({"source": "NOAA AWC METAR KNEW", "status": "failed", "category": "shadow",
                              "error": f"{type(exc).__name__}: {exc}"}))

        # NWCL1 CO-OPS products are critical to the established core archive.
        for product in ("wind", "water_level", "predictions"):
            smoke_now = dt.datetime.now(UTC)
            url = (noaa_url(product, "history", smoke_now-dt.timedelta(hours=6), smoke_now)
                   if product in {"wind", "water_level"} else noaa_url(product, "latest"))
            body, received, date, status, attempts = fetch(url, urllib.request.urlopen)
            parsed = json.loads(body)
            digest = hashlib.sha256(body).hexdigest()
            rows = noaa_records(product, parsed, received, digest, url, f"raw/{digest}.json", date)
            if status != 200 or not rows:
                raise RuntimeError(f"live NOAA smoke failed: {url} HTTP {status}, parsed receipts={len(rows)}")
            unique_times = {r["valid_time"] for r in rows}
            if product in {"wind", "water_level"} and len(unique_times) < 2:
                raise RuntimeError(f"live NOAA history smoke returned fewer than two valid times: {url}")
            print(json.dumps({"source": f"NOAA CO-OPS 8761927 {product}", "http_status": status,
                              "parsed_receipts": len(rows), "unique_valid_times": len(unique_times),
                              "retrieved_at": iso(received), "http_date": date,
                              "category": "core"}))

        # Verify every configured USGS source. Candidate/shadow feeds remain
        # optional: their failures are visible but cannot mask or block core.
        for name, meta in SOURCES.items():
            if meta.get("provider") != "USGS":
                continue
            for parameter in meta["parameters"]:
                smoke_now = dt.datetime.now(UTC)
                url = usgs_url(meta["station"], parameter, smoke_now-dt.timedelta(hours=6), smoke_now)
                optional_datum = name == "MAUL1" and parameter == "63160"
                critical = meta.get("critical", meta["category"] == "core") and not optional_datum
                try:
                    pages = fetch_usgs_history(url, urllib.request.urlopen)
                    rows, parsed_count = [], 0
                    for page_url, body, received, date, status, attempts, parsed in pages:
                        digest = hashlib.sha256(body).hexdigest()
                        page_rows = usgs_records(parsed, received, digest, page_url, f"raw/{digest}.json", date)
                        rows.extend(r for r in page_rows if r["station_id"] == name and r["parameter_code"] == parameter)
                        parsed_count += len(parsed.get("features", []))
                    unique_times = {r["valid_time"] for r in rows}
                except Exception as exc:
                    print(json.dumps({"source": f"USGS {name} {meta['station']} parameter {parameter}",
                                      "status": "failed", "category": meta["category"], "critical": critical,
                                      "error": f"{type(exc).__name__}: {exc}"}))
                    if critical:
                        raise
                    continue
                if (status != 200 or not rows or len(unique_times) < 2) and critical:
                    sample = (parsed.get("features") or [{}])[0].get("properties", {}) if isinstance(parsed, dict) else {}
                    raise RuntimeError(f"live USGS smoke failed: {name} parameter {parameter} HTTP {status}, "
                                       f"parsed receipts={len(rows)}, sample_properties={json.dumps(sample, sort_keys=True)[:1200]}")
                print(json.dumps({"source": f"USGS {name} {meta['station']} parameter {parameter}",
                                  "status": "success" if status == 200 and len(unique_times) >= 2 else "empty_or_failed",
                                  "http_status": status, "parsed_receipts": len(rows),
                                  "unique_valid_times":len(unique_times),
                                  "newest_valid_time": max((r["valid_time"] for r in rows), default=None),
                                  "retrieved_at": iso(received), "http_date": date,
                                  "optional_unavailable": not rows and not critical,
                                  "category": meta["category"], "critical": critical}))
        return
    report = collect(args.out_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["critical_failures"]:
        raise SystemExit("critical acquisition failures or empty feeds; see health/ run report")


if __name__ == "__main__":
    main()
