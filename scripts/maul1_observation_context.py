"""Refresh a separate, visual-only 28-day MAUL1 00065 observation series."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import sys
import tempfile
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build

UTC = dt.timezone.utc
OUTPUT = ROOT / "site/data/maul1-observation-context.json"
BASE_URL = "https://waterservices.usgs.gov/nwis/iv/"
USER_AGENT = "MAUL1-research/1.1 (public research; visual observation context)"
DAYS = 28
SCHEMA = "maul1-observation-context.v1"


def _stamp(value: dt.datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_stamp(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("observation timestamp must include a timezone")
    return parsed.astimezone(UTC)


def request_url(now: dt.datetime) -> str:
    start = now.astimezone(UTC) - dt.timedelta(days=DAYS)
    params = {
        "format": "json", "sites": "07380215", "parameterCd": "00065",
        "startDT": _stamp(start), "endDT": _stamp(now), "siteStatus": "all",
    }
    return BASE_URL + "?" + urllib.parse.urlencode(params)


def _get(url: str) -> tuple[bytes, str | None]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read(), response.headers.get("Date")


def validate_dataset(document: dict) -> dict:
    if document.get("schema") != SCHEMA:
        raise ValueError("unsupported observation-context schema")
    if (document.get("station") != "MAUL1" or document.get("usgs_site") != "07380215"
            or document.get("parameter_code") != "00065" or document.get("units") != "ft"
            or document.get("datum") != "gage height"):
        raise ValueError("observation context must be USGS MAUL1 00065 native gage height in feet")
    if document.get("purpose") != "visual_context_only_not_forecast_verification":
        raise ValueError("observation context must remain visual-only")
    if document.get("source") != "USGS NWIS Instantaneous Values":
        raise ValueError("observation context source must be USGS NWIS IV")
    source_url = document.get("source_url", "")
    parsed_url = urllib.parse.urlparse(source_url)
    query = urllib.parse.parse_qs(parsed_url.query)
    if (parsed_url.scheme != "https" or parsed_url.netloc != "waterservices.usgs.gov"
            or parsed_url.path != "/nwis/iv/" or query.get("sites") != ["07380215"]
            or query.get("parameterCd") != ["00065"]):
        raise ValueError("observation provenance must identify USGS MAUL1 parameter 00065")
    cutoff = _parse_stamp(document["retrieved_utc"])
    requested_start = _parse_stamp(document["requested_start_utc"])
    requested_end = _parse_stamp(document["requested_end_utc"])
    if requested_end != cutoff or requested_start > cutoff:
        raise ValueError("invalid requested observation window")
    points = document.get("observations")
    if not isinstance(points, list) or not points:
        raise ValueError("observation context has no usable observations")
    previous = None
    for point in points:
        stamp = _parse_stamp(point["valid_time_utc"])
        value = float(point["stage_ft"])
        if not math.isfinite(value) or stamp > cutoff or stamp < requested_start:
            raise ValueError("invalid or out-of-window observation")
        if previous is not None and stamp <= previous:
            raise ValueError("observations must be unique and chronologically ordered")
        qualifiers = point.get("qualifiers", [])
        if not isinstance(qualifiers, list):
            raise ValueError("USGS qualifiers must be retained as a list")
        provisional = any(str(q).upper() in {"P", "PROVISIONAL"} for q in qualifiers)
        if point.get("provisional") is not provisional:
            raise ValueError("provisional status must match the USGS qualifier")
        previous = stamp
    if len({p["valid_time_utc"] for p in points}) != len(points):
        raise ValueError("duplicate observation timestamp")
    if (document.get("observation_count") != len(points)
            or document.get("coverage_start_utc") != points[0]["valid_time_utc"]
            or document.get("coverage_end_utc") != points[-1]["valid_time_utc"]
            or document.get("provisional_count") != sum(bool(p["provisional"]) for p in points)):
        raise ValueError("observation coverage metadata does not match the series")
    digest = document.get("response_sha256", "")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
        raise ValueError("invalid source response hash")
    return document


def build_dataset(raw: bytes, retrieved: dt.datetime, server_date: str | None = None) -> dict:
    retrieved = retrieved.astimezone(UTC)
    start = retrieved - dt.timedelta(days=DAYS)
    url = request_url(retrieved)
    payload = json.loads(raw.decode("utf-8"))
    series = payload.get("value", {}).get("timeSeries", [])
    target = [item for item in series
              if item.get("sourceInfo", {}).get("siteCode", [{}])[0].get("value") == "07380215"
              and item.get("variable", {}).get("variableCode", [{}])[0].get("value") == "00065"]
    if len(target) != 1:
        raise ValueError(f"expected one MAUL1 USGS 00065 time series; found {len(target)}")
    parsed = build.parse_usgs(payload, "MAUL1")
    points_by_time: dict[str, dict] = {}
    for row in parsed:
        if row.get("variable") != "stage" or row.get("unit") != "ft" or row.get("datum") != "gage height":
            continue
        valid = _parse_stamp(row["time"])
        if valid < start or valid > retrieved:
            continue
        value = float(row["value"])
        if not math.isfinite(value):
            continue
        qualifiers = sorted({str(q) for q in (row.get("quality") or [])})
        item = {"valid_time_utc": _stamp(valid), "stage_ft": value, "qualifiers": qualifiers,
                "provisional": any(q.upper() in {"P", "PROVISIONAL"} for q in qualifiers)}
        prior = points_by_time.get(item["valid_time_utc"])
        if prior is not None and prior != item:
            raise ValueError(f"conflicting duplicate observation at {item['valid_time_utc']}")
        points_by_time[item["valid_time_utc"]] = item
    observations = [points_by_time[k] for k in sorted(points_by_time)]
    if not observations:
        raise ValueError("USGS returned no usable MAUL1 00065 observations")
    document = {
        "schema": SCHEMA, "purpose": "visual_context_only_not_forecast_verification",
        "station": "MAUL1", "usgs_site": "07380215", "parameter_code": "00065",
        "parameter": "gage height", "units": "ft", "datum": "gage height",
        "source": "USGS NWIS Instantaneous Values", "source_url": url,
        "revision_policy": "current USGS response snapshot for visual context; immutable archived verification observations remain authoritative",
        "retrieved_utc": _stamp(retrieved), "server_date": server_date,
        "requested_start_utc": _stamp(start), "requested_end_utc": _stamp(retrieved),
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "observation_count": len(observations),
        "coverage_start_utc": observations[0]["valid_time_utc"],
        "coverage_end_utc": observations[-1]["valid_time_utc"],
        "provisional_count": sum(bool(p["provisional"]) for p in observations),
        "observations": observations,
    }
    return validate_dataset(document)


def _read_previous(path: pathlib.Path) -> dict | None:
    try:
        return validate_dataset(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def update_dataset(path: pathlib.Path = OUTPUT, fetcher=_get, now: dt.datetime | None = None) -> dict:
    now = (now or dt.datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    previous = _read_previous(path)
    url = request_url(now)
    try:
        raw, server_date = fetcher(url)
        current = build_dataset(raw, now, server_date)
    except Exception as exc:
        return {"status": "retained_previous" if previous else "unavailable", "error": str(exc),
                "dataset_retrieved_utc": previous.get("retrieved_utc") if previous else None,
                "path": str(path)}
    if previous and previous["observations"] == current["observations"]:
        return {"status": "unchanged", "dataset_retrieved_utc": previous["retrieved_utc"],
                "coverage_start_utc": previous["coverage_start_utc"],
                "coverage_end_utc": previous["coverage_end_utc"], "observation_count": previous["observation_count"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(current, handle, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {"status": "updated", "dataset_retrieved_utc": current["retrieved_utc"],
            "coverage_start_utc": current["coverage_start_utc"],
            "coverage_end_utc": current["coverage_end_utc"], "observation_count": current["observation_count"]}


if __name__ == "__main__":
    result = update_dataset()
    print(json.dumps(result, indent=2))
