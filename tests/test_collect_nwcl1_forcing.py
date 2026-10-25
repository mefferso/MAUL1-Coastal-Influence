"""Deterministic tests for NWCL1 receipt ingestion; no internet or fake published archive."""
import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import collect_nwcl1_forcing as collector

UTC = dt.timezone.utc


class TestNWCL1Collector(unittest.TestCase):
    def setUp(self):
        self.received = dt.datetime(2026, 10, 25, 13, 0, tzinfo=UTC)

    def test_wind_from_east_produces_westward_u(self):
        payload = {"data": [{"t": "2026-10-25 12:00", "s": "20", "d": "90", "f": "0"}]}
        rows = collector.records_for_payload("wind", payload, self.received, "digest", "url", "raw/x")
        self.assertEqual(len(rows), 4)
        by_var = {r["variable"]: r for r in rows}
        self.assertAlmostEqual(by_var["wind_u"]["value"], -20)
        self.assertAlmostEqual(by_var["wind_v"]["value"], 0, places=5)
        self.assertEqual(by_var["wind_speed"]["value"], 20)
        self.assertEqual(by_var["wind_direction"]["value"], 90)
        self.assertEqual(by_var["wind_u"]["retrieved_at"], "2026-10-25T13:00:00Z")

    def test_future_time_skipped(self):
        payload = {"data": [{"t": "2026-10-25 14:00", "v": "2.1"}]}
        self.assertEqual(collector.records_for_payload("water_level", payload, self.received, "digest", "url", "raw/x"), [])

    def test_water_datum_explicit(self):
        payload = {"data": [{"t": "2026-10-25 12:00", "v": "2.1"}]}
        rows = collector.records_for_payload("water_level", payload, self.received, "digest", "url", "raw/x")
        self.assertEqual(rows[0]["datum"], "MLLW")

    def test_provider_errors_rejected(self):
        with self.assertRaises(ValueError):
            collector.records_for_payload("wind", {"error": "unavailable"}, self.received, "d", "u", "p")

    def test_tide_predictions_allow_future_times_and_keep_datum(self):
        p = {"predictions": [{"t": "2026-10-25 14:00", "v": "2.1"}]}
        rows = collector.noaa_records("predictions", p, self.received, "d", "u", "raw/x")
        self.assertEqual(rows[0]["record_type"], "prediction")
        self.assertEqual(rows[0]["datum"], "MLLW")

    def test_usgs_keeps_native_stage_separate_from_navd88(self):
        data = {"features": [{"properties": {"monitoring_location_id": "USGS-07380215",
                "parameter_code": "00065", "time": "2026-10-25T12:00:00Z", "value": "3.2",
                "unit_of_measure": "ft", "approval_status": "approved"}},
                {"properties": {"monitoring_location_id": "USGS-07380215", "parameter_code": "63160",
                "time": "2026-10-25T12:00:00Z", "value": "-1.2", "unit_of_measure": "ft",
                "approval_status": "approved"}}]}
        rows = collector.usgs_records(data, self.received, "d", "url", "raw/x")
        self.assertEqual([x["datum"] for x in rows], ["native_gage_datum:USGS-07380215", "NAVD88"])

    def test_usgs_cubic_feet_unit_from_live_ogc_spelling_is_preserved(self):
        data = {"features": [{"properties": {"monitoring_location_id": "USGS-07378500",
                "parameter_code": "00060", "time": "2026-10-25T12:00:00Z", "value": "314",
                "unit_of_measure": "ft^3/s", "approval_status": "Provisional", "qualifier": None}}]}
        row = collector.usgs_records(data, self.received, "d", "url", "raw/x")[0]
        self.assertEqual(row["unit"], "cfs")
        self.assertEqual(row["provider_unit"], "ft^3/s")
        self.assertIn("approval_status:Provisional", row["qc_flags"])

    def test_raw_payload_content_addressed_and_deduplicated(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            digest1, path1 = collector.write_immutable_raw(directory, b'{"x":1}')
            digest2, path2 = collector.write_immutable_raw(directory, b'{"x":1}')
            self.assertEqual((digest1, path1), (digest2, path2))

    def test_http_retry_records_actual_response_headers_and_attempt(self):
        class Response:
            status = 200
            headers = {"Date": "Sun, 25 Oct 2026 13:00:00 GMT"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"data": []}'
        calls = []
        def opener(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise OSError("temporary outage")
            return Response()
        waits = []
        body, receipt, date, status, attempts = collector.fetch("https://example.invalid", opener, sleeper=waits.append)
        self.assertEqual((body, date, status, attempts), (b'{"data": []}', "Sun, 25 Oct 2026 13:00:00 GMT", 200, 2))
        self.assertEqual(waits, [1])

    def test_permanent_http_error_is_not_retried(self):
        import urllib.error
        calls = []
        def opener(*args, **kwargs):
            calls.append(1)
            raise urllib.error.HTTPError("https://example.invalid", 400, "bad request", {}, None)
        with self.assertRaisesRegex(RuntimeError, "non-retryable HTTP 400"):
            collector.fetch("https://example.invalid", opener, sleeper=lambda _: None)
        self.assertEqual(len(calls), 1)

    def test_collection_health_raw_provenance_and_cross_run_deduplication(self):
        class Response:
            status = 200
            headers = {"Date": "Sun, 25 Oct 2026 13:00:00 GMT"}
            def __init__(self, payload): self.payload = payload
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps(self.payload).encode()

        def opener(request, timeout=30):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)
            if "product" in query:
                product = query["product"][0]
                if product == "wind": payload = {"data": [{"t": "2026-10-25 12:00", "s": "10", "d": "180", "f": "0"}]}
                elif product == "water_level": payload = {"data": [{"t": "2026-10-25 12:00", "v": "1.2", "f": "0"}]}
                else: payload = {"predictions": [{"t": "2026-10-25 14:00", "v": "1.4"}]}
                return Response(payload)
            station, parameter = query["monitoring_location_id"][0], query["parameter_code"][0]
            if station == "USGS-07380215" and parameter == "63160":
                return Response({"features": []})
            value = "100" if parameter == "00060" else "2.5"
            return Response({"features": [{"properties": {"monitoring_location_id": station,
                    "parameter_code": parameter, "time": "2026-10-25T12:00:00Z", "value": value,
                    "unit_of_measure": "ft3/s" if parameter == "00060" else "ft",
                    "approval_status": "approved", "time_series_id": "series-1"}}]})

        with tempfile.TemporaryDirectory() as temp:
            now = dt.datetime(2026, 10, 25, 15, 0, tzinfo=UTC)
            first = collector.collect(temp, now=now, opener=opener, sleeper=lambda _: None)
            self.assertEqual(first["critical_failures"], [])
            self.assertGreater(first["records_added"], 0)
            self.assertEqual(len(list((pathlib.Path(temp) / "raw").glob("*.json"))), 8)
            self.assertTrue((pathlib.Path(temp) / "health" / (first["run_id"] + ".json")).exists())
            self.assertEqual(next(r for r in first["sources"] if "63160" in r["source"])["status"], "empty")
            second = collector.collect(temp, now=now + dt.timedelta(minutes=1), opener=opener, sleeper=lambda _: None)
            self.assertEqual(second["records_added"], 0)


if __name__ == "__main__":
    unittest.main()

