"""Archive research-only MRMS hourly basin rainfall aggregates.

The full gridded source is downloaded to memory and never committed. Receipts
keep the aggregate, grid coverage, NLDI geometry hash, provider timestamps and
the exact compressed-source hash. No forecast consumes this archive.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
import re
import tempfile
import urllib.request
from typing import Any

from collect_nwcl1_forcing import UTC, USER_AGENT, append_receipts, iso, write_immutable_raw
from validate_forcing_archive import validate

PRODUCT = "MultiSensor_QPE_01H_Pass2"
PRODUCT_URL = f"https://mrms.ncep.noaa.gov/2D/{PRODUCT}/MRMS_{PRODUCT}.latest.grib2.gz"
NLDI_URLS = {
    "MAUL1": "https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-07380215/basin?f=json",
    "DENL1": "https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-07378500/basin?f=json",
}
MIN_GRID_COVERAGE = 0.80
MAX_DENL1_OUTSIDE_MAUL1_FRACTION = 0.001
USER_AGENT_MRMS = USER_AGENT.replace("observation-archive", "rainfall-archive")


def _fetch_source(url: str, opener=None, attempts: int = 3) -> tuple[bytes, dt.datetime, str | None, str | None, str | None, int, int]:
    """Fetch source bytes while retaining provider revision and content headers."""
    opener = opener or urllib.request.urlopen
    last_error = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT_MRMS, "Accept-Encoding": "gzip"})
        try:
            with opener(request, timeout=30) as response:
                body = response.read()
                headers = response.headers
                date = headers.get("Date")
                return (body, dt.datetime.now(UTC), date,
                        headers.get("Last-Modified"), headers.get("ETag"),
                        int(getattr(response, "status", 200)), attempt)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"failed to fetch {url} after {attempts} attempts: {last_error}")


def validate_accumulation_period(step_type: str | None, step_range: str | None) -> int:
    """Accept only the documented 0–1 hour accumulated QPE interval."""
    if str(step_type or "").lower() not in {"accum", "accumulation"}:
        raise ValueError(f"unsupported MRMS step type {step_type!r}; expected accumulation")
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)[-–](\d+(?:\.\d+)?)\s*", str(step_range or ""))
    if not match:
        raise ValueError(f"missing or malformed MRMS accumulation step range {step_range!r}")
    start, end = map(float, match.groups())
    if start != 0.0 or end != 1.0:
        raise ValueError(f"MRMS step range {step_range!r} is not a 0–1 hour accumulation")
    return 3600


def incremental_basin_mean(outer_mean: float, outer_area_km2: float,
                           inner_mean: float, inner_area_km2: float) -> float:
    """Recover area-mean precipitation in a nested outer-minus-inner basin."""
    if not all(math.isfinite(x) for x in (outer_mean, outer_area_km2, inner_mean, inner_area_km2)):
        raise ValueError("basin means and areas must be finite")
    increment = outer_area_km2 - inner_area_km2
    if inner_area_km2 <= 0 or increment <= 0:
        raise ValueError("basins are not nested with a positive incremental area")
    value = (outer_mean * outer_area_km2 - inner_mean * inner_area_km2) / increment
    if not math.isfinite(value) or value < -1e-8:
        raise ValueError("nested-basin volume difference is invalid")
    return max(0.0, value)


def _polygon_rings(geometry: dict) -> list[list[list[float]]]:
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "Polygon" and isinstance(coords, list):
        return coords
    if kind == "MultiPolygon" and isinstance(coords, list):
        return [ring for polygon in coords for ring in polygon]
    raise ValueError("NLDI basin geometry must be Polygon or MultiPolygon")


def _geometry_bounds(geometry: Any) -> tuple[float, float, float, float]:
    if isinstance(geometry, dict):
        points = [point for ring in _polygon_rings(geometry) for point in ring]
        return (min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points))
    bounds = getattr(geometry, "bounds", None)
    if bounds is None or len(bounds) != 4:
        raise ValueError("invalid basin geometry bounds")
    return tuple(float(x) for x in bounds)


def _point_on_segment(x: float, y: float, a: list[float], b: list[float]) -> bool:
    cross = (x - a[0]) * (b[1] - a[1]) - (y - a[1]) * (b[0] - a[0])
    if abs(cross) > 1e-10:
        return False
    return min(a[0], b[0]) - 1e-10 <= x <= max(a[0], b[0]) + 1e-10 and min(a[1], b[1]) - 1e-10 <= y <= max(a[1], b[1]) + 1e-10


def _ring_contains(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        if _point_on_segment(x, y, a, b):
            return True
        if (a[1] > y) != (b[1] > y):
            crossing_x = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < crossing_x:
                inside = not inside
    return inside


def _geojson_contains(geometry: dict, x: float, y: float) -> bool:
    rings = _polygon_rings(geometry)
    # Polygon rings are outer boundary followed by holes. MultiPolygon rings
    # are flattened, so the no-hole fast path is preferred for NLDI basins.
    if geometry["type"] == "MultiPolygon":
        for polygon in geometry["coordinates"]:
            if _ring_contains(x, y, polygon[0]) and not any(_ring_contains(x, y, hole) for hole in polygon[1:]):
                return True
        return False
    return _ring_contains(x, y, rings[0]) and not any(_ring_contains(x, y, hole) for hole in rings[1:])


def _contains_mask(geometry: Any, lons, lats):
    """Use Shapely's vectorized C path in acquisition; retain a pure test fallback."""
    try:
        import numpy as np
        from shapely import contains_xy
        from shapely.geometry import shape
        geom = shape(geometry) if isinstance(geometry, dict) else geometry
        return contains_xy(geom, lons, lats)
    except ImportError:
        import numpy as np
        if not isinstance(geometry, dict):
            raise RuntimeError("Shapely is required for basin polygon aggregation")
        return np.asarray([[_geojson_contains(geometry, float(x), float(y))
                            for x, y in zip(lon_row, lat_row)]
                           for lon_row, lat_row in zip(lons, lats)], dtype=bool)


