"""Retrieve real NWCL1 NOAA CO-OPS wind and water receipts.

Research only. Manual collector; deliberately NOT connected to Phase 6.
Run with: python scripts/collect_nwcl1_forcing.py --out-dir local-archive
Never use this tool to retrospectively invent provider receipt times.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import pathlib
import urllib.parse
import urllib.request
from validate_forcing_archive import validate

UTC = dt.timezone.utc
API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
SOURCE = "NOAA CO-OPS 8761927"
STATION = "NWCL1"


def iso(t):
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_url(product, date):
    args = dict(product=product, station="8761927", date=date.strftime("%Y%m%d"),
                units="english", time_zone="gmt", format="json")
    if product == "water_level":
        args["datum"] = "MLLW"
    return API + "?" + urllib.parse.urlencode(args)


def records_for_payload(product, payload, received, digest, url, raw_path):
    if not isinstance(payload, dict) or "error" in payload or not isinstance(payload.get("data"), list):
        raise ValueError(f"{product}: NOAA returned an error or missing data list")
    result = []
    for idx, entry in enumerate(payload["data"]):
        try:
            valid = dt.datetime.strptime(entry["t"], "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
            # Forecast-future timestamps cannot be presented as actual observed receipts.
            if valid > received:
                continue
            if product == "wind":
                speed = float(entry["s"])
                direction = float(entry["d"])
                if not (math.isfinite(speed) and speed >= 0 and math.isfinite(direction) and 0 <= direction <= 360):
                    continue
                radians = math.radians(direction)
                readings = [("wind_u", -speed * math.sin(radians), "knots", "not_applicable"),
                            ("wind_v", -speed * math.cos(radians), "knots", "not_applicable")]
            else:
                value = float(entry["v"])
                if not math.isfinite(value):
                    continue
                readings = [("water_level", value, "ft", "MLLW")]
        except (KeyError, TypeError, ValueError):
            continue
        for variable, value, unit, datum in readings:
            rec = dict(schema_version="forcing-1", station_id=STATION, source=SOURCE,
                       variable=variable, unit=unit, datum=datum,
                       valid_time=iso(valid), retrieved_at=iso(received),
                       value=value, status="provisional",
                       raw_id=f"{product}:{entry['t']}:{idx}:{variable}",
                       qc_flags=[f"provider_flag:{entry['f']}"] if entry.get("f") else [],
                       product=product, provider_url=url, raw_sha256=digest,
                       raw_path=raw_path)
            validate(rec)
            result.append(rec)
    return result


def collect(out_dir, now=None, opener=None):
    now = now or dt.datetime.now(UTC)
    if opener is None:
        opener = urllib.request.urlopen
    out_dir = pathlib.Path(out_dir)
    raw_dir = out_dir / "raw"
    receipts_dir = out_dir / "receipts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    receipts_dir.mkdir(parents=True, exist_ok=True)
    today = now.astimezone(UTC).date()
    records = []
    # Include previous UTC day to capture delayed publication/revisions.
    for offset in (1, 0):
        date = today - dt.timedelta(days=offset)
        for product in ("wind", "water_level"):
            url = api_url(product, date)
            req = urllib.request.Request(url, headers={"User-Agent": "MAUL1-research/1.0 (nonoperational)"})
            with opener(req, timeout=30) as response:
                raw = response.read()
                receipt_time = dt.datetime.now(UTC)
            digest = hashlib.sha256(raw).hexdigest()
            raw_name = f"{digest}.json"
            path = raw_dir / raw_name
            if not path.exists():
                path.write_bytes(raw)
            payload = json.loads(raw)
            records.extend(records_for_payload(product, payload, receipt_time,
                                               digest, url, "raw/" + raw_name))
    # Avoid overwrite: each run gets a new unique receipt file.
    import uuid
    destination = receipts_dir / (now.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex + ".jsonl")
    with destination.open("x", encoding="utf-8") as stream:
        for item in records:
            stream.write(json.dumps(item, sort_keys=True, allow_nan=False) + "\n")
    if not records:
        raise RuntimeError("NOAA returned no acceptable observations; inspect raw responses")
    return destination, len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    path, count = collect(args.out_dir)
    print(f"Collected {count} provisional NWCL1 observation receipts in {path}")
    print("Not a successful live-feed verification until the source endpoint is tested.")


if __name__ == "__main__":
    main()
