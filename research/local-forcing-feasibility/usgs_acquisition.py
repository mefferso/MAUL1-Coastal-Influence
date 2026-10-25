"""Research-only USGS Water Data OGC API snapshot helper.

This module never feeds a forecast. It stores provider features unchanged and
adds the local request/receipt times and a response hash around each response.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/continuous/items"
SOURCES = {
    "USGS-301828090363100": ("00045",),
    "USGS-07378810": ("00045", "00065"),
    "USGS-07378746": ("00045", "00065"),
    "USGS-07379960": ("00045", "00065"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def request_url(site_id: str, parameter_code: str, hours: int = 24) -> str:
    if site_id not in SOURCES or parameter_code not in SOURCES[site_id]:
        raise ValueError("site and parameter must be listed in the source inventory")
    if not 1 <= hours <= 168:
        raise ValueError("hours must be between 1 and 168")
    query = urlencode({
        "f": "json",
        "monitoring_location_id": site_id,
        "parameter_code": parameter_code,
        "datetime": f"PT{hours}H",
        "limit": "10000",
    })
    return f"{BASE_URL}?{query}"


def _get(url: str, timeout: int = 30) -> tuple[int, bytes]:
    req = Request(url, headers={"Accept": "application/geo+json, application/json", "User-Agent": "MAUL1-local-forcing-research/1.0"})
    with urlopen(req, timeout=timeout) as response:
        return response.status, response.read()


def fetch_series(site_id: str, parameter_code: str, hours: int = 24, get=_get, now=utc_now) -> dict:
    """Fetch one recent series, retaining raw feature properties and provenance."""
    url = request_url(site_id, parameter_code, hours)
    requested_at = now()
    try:
        status_code, body = get(url)
        received_at = now()
        response_hash = hashlib.sha256(body).hexdigest()
        payload = json.loads(body)
        features = payload.get("features")
        if not isinstance(features, list):
            raise ValueError("provider response has no GeoJSON features array")
        return {
            "site_id": site_id,
            "parameter_code": parameter_code,
            "requested_at_utc": requested_at,
            "received_at_utc": received_at,
            "request_url": url,
            "http_status": status_code,
            "response_sha256": response_hash,
            "provider_timestamp": payload.get("timeStamp"),
            "status": "retrieved" if features else "no_observations",
            "features": features,
        }
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "site_id": site_id,
            "parameter_code": parameter_code,
            "requested_at_utc": requested_at,
            "received_at_utc": now(),
            "request_url": url,
            "status": "retrieval_error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "features": [],
        }


def collect(hours: int = 24, get=_get, now=utc_now, pause_seconds: float = 0.1) -> dict:
    started_at = now()
    results = []
    for site_id, parameters in SOURCES.items():
        for parameter_code in parameters:
            results.append(fetch_series(site_id, parameter_code, hours, get=get, now=now))
            if pause_seconds:
                time.sleep(pause_seconds)
    return {
        "schema_version": 1,
        "record_classification": "research-only; not a forecast issuance or verification record",
        "retrieval_started_at_utc": started_at,
        "retrieval_completed_at_utc": now(),
        "source": "USGS Water Data OGC API",
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=int, default=24, help="recent period to query (1-168 hours)")
    parser.add_argument("--output", type=Path, required=True, help="write one immutable JSON snapshot here")
    args = parser.parse_args()
    payload = collect(hours=args.hours)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = sum(item["status"] == "retrieval_error" for item in payload["results"])
    print(json.dumps({"output": str(args.output), "series": len(payload["results"]), "retrieval_errors": errors}))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