def _regular_axis(axis, label: str):
    import numpy as np
    axis = np.asarray(axis, dtype=float)
    if axis.ndim != 1 or len(axis) < 2 or not np.all(np.isfinite(axis)):
        raise ValueError(f"MRMS {label} coordinate must be a finite regular axis")
    differences = np.diff(axis)
    step = float(np.median(np.abs(differences)))
    if step <= 0 or not np.allclose(np.abs(differences), step, rtol=1e-3, atol=1e-6):
        raise ValueError(f"MRMS {label} coordinate is not regularly spaced")
    return axis, step


def aggregate_grid(values, latitudes, longitudes, geometry: Any,
                   min_coverage: float = MIN_GRID_COVERAGE,
                   grid_type: str = "regular_ll") -> dict:
    """Compute a cell-area-weighted mean for valid grid centers in a basin.

    Only the regular latitude/longitude grid contract is accepted. Cell area
    varies with latitude, so cos(latitude) weights are used when latitude and
    longitude spacing are uniform. Basin-edge cell fractions are approximated
    by cell-center inclusion and coverage is reported explicitly.
    """
    import numpy as np
    if not 0.0 < min_coverage <= 1.0:
        raise ValueError("minimum coverage must be in (0, 1]")
    if grid_type != "regular_ll":
        raise ValueError(f"unsupported MRMS grid type {grid_type!r}; expected regular_ll")
    field = np.asarray(values, dtype=float)
    lat = np.asarray(latitudes, dtype=float)
    lon = np.asarray(longitudes, dtype=float)
    if field.ndim != 2:
        raise ValueError("MRMS QPE field must be a 2-D grid")
    if lat.ndim == lon.ndim == 1:
        lat_axis, dy = _regular_axis(lat, "latitude")
        lon_axis, dx = _regular_axis(lon, "longitude")
        if field.shape != (len(lat_axis), len(lon_axis)):
            raise ValueError("MRMS coordinate axes do not match QPE grid shape")
        lon_grid, lat_grid = np.meshgrid(lon_axis, lat_axis)
    elif lat.ndim == lon.ndim == 2 and lat.shape == lon.shape == field.shape:
        if not (np.allclose(lat, lat[:, :1], rtol=0, atol=1e-5) and
                np.allclose(lon, lon[:1, :], rtol=0, atol=1e-5)):
            raise ValueError("MRMS grid coordinates are not a regular latitude/longitude grid")
        lat_axis, dy = _regular_axis(lat[:, 0], "latitude")
        lon_axis, dx = _regular_axis(lon[0, :], "longitude")
        lon_grid, lat_grid = lon, lat
    else:
        raise ValueError("MRMS latitude/longitude coordinates do not match the QPE grid")
    if not np.all(np.isfinite(lat_grid)) or not np.all(np.isfinite(lon_grid)):
        raise ValueError("MRMS grid contains nonfinite coordinate values")
    west, south, east, north = _geometry_bounds(geometry)
    row_mask = (lat_axis >= south - dy / 2) & (lat_axis <= north + dy / 2)
    col_mask = (lon_axis >= west - dx / 2) & (lon_axis <= east + dx / 2)
    rows, cols = np.where(row_mask)[0], np.where(col_mask)[0]
    if not len(rows) or not len(cols):
        raise ValueError("MRMS grid does not intersect basin geometry")
    r0, r1, c0, c1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    basin_lons, basin_lats = lon_grid[r0:r1, c0:c1], lat_grid[r0:r1, c0:c1]
    basin_values = field[r0:r1, c0:c1]
    inside = _contains_mask(geometry, basin_lons, basin_lats)
    expected_count = int(np.count_nonzero(inside))
    if expected_count == 0:
        raise ValueError("no MRMS cell centers intersect basin geometry")
    valid = inside & np.isfinite(basin_values) & (basin_values >= 0)
    valid_count = int(np.count_nonzero(valid))
    coverage = valid_count / expected_count
    result = {"status": "success" if coverage >= min_coverage else "insufficient_coverage",
              "mean_mm": None, "expected_cell_count": expected_count,
              "valid_cell_count": valid_count, "invalid_cell_count": expected_count - valid_count,
              "coverage_fraction": coverage, "grid_type": grid_type,
              "grid_spacing_degrees": {"latitude": dy, "longitude": dx},
              "cell_area_weighting": "cos(latitude) × regular angular cell area",
              "boundary_method": "grid-center inclusion; no fractional boundary-cell weighting"}
    if valid_count and coverage >= min_coverage:
        weights = np.cos(np.deg2rad(basin_lats[valid])) * math.radians(dx) * math.radians(dy)
        result["mean_mm"] = float(np.sum(basin_values[valid] * weights) / np.sum(weights))
    return result


