"""Deterministic spatial aggregation tests; no internet or GRIB fixtures required."""
import pathlib
import json
import importlib.util
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import collect_mrms_basin_qpe as mrms
from validate_forcing_archive import validate


def rectangle(west, south, east, north):
    return {"type": "Polygon", "coordinates": [[
        [west, south], [east, south], [east, north], [west, north], [west, south]
    ]]}


class TestMRMSBasinAggregation(unittest.TestCase):
    def test_fetch_captures_provider_revision_headers(self):
        class Response:
            status = 200
            headers = {"Date": "Sun, 25 Oct 2026 12:05:00 GMT",
                       "Last-Modified": "Sun, 25 Oct 2026 12:04:00 GMT", "ETag": '"abc"'}

            def read(self):
                return b"grid"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        body, received, date, modified, etag, status, attempts = mrms._fetch_source(
            "https://example.invalid/data", lambda request, timeout: Response())
        self.assertEqual(body, b"grid")
        self.assertIsNotNone(received.tzinfo)
        self.assertEqual((date, modified, etag, status, attempts),
                         ("Sun, 25 Oct 2026 12:05:00 GMT", "Sun, 25 Oct 2026 12:04:00 GMT", '"abc"', 200, 1))

    def test_polygon_mean_uses_valid_cell_area_weights(self):
        result = mrms.aggregate_grid(
            values=[[10.0, 10.0], [20.0, 20.0]],
            latitudes=[[0.0, 0.0], [60.0, 60.0]],
            longitudes=[[0.5, 1.5], [0.5, 1.5]],
            geometry=rectangle(0.0, -1.0, 2.0, 61.0),
        )
        self.assertAlmostEqual(result["mean_mm"], 40 / 3, places=5)
        self.assertEqual(result["expected_cell_count"], 4)
        self.assertEqual(result["valid_cell_count"], 4)
        self.assertEqual(result["coverage_fraction"], 1.0)

    def test_negative_sentinels_and_nan_are_missing_not_zero_rain(self):
        result = mrms.aggregate_grid(
            values=[[0.0, -3.0, float("nan")], [-3.0, float("nan"), -3.0]],
            latitudes=[[0.25, 0.25, 0.25], [0.75, 0.75, 0.75]],
            longitudes=[[0.5, 1.5, 2.5], [0.5, 1.5, 2.5]],
            geometry=rectangle(0.0, 0.0, 3.0, 1.0),
            min_coverage=0.1,
        )
        self.assertEqual(result["mean_mm"], 0.0)
        self.assertEqual(result["expected_cell_count"], 6)
        self.assertEqual(result["valid_cell_count"], 1)
        self.assertAlmostEqual(result["coverage_fraction"], 1 / 6)

    def test_coverage_below_gate_is_reported_without_a_mean(self):
        result = mrms.aggregate_grid(
            values=[[1.0, -3.0], [-3.0, -3.0]],
            latitudes=[[0.25, 0.25], [0.75, 0.75]],
            longitudes=[[0.5, 1.5], [0.5, 1.5]],
            geometry=rectangle(0.0, 0.0, 2.0, 1.0), min_coverage=0.8,
        )
        self.assertEqual(result["status"], "insufficient_coverage")
        self.assertIsNone(result["mean_mm"])

    def test_nonfinite_or_irregular_grid_coordinates_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "coordinate"):
            mrms.aggregate_grid(values=[[1.0]], latitudes=[[float("nan")]],
                                longitudes=[[0.5]], geometry=rectangle(0, 0, 1, 1))

    def test_one_hour_accumulation_contract_is_strict(self):
        self.assertEqual(mrms.validate_accumulation_period("accum", "0-1"), 3600)
        for kind, step_range in (("avg", "0-1"), ("accum", "0-2"), ("instant", "0-1"), ("accum", None)):
            with self.subTest(kind=kind, step_range=step_range):
                with self.assertRaises(ValueError):
                    mrms.validate_accumulation_period(kind, step_range)

    def test_incremental_rainfall_uses_area_weighted_volume_difference(self):
        self.assertAlmostEqual(mrms.incremental_basin_mean(20.0, 100.0, 10.0, 60.0), 35.0)
        with self.assertRaisesRegex(ValueError, "nested"):
            mrms.incremental_basin_mean(20.0, 50.0, 10.0, 60.0)

    @unittest.skipUnless(importlib.util.find_spec("shapely"), "optional MRMS geometry dependency")
    def test_nonnested_live_nldi_basins_emit_only_individual_aggregates(self):
        class Response:
            status = 200
            headers = {"Date": "Sun, 25 Oct 2026 13:05:00 GMT"}

            def __init__(self, body): self.body = body
            def read(self): return self.body
            def __enter__(self): return self
            def __exit__(self, *args): return False

        maul = rectangle(0.0, 0.0, 2.0, 2.0)
        den = rectangle(1.0, 0.0, 3.0, 2.0)
        payloads = {
            mrms.NLDI_URLS["MAUL1"]: json.dumps({"type": "Feature", "properties": {}, "geometry": maul}).encode(),
            mrms.NLDI_URLS["DENL1"]: json.dumps({"type": "Feature", "properties": {}, "geometry": den}).encode(),
            mrms.PRODUCT_URL: b"synthetic grib source",
        }

        def opener(request, timeout=30):
            return Response(payloads[request.full_url])

        decoded = ([[1.0] * 7, [1.0] * 7],
                   [[0.5] * 7, [1.5] * 7],
                   [[0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25]] * 2,
                   "2026-10-25T13:00:00Z", "2026-10-25T12:00:00Z",
                   {"grid_type": "regular_ll", "generating_process": 42})
        with patch.object(mrms, "_decode_mrms", return_value=decoded):
            report, rows, raw_geometries = mrms._acquire(opener)
        self.assertEqual(report["status"], "partial", report.get("error"))
        self.assertEqual(report["incremental_basin_status"], "withheld_nldi_basins_not_nested")
        self.assertAlmostEqual(report["basin_relationship"]["denl1_fraction_inside_maul1"], 0.5)
        self.assertEqual({row["station_id"] for row in rows}, {
            "MRMS-MAUL1-UPSTREAM-BASIN", "MRMS-DENL1-UPSTREAM-BASIN"})
        self.assertEqual(len(raw_geometries), 2)

        # A topology sliver below the documented limit is clipped to the
        # downstream outline before forming the incremental catchment.
        near_den = rectangle(0.0, 0.0, 1.5, 2.00001)
        payloads[mrms.NLDI_URLS["DENL1"]] = json.dumps({
            "type": "Feature", "properties": {}, "geometry": near_den}).encode()
        with patch.object(mrms, "_decode_mrms", return_value=decoded):
            near_report, near_rows, _ = mrms._acquire(opener)
        self.assertEqual(near_report["incremental_basin_status"], "available_with_small_geometry_tolerance")
        self.assertLessEqual(near_report["basin_relationship"]["denl1_fraction_outside_maul1"],
                             mrms.MAX_DENL1_OUTSIDE_MAUL1_FRACTION)
        self.assertEqual(near_report["status"], "success", near_report.get("error"))
        self.assertIn("MRMS-MAUL1-BELOW-DENL1-BASIN", {row["station_id"] for row in near_rows})

    def test_basin_receipt_preserves_interval_grid_and_geometry_provenance(self):
        summary = {"status": "success", "mean_mm": 2.25, "valid_cell_count": 8,
                   "expected_cell_count": 10, "coverage_fraction": 0.8,
                   "area_km2": 120.0, "grid_type": "regular_ll",
                   "cell_area_weighting": "cos(latitude) × regular angular cell area",
                   "boundary_method": "grid-center inclusion", "grid_spacing_degrees": {"latitude": 0.01, "longitude": 0.01}}
        row = mrms.to_receipt("MRMS-MAUL1-UPSTREAM-BASIN", summary,
                              "2026-10-25T12:00:00Z", "2026-10-25T13:05:00Z",
                              "digest", "https://example.invalid/latest", "geometry-digest",
                              "Sun, 25 Oct 2026 13:05:00 GMT", {"version": "fixture"},
                              "Sun, 25 Oct 2026 13:04:00 GMT", '"etag"')
        validate(row)
        self.assertEqual(row["unit"], "mm")
        self.assertEqual(row["measurement_semantics"], "one_hour_accumulation")
        self.assertEqual(row["valid_start"], "2026-10-25T12:00:00Z")
        self.assertEqual(row["valid_time"], "2026-10-25T13:00:00Z")
        self.assertEqual(row["raw_sha256"], "digest")
        self.assertEqual(row["source_metadata"]["geometry_sha256"], "geometry-digest")
        self.assertEqual(row["provider_last_modified"], "Sun, 25 Oct 2026 13:04:00 GMT")
        self.assertEqual(row["provider_etag"], '"etag"')


if __name__ == "__main__":
    unittest.main()