def _geometry_area_km2(geometry) -> float:
    from pyproj import Geod
    from shapely.geometry import shape
    geom = shape(geometry) if isinstance(geometry, dict) else geometry
    area, _ = Geod(ellps="WGS84").geometry_area_perimeter(geom)
    return abs(float(area)) / 1_000_000.0


def _valid_time_iso(value) -> str:
    stamp = dt.datetime.fromisoformat(str(value).split(".")[0].replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    return iso(stamp)


def to_receipt(station_id: str, summary: dict, valid_start: str, retrieved_at: str,
               raw_sha256: str, provider_url: str, geometry_sha256: str,
               provider_http_date: str | None = None, product_metadata: dict | None = None,
               provider_last_modified: str | None = None, provider_etag: str | None = None) -> dict:
    """Map one area aggregate into the existing forcing-1 receipt schema."""
    if summary.get("status") != "success" or summary.get("mean_mm") is None:
        raise ValueError("only coverage-qualified basin aggregates can become receipts")
    start = dt.datetime.fromisoformat(valid_start.replace("Z", "+00:00"))
    if start.tzinfo is None:
        raise ValueError("valid_start must be timezone-aware")
    start = start.astimezone(UTC)
    end = start + dt.timedelta(hours=1)
    retrieved = dt.datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    if retrieved.tzinfo is None or retrieved < end:
        raise ValueError("receipt time must be timezone-aware and after valid interval end")
    product_metadata = product_metadata or {}
    row = {"schema_version": "forcing-1", "record_type": "observation",
           "station_id": station_id, "source": f"NOAA MRMS {PRODUCT}",
           "sensor_id": f"MRMS-{PRODUCT}-{product_metadata.get('version', 'version-unknown')}",
           "variable": "precipitation", "unit": "mm", "datum": "not_applicable",
           "valid_time": iso(end), "valid_start": iso(start), "valid_end": iso(end),
           "retrieved_at": iso(retrieved), "provider_http_date": provider_http_date,
           "provider_last_modified": provider_last_modified, "provider_etag": provider_etag,
           "value": float(summary["mean_mm"]), "status": "provisional", "parameter_code": PRODUCT,
           "measurement_semantics": "one_hour_accumulation", "accumulation_period_seconds": 3600,
           "raw_id": f"mrms:{PRODUCT}:{station_id}:{iso(end)}:{raw_sha256}",
           "qc_flags": [f"valid_cell_coverage:{summary['coverage_fraction']:.6f}"],
           "product": PRODUCT, "product_version": product_metadata.get("version"),
           "provider_url": provider_url, "raw_sha256": raw_sha256,
           "raw_archive_policy": "content hash retained; full continental grid not committed",
           "source_metadata": {"geometry_sha256": geometry_sha256,
                               "valid_grid_cells": summary["valid_cell_count"],
                               "expected_grid_cells": summary["expected_cell_count"],
                               "coverage_fraction": summary["coverage_fraction"],
                               "cell_area_weighting": summary["cell_area_weighting"],
                               "boundary_method": summary["boundary_method"],
                               "grid_type": summary["grid_type"],
                               "grid_spacing_degrees": summary["grid_spacing_degrees"],
                               "area_km2": summary["area_km2"],
                               "provider_interval": "00:00–01:00 hour accumulation; valid_time is interval end"}}
    validate(row)
    return row


def _extract_feature(payload: dict) -> dict:
    if payload.get("type") == "Feature":
        return payload
    if payload.get("type") == "FeatureCollection" and len(payload.get("features", [])) == 1:
        return payload["features"][0]
    raise ValueError("NLDI basin response must contain exactly one GeoJSON feature")


def _decode_mrms(body: bytes) -> tuple[Any, Any, Any, str, str, dict]:
    """Decode one compressed GRIB2 message using optional, research-only libs."""
    import cfgrib
    import numpy as np
    try:
        import xarray  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("xarray is required by cfgrib") from exc
    raw = gzip.decompress(body)
    with tempfile.NamedTemporaryFile(suffix=".grib2") as temp:
        temp.write(raw)
        temp.flush()
        datasets = cfgrib.open_datasets(temp.name, backend_kwargs={"indexpath": ""})
        try:
            candidates = [(dataset, name, dataset[name]) for dataset in datasets
                          for name in dataset.data_vars if dataset[name].ndim == 2]
            if len(candidates) != 1:
                raise ValueError(f"expected one 2-D MRMS field, found {len(candidates)}")
            dataset, name, field = candidates[0]
            attrs = dict(field.attrs)
            units = str(attrs.get("units") or attrs.get("GRIB_units") or "").strip().lower().replace("**", "^")
            if units not in {"mm", "kg m^-2", "kg m-2", "kg/m^2"}:
                raise ValueError(f"unsupported MRMS QPE units {attrs.get('units')!r}; "
                                 f"GRIB_units={attrs.get('GRIB_units')!r}; field={name!r}; attrs={attrs!r}")
            period = validate_accumulation_period(attrs.get("GRIB_stepType"), attrs.get("GRIB_stepRange"))
            valid_coord = dataset.coords.get("valid_time")
            if valid_coord is None:
                valid_coord = dataset.coords.get("time")
            if valid_coord is None:
                raise ValueError("MRMS GRIB has no valid-time coordinate")
            valid_end = _valid_time_iso(np.asarray(valid_coord.values).reshape(-1)[0])
            start = dt.datetime.fromisoformat(valid_end.replace("Z", "+00:00")) - dt.timedelta(seconds=period)
            lat = dataset.coords.get("latitude")
            lon = dataset.coords.get("longitude")
            if lat is None or lon is None:
                raise ValueError("MRMS GRIB has no latitude/longitude grid coordinates")
            grid_type = str(attrs.get("GRIB_gridType") or dataset.attrs.get("GRIB_gridType") or "")
            metadata = {"field_name": name, "provider_units": attrs.get("units") or attrs.get("GRIB_units"),
                        "step_type": attrs.get("GRIB_stepType"), "step_range": attrs.get("GRIB_stepRange"),
                        "grid_type": grid_type, "long_name": attrs.get("long_name"),
                        "generating_process": attrs.get("GRIB_generatingProcessIdentifier"),
                        "period_seconds": period}
            field_values = np.asarray(field.values, dtype=float)
            if units != "mm":
                # One kg m-2 liquid-water equivalent is one millimeter.
                field_values = field_values.copy()
            return field_values, np.asarray(lat.values), np.asarray(lon.values), valid_end, iso(start), metadata
        finally:
            for dataset in datasets:
                dataset.close()


def _area_summary(geometry, aggregation: dict) -> dict:
    return {**aggregation, "area_km2": _geometry_area_km2(geometry)}


def _acquire(opener=None) -> tuple[dict, list[dict], list[tuple[bytes, str]]]:
    opener = opener or __import__("urllib.request", fromlist=["urlopen"]).urlopen
    started = dt.datetime.now(UTC)
    report = {"schema_version": "mrms-basin-run-1", "status": "failed",
              "product": PRODUCT, "product_url": PRODUCT_URL, "started_at": iso(started),
              "basins": [], "source_status": [], "receipts": 0}
    rows, raw_geometries = [], []
    try:
        geometries, geometry_hashes = {}, {}
        for name, url in NLDI_URLS.items():
            body, received, server_date, last_modified, etag, status, attempts = _fetch_source(url, opener)
            if status != 200:
                raise RuntimeError(f"NLDI {name} returned HTTP {status}")
            payload = json.loads(body)
            feature = _extract_feature(payload)
            geometry = feature.get("geometry")
            if not geometry:
                raise ValueError(f"NLDI {name} response lacks a basin geometry")
            from shapely.geometry import shape
            geom = shape(geometry)
            if geom.is_empty or not geom.is_valid:
                raise ValueError(f"NLDI {name} geometry is empty or invalid")
            geometries[name] = geom
            digest = hashlib.sha256(body).hexdigest()
            geometry_hashes[name] = digest
            raw_geometries.append((body, f"NLDI {name}"))
            report["source_status"].append({"source": f"USGS NLDI basin {name}", "status": "success",
                                             "url": url, "http_status": status,
                                             "retrieved_at": iso(received), "provider_http_date": server_date,
                                             "last_modified": last_modified, "etag": etag,
                                             "attempts": attempts, "raw_sha256": digest,
                                             "feature_properties": feature.get("properties", {})})
        maul = geometries["MAUL1"]
        den = geometries["DENL1"]
        overlap = maul.intersection(den)
        nesting = {
            "maul1_area_km2": _geometry_area_km2(maul),
            "denl1_area_km2": _geometry_area_km2(den),
            "intersection_area_km2": _geometry_area_km2(overlap),
            "denl1_fraction_inside_maul1": (overlap.area / den.area if den.area else 0.0),
            "denl1_fraction_outside_maul1": (1.0 - overlap.area / den.area if den.area else 1.0),
            "maul1_fraction_inside_denl1": (overlap.area / maul.area if maul.area else 0.0),
            "maximum_denl1_outside_fraction": MAX_DENL1_OUTSIDE_MAUL1_FRACTION,
            "method": "NLDI polygon intersection; planar overlap fraction in shared GeoJSON coordinate system",
        }
        report["basin_relationship"] = nesting
        nested = nesting["denl1_fraction_outside_maul1"] <= MAX_DENL1_OUTSIDE_MAUL1_FRACTION
        # Clip the upstream polygon to the downstream outline before differencing;
        # tolerated coordinate/topology slivers cannot subtract area outside MAUL1.
        clipped_den = overlap if nested else None
        incremental = maul.difference(clipped_den) if clipped_den is not None else None
        if incremental is not None and (incremental.is_empty or not incremental.is_valid):
            incremental = None
            nested = False
        report["incremental_basin_status"] = (
            "available_with_small_geometry_tolerance" if nested else "withheld_nldi_basins_not_nested")

        body, received, server_date, last_modified, etag, status, attempts = _fetch_source(PRODUCT_URL, opener)
        if status != 200:
            raise RuntimeError(f"MRMS product returned HTTP {status}")
        digest = hashlib.sha256(body).hexdigest()
        mrms_source = {"source": f"NOAA MRMS {PRODUCT}", "status": "downloaded_unvalidated",
                       "url": PRODUCT_URL, "http_status": status,
                       "retrieved_at": iso(received), "provider_http_date": server_date,
                       "last_modified": last_modified, "etag": etag, "attempts": attempts,
                       "raw_sha256": digest, "raw_bytes": len(body)}
        report["source_status"].append(mrms_source)
        values, latitudes, longitudes, valid_end, valid_start, metadata = _decode_mrms(body)
        if metadata["grid_type"] != "regular_ll":
            raise ValueError(f"MRMS grid type {metadata['grid_type']!r} is not supported")
        mrms_source.update(status="success", valid_start=valid_start, valid_end=valid_end,
                           product_metadata=metadata)
        geom_map = {"MRMS-MAUL1-UPSTREAM-BASIN": (maul, "MAUL1"),
                    "MRMS-DENL1-UPSTREAM-BASIN": (den, "DENL1")}
        if incremental is not None:
            geom_map["MRMS-MAUL1-BELOW-DENL1-BASIN"] = (incremental, "incremental")
        for station_id, (geom, label) in geom_map.items():
            result = aggregate_grid(values, latitudes, longitudes, geom, grid_type=metadata["grid_type"])
            result = _area_summary(geom, result)
            item = {"station_id": station_id, **result, "geometry_sha256": geometry_hashes["MAUL1"] if label != "DENL1" else geometry_hashes["DENL1"]}
            report["basins"].append(item)
            if result["status"] != "success":
                continue
            geometry_hash = item["geometry_sha256"]
            if label == "incremental":
                geometry_hash = hashlib.sha256((geometry_hashes["MAUL1"] + geometry_hashes["DENL1"]).encode()).hexdigest()
            row = to_receipt(station_id, result, valid_start, iso(received), digest, PRODUCT_URL,
                             geometry_hash, server_date,
                             {"version": str(metadata.get("generating_process") or "metadata-unspecified"),
                              **metadata}, last_modified, etag)
            row["source_metadata"].update({"nldi_feature_ids": ["USGS-07380215", "USGS-07378500"] if label == "incremental" else ["USGS-07380215" if label == "MAUL1" else "USGS-07378500"],
                                           "nldi_geometry_sha256": geometry_hash})
            validate(row)
            rows.append(row)
        required_basin_rows = {row["station_id"] for row in rows} >= {
            "MRMS-MAUL1-UPSTREAM-BASIN", "MRMS-DENL1-UPSTREAM-BASIN"}
        report.update(status="success" if len(rows) == 3 else "partial", completed_at=iso(dt.datetime.now(UTC)),
                      product_sha256=digest, valid_start=valid_start, valid_end=valid_end,
                      records_prepared=len(rows), provider_http_date=server_date)
        if len(rows) != 3:
            report["error"] = ("incremental basin withheld because NLDI polygons were not nested"
                                if not nested else
                                "one or more basin coverage gates failed; complete three-basin set not prepared")
        if not required_basin_rows:
            rows = []
    except Exception as exc:
        report.update(status="failed", completed_at=iso(dt.datetime.now(UTC)),
                      error=f"{type(exc).__name__}: {exc}")
        rows = []
    return report, rows, raw_geometries


def collect(out_dir, opener=None) -> dict:
    """Collect one MRMS hour; source failure remains health data, not core-feed failure."""
    out = pathlib.Path(out_dir)
    for directory in (out / "raw", out / "receipts", out / "health"):
        directory.mkdir(parents=True, exist_ok=True)
    report, rows, raw_geometries = _acquire(opener)
    for body, _source in raw_geometries:
        write_immutable_raw(out / "raw", body)
    if rows:
        receipt_path, count = append_receipts(out / "receipts", rows)
        report["receipt_file"] = str(receipt_path) if receipt_path else None
        report["records_added"] = count
    else:
        report["receipt_file"] = None
        report["records_added"] = 0
    run_id = dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-mrms-" + hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()[:8]
    report["run_id"] = run_id
    health = out / "health" / f"{run_id}.json"
    with health.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return report


def live_smoke(opener=None) -> dict:
    """Fetch and validate one current product without writing archive files."""
    report, rows, _ = _acquire(opener)
    report["records_prepared"] = len(rows)
    report["live_smoke_success"] = (
        report.get("status") in {"success", "partial"} and
        {row.get("station_id") for row in rows} >= {
            "MRMS-MAUL1-UPSTREAM-BASIN", "MRMS-DENL1-UPSTREAM-BASIN"})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=pathlib.Path, default=pathlib.Path("research/prospective-forcing-archive"))
    parser.add_argument("--live-smoke", action="store_true", help="verify a current MRMS grid and NLDI geometry without persisting")
    args = parser.parse_args()
    if args.live_smoke:
        report = live_smoke()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("live_smoke_success") else 2
    report = collect(args.out_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    # MRMS is an optional research feed: persist health state without blocking
    # the established NOAA/USGS receipt collector.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
