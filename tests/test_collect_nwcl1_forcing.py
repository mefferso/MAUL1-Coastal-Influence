"""Deterministic tests for NWCL1 receipt ingestion; no internet or fake published archive."""
import datetime as dt
import hashlib
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
    def test_existing_core_feed_registry_remains_unchanged(self):
        self.assertEqual((collector.SOURCES["NWCL1"]["station"], collector.SOURCES["NWCL1"]["products"]),
                         ("8761927", ["wind", "water_level", "predictions"]))
        self.assertEqual((collector.SOURCES["DENL1"]["station"], collector.SOURCES["DENL1"]["parameters"]),
                         ("USGS-07378500", ["00060", "00065"]))
        self.assertEqual((collector.SOURCES["MDLL1"]["station"], collector.SOURCES["MDLL1"]["parameters"]),
                         ("USGS-301200090072400", ["00065"]))
        self.assertEqual((collector.SOURCES["MAUL1"]["station"], collector.SOURCES["MAUL1"]["parameters"]),
                         ("USGS-07380215", ["00065", "63160"]))
        self.assertEqual(collector.SOURCES["NWCL1"]["category"], "core")
        self.assertEqual(collector.SOURCES["KNEW"]["category"], "shadow")
        self.assertEqual(collector.SOURCES["MCHL1-USGS"]["category"], "shadow")

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

    def test_observation_collection_uses_provider_recent_window_for_recovery(self):
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlparse(collector.noaa_url("wind", "recent")).query)["date"], ["recent"])
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlparse(collector.noaa_url("predictions", "latest")).query)["date"], ["latest"])

    def test_noaa_range_and_usgs_continuous_history_urls(self):
        begin, end = dt.datetime(2026, 10, 25, tzinfo=UTC), dt.datetime(2026, 10, 31, tzinfo=UTC)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(collector.noaa_url("water_level", begin=begin, end=end)).query)
        self.assertEqual(q["begin_date"], ["20261025 00:00"])
        self.assertEqual(q["end_date"], ["20261031 00:00"])
        self.assertEqual(q["datum"], ["MLLW"])
        u = urllib.parse.parse_qs(urllib.parse.urlparse(collector.usgs_url("USGS-07380215", "63160", begin=begin, end=end)).query)
        self.assertEqual(u["time"], ["2026-10-25T00:00:00Z/2026-10-31T00:00:00Z"])
        self.assertIn("continuous", collector.usgs_url("USGS-07380215", "63160", begin=begin, end=end))

    def test_noaa_history_windows_are_bounded(self):
        windows = collector.noaa_windows(dt.datetime(2026, 1, 1, tzinfo=UTC), dt.datetime(2026, 3, 5, tzinfo=UTC))
        self.assertTrue(all(end - start <= dt.timedelta(days=31) for start, end in windows))
        self.assertEqual(windows[0][0], dt.datetime(2026, 1, 1, tzinfo=UTC))
        self.assertEqual(windows[-1][1], dt.datetime(2026, 3, 5, tzinfo=UTC))

    def test_receipt_identity_retains_provider_revisions_and_recovery_class(self):
        row = {"source":"USGS s", "station_id":"s", "variable":"gage_height", "valid_time":"2026-10-25T12:00:00Z",
               "value":1.0, "qc_flags":[], "status":"provisional", "provider_updated_at":"2026-10-25T12:01:00Z",
               "acquisition_mode":"prospective"}
        self.assertNotEqual(collector._receipt_identity(row), collector._receipt_identity({**row, "status":"observed"}))
        self.assertEqual(collector._receipt_identity(row), collector._receipt_identity({**row, "acquisition_mode":"delayed_recovery"}))

    def test_history_rows_mark_recovery_without_backdating_retrieval(self):
        valid = dt.datetime(2026, 10, 25, 12, tzinfo=UTC)
        acquired = dt.datetime(2026, 10, 25, 18, tzinfo=UTC)
        payload = {"data": [{"t":"2026-10-25 12:00", "v":"2.1"}]}
        row = collector.noaa_records("water_level", payload, acquired, "d", "u", "raw/d", acquisition_mode="delayed_recovery")[0]
        self.assertEqual(row["valid_time"], collector.iso(valid))
        self.assertEqual(row["retrieved_at"], collector.iso(acquired))
        self.assertEqual(row["acquisition_mode"], "delayed_recovery")

    def test_usgs_history_bootstrap_matches_logical_archive_station_and_parameter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            receipts=root/"receipts"; health=root/"health"
            receipts.mkdir(); health.mkdir()
            row={"source":"USGS USGS-07380215", "station_id":"MAUL1", "parameter_code":"63160",
                 "record_type":"observation", "valid_time":"2026-10-25T12:00:00Z"}
            (receipts/"a.jsonl").write_text(json.dumps(row)+"\n")
            begin=collector.history_begin(receipts, health, "USGS MAUL1 USGS-07380215 parameter 63160",
                dt.datetime(2026,10,31,tzinfo=UTC), receipt_station_id="MAUL1", parameter_code="63160")
            self.assertEqual(begin, dt.datetime(2026,10,25,12,tzinfo=UTC))

    def test_noaa_history_bootstrap_matches_product_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            receipts=root/"receipts"; health=root/"health"
            receipts.mkdir(); health.mkdir()
            row={"source":"NOAA CO-OPS 8761927", "station_id":"NWCL1", "product":"water_level",
                 "record_type":"observation", "valid_time":"2026-10-25T12:00:00Z"}
            (receipts/"a.jsonl").write_text(json.dumps(row)+"\n")
            begin=collector.history_begin(receipts, health, "NOAA CO-OPS 8761927 water_level",
                dt.datetime(2026,10,31,tzinfo=UTC), receipt_station_id="NWCL1", receipt_product="water_level")
            self.assertEqual(begin, dt.datetime(2026,10,25,12,tzinfo=UTC))

    def test_six_hour_actions_outage_recovers_intermediate_noaa_observations(self):
        start = dt.datetime(2026, 10, 31, 0, tzinfo=UTC)
        resumed = start + dt.timedelta(hours=6)
        actual_received = resumed + dt.timedelta(minutes=5)
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            old = collector.noaa_records("water_level", {"data":[{"t":"2026-10-31 00:00", "v":"1.0"}]},
                start, "old", "old-url", "raw/old.json")[0]
            collector.append_receipts(out / "receipts", [old])

            class Response:
                status=200
                headers={"Date":"Sat, 31 Oct 2026 06:00:00 GMT"}
                def __init__(self, payload): self.payload=payload
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self): return json.dumps(self.payload).encode()

            def opener(request, timeout=30):
                query=urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)
                if "ids" in query:
                    return Response([{"icaoId":"KNEW", "obsTime":int((resumed-dt.timedelta(minutes=5)).timestamp()),
                        "reportTime":"2026-10-31T05:55:00Z", "wdir":180, "wspd":5}])
                if "product" in query:
                    product=query["product"][0]
                    if product == "predictions":
                        return Response({"predictions":[{"t":"2026-10-31 06:00", "v":"1.5"}]})
                    data=[]
                    for hour in range(7):
                        t=(start+dt.timedelta(hours=hour)).strftime("%Y-%m-%d %H:%M")
                        data.append({"t":t, "s":"5", "d":"180", "f":"0"} if product=="wind" else {"t":t,"v":str(1+hour/10),"f":"0"})
                    return Response({"data":data})
                station, parameter=query["monitoring_location_id"][0],query["parameter_code"][0]
                unit="ft^3/s" if parameter=="00060" else ("in" if parameter=="00045" else "ft")
                value="100" if parameter=="00060" else ("0.01" if parameter=="00045" else "2.0")
                if station=="USGS-073802302" and parameter=="00065":
                    if "page" in query:
                        raise OSError("simulated outage on second USGS page")
                    return Response({"features":[{"properties":{"monitoring_location_id":station,
                        "parameter_code":parameter,"time":"2026-10-31T05:45:00Z","value":value,
                        "unit_of_measure":unit,"approval_status":"Provisional","time_series_id":station+parameter}}],
                        "links":[{"rel":"next","href":"?page=2"}]})
                return Response({"features":[{"properties":{"monitoring_location_id":station,"parameter_code":parameter,
                    "time":"2026-10-31T05:55:00Z","value":value,"unit_of_measure":unit,
                    "approval_status":"Provisional","time_series_id":station+parameter}}]})

            report=collector.collect(out, now=resumed, opener=opener, sleeper=lambda _:None,
                                     clock=lambda: actual_received)
            self.assertEqual(report["critical_failures"], [])
            partial=next(x for x in report["sources"] if x["source"].endswith("USGS-073802302 parameter 00065"))
            self.assertEqual(partial["status"], "failed")
            self.assertEqual(len(partial["raw_responses"]), 1)
            preserved=out/partial["raw_responses"][0]["path"]
            self.assertEqual(hashlib.sha256(preserved.read_bytes()).hexdigest(), partial["raw_responses"][0]["sha256"])
            history=next(x for x in report["sources"] if x["source"]=="NOAA CO-OPS 8761927 water_level")
            self.assertEqual(history["request_window"], "history")
            receipt_rows=[json.loads(line) for p in (out/"receipts").glob("*.jsonl") for line in p.read_text().splitlines()]
            recovered=[r for r in receipt_rows if r.get("variable")=="water_level" and r.get("station_id")=="NWCL1"]
            self.assertEqual({r["valid_time"] for r in recovered}, {f"2026-10-31T0{h}:00:00Z" for h in range(7)})
            for row in recovered:
                self.assertEqual(row["retrieved_at"], collector.iso(actual_received) if row["valid_time"] != collector.iso(start) else collector.iso(start))
                if row["valid_time"] in {"2026-10-31T01:00:00Z", "2026-10-31T02:00:00Z", "2026-10-31T03:00:00Z"}:
                    self.assertEqual(row["acquisition_mode"], "delayed_recovery")

    def test_usgs_continuous_pages_keep_each_page_raw_reference(self):
        base={"monitoring_location_id":"USGS-07380215", "parameter_code":"63160", "unit_of_measure":"ft",
              "approval_status":"Provisional", "time_series_id":"series"}
        page1 = {"features": [{"properties":{**base,"time":"2026-10-25T12:00:00Z","value":"-1.0"}}],
                 "links": [{"rel":"next", "href":"?page=2"}]}
        page2 = {"features": [{"properties":{**base,"time":"2026-10-25T12:15:00Z","value":"-0.9"}}], "links": []}
        class Response:
            status=200
            headers={"Date":"Sat, 31 Oct 2026 18:00:00 GMT"}
            def __init__(self, payload): self.payload=payload
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps(self.payload).encode()
        urls=[]
        def opener(request, timeout=30):
            urls.append(request.full_url)
            return Response(page1 if len(urls)==1 else page2)
        pages=collector.fetch_usgs_history(collector.usgs_url("USGS-07380215", "63160"), opener, clock=lambda: self.received)
        self.assertEqual(len(pages), 2)
        self.assertIn("page=2", urls[1])
        self.assertNotEqual(pages[0][1], pages[1][1])
        with tempfile.TemporaryDirectory() as tmp:
            rows=[]
            for url, body, retrieved, http_date, status, attempts, payload in pages:
                digest, path=collector.write_immutable_raw(pathlib.Path(tmp), body)
                rows.extend(collector.usgs_records(payload, retrieved, digest, url, path, http_date))
            self.assertEqual([r["valid_time"] for r in rows], ["2026-10-25T12:00:00Z", "2026-10-25T12:15:00Z"])
            self.assertEqual(len(list(pathlib.Path(tmp).glob("*.json"))), 2)

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
                "unit_of_measure": "ft^3/s", "approval_status": "Provisional", "qualifier": "A"}}]}
        row = collector.usgs_records(data, self.received, "d", "url", "raw/x")[0]
        self.assertEqual(row["unit"], "cfs")
        self.assertEqual(row["provider_unit"], "ft^3/s")
        self.assertIn("approval_status:Provisional", row["qc_flags"])
        self.assertIn("qualifier:A", row["qc_flags"])

    def test_local_usgs_registry_adds_precipitation_and_stage_without_inventing_discharge(self):
        expected = {
            "USGS-301828090363100": ["00045"],
            "USGS-07379960": ["00045", "00065"],
            "USGS-07378810": ["00045", "00065"],
            "USGS-07378746": ["00045", "00065"],
        }
        for station, parameters in expected.items():
            with self.subTest(station=station):
                self.assertEqual(collector.SOURCES[station]["station"], station)
                self.assertEqual(collector.SOURCES[station]["parameters"], parameters)
                self.assertFalse(collector.SOURCES[station]["critical"])
                self.assertNotIn("00060", collector.SOURCES[station]["parameters"])

    def test_usgs_00045_is_retained_as_accumulated_precipitation_with_provider_metadata(self):
        data = {"features": [{"properties": {
            "monitoring_location_id": "USGS-301828090363100", "parameter_code": "00045",
            "time": "2026-10-25T12:00:00Z", "value": "0.12", "unit_of_measure": "inches",
            "approval_status": "Provisional", "qualifier": "P", "time_series_id": "series-rain-1",
            "accumulation_period_seconds": 900,
        }}]}
        rows = collector.usgs_records(data, self.received, "digest", "url", "raw/digest.json")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["variable"], "precipitation")
        self.assertEqual(row["unit"], "in")
        self.assertEqual(row["provider_unit"], "inches")
        self.assertEqual(row["parameter_code"], "00045")
        self.assertEqual(row["measurement_semantics"], "reported_accumulation")
        self.assertEqual(row["accumulation_period_seconds"], 900)
        self.assertEqual(row["sensor_id"], "series-rain-1")
        self.assertEqual(row["status"], "provisional")
        self.assertIn("qualifier:P", row["qc_flags"])
        self.assertEqual(row["raw_sha256"], "digest")

    def test_usgs_00045_does_not_assume_an_accumulation_interval_or_rate(self):
        data = {"features": [{"properties": {
            "monitoring_location_id": "USGS-301828090363100", "parameter_code": "00045",
            "time": "2026-10-25T12:00:00Z", "value": "0.0", "unit_of_measure": "in",
        }}]}
        row = collector.usgs_records(data, self.received, "digest", "url", "raw/digest.json")[0]
        self.assertEqual(row["measurement_semantics"], "reported_accumulation")
        self.assertIsNone(row["accumulation_period_seconds"])
        self.assertNotIn("precipitation_rate", row["variable"])

    def test_usgs_precipitation_rejects_negative_sentinel_and_timezone_free_valid_time(self):
        base = {"monitoring_location_id": "USGS-301828090363100", "parameter_code": "00045",
                "unit_of_measure": "in", "approval_status": "Provisional"}
        payload = {"features": [
            {"properties": {**base, "time": "2026-10-25T12:00:00Z", "value": "-999"}},
            {"properties": {**base, "time": "2026-10-25T12:00:00", "value": "0.1"}},
        ]}
        self.assertEqual(collector.usgs_records(payload, self.received, "d", "u", "p"), [])
    def test_knew_awc_metar_preserves_identity_timestamp_and_wind_vector(self):
        payload = [{"icaoId": "KNEW", "obsTime": 1792929600, "reportTime": "2026-10-25T12:00:00Z",
                    "lat": 30.05, "lon": -90.03, "elev": 1, "wdir": 90, "wspd": 10, "wgst": 15,
                    "rawOb": "METAR KNEW 251200Z 09010G15KT"}]
        rows = collector.awc_wind_records(payload, self.received, "d", "url", "raw/x")
        self.assertEqual({row["variable"] for row in rows}, {"wind_speed", "wind_direction", "wind_u", "wind_v", "wind_gust"})
        by_var = {row["variable"]: row for row in rows}
        self.assertEqual(by_var["wind_speed"]["unit"], "knots")
        self.assertEqual(by_var["wind_u"]["value"], -10)
        self.assertEqual(by_var["wind_direction"]["valid_time"], "2026-10-25T12:00:00Z")
        self.assertEqual(by_var["wind_speed"]["station_id"], "KNEW")
        self.assertEqual(by_var["wind_speed"]["source_category"], "shadow")
        self.assertEqual(by_var["wind_speed"]["source_metadata"]["station_longitude"], -90.03)

    def test_awc_rejects_wrong_station_and_does_not_make_calm_direction(self):
        payload = [{"icaoId": "KMSY", "obsTime": 1792929600, "wdir": 90, "wspd": 5}]
        with self.assertRaises(ValueError):
            collector.awc_wind_records(payload, self.received, "d", "url", "raw/x")
        payload = [{"icaoId": "KNEW", "obsTime": 1792929600, "wdir": None, "wspd": 0}]
        rows = collector.awc_wind_records(payload, self.received, "d", "url", "raw/x")
        self.assertEqual([row["variable"] for row in rows], ["wind_speed"])

    def test_usgs_mchl1_stage_is_shadow_and_retains_native_datum(self):
        data = {"features": [{"properties": {"monitoring_location_id": "USGS-073802302",
                "parameter_code": "00065", "time": "2026-10-25T12:00:00Z", "value": "1.1",
                "unit_of_measure": "ft", "approval_status": "Provisional", "time_series_id": "mchl1"}}]}
        row = collector.usgs_records(data, self.received, "d", "url", "raw/x")[0]
        self.assertEqual(row["datum"], "native_gage_datum:USGS-073802302")
        self.assertEqual(row["source_category"], "shadow")

    def test_noaa_zero_quality_codes_are_not_reported_as_flags(self):
        payload = {"data": [{"t": "2026-10-25 12:00", "v": "2.1", "f": "0,0"}]}
        row = collector.noaa_records("water_level", payload, self.received, "d", "url", "raw/x")[0]
        self.assertEqual(row["qc_flags"], [])

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

        requested_urls = []
        def opener(request, timeout=30):
            requested_urls.append(request.full_url)
            query = urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)
            if "ids" in query:
                return Response([{"icaoId": "KNEW", "obsTime": 1792940400, "reportTime": "2026-10-25T15:00:00Z",
                                  "wdir": 180, "wspd": 5, "rawOb": "METAR KNEW"}])
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

        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            now = dt.datetime(2026, 10, 25, 15, 0, tzinfo=UTC)
            receipt_clock = [now]
            real_fetch = collector.fetch
            def fetch_at_injected_clock(*args, **kwargs):
                body, _received, http_date, status, attempts = real_fetch(*args, **kwargs)
                return body, receipt_clock[0], http_date, status, attempts
            with patch.object(collector, "fetch", side_effect=fetch_at_injected_clock):
                first = collector.collect(temp, now=now, opener=opener, sleeper=lambda _: None)
            self.assertEqual(first["critical_failures"], [], json.dumps(first["sources"], indent=2))
            self.assertGreater(first["records_added"], 0)
            self.assertGreaterEqual(len(list((pathlib.Path(temp) / "raw").glob("*.json"))), 8)
            knew = next(item for item in first["sources"] if item["source"] == "NOAA AWC METAR KNEW")
            self.assertEqual(knew["category"], "shadow")
            self.assertEqual(knew["status"], "success")
            self.assertLessEqual(knew["newest_valid_age_seconds"], knew["freshness_limit_seconds"])
            self.assertEqual(sum("begin_date" in url for url in requested_urls), 2)
            self.assertEqual(sum("date=recent" in url for url in requested_urls), 0)
            self.assertTrue((pathlib.Path(temp) / "health" / (first["run_id"] + ".json")).exists())
            self.assertEqual(next(r for r in first["sources"] if "63160" in r["source"])["status"], "empty")
            receipt_clock[0] = now + dt.timedelta(minutes=1)
            with patch.object(collector, "fetch", side_effect=fetch_at_injected_clock):
                second = collector.collect(temp, now=receipt_clock[0], opener=opener, sleeper=lambda _: None)
            self.assertEqual(second["records_added"], 0)
            self.assertEqual(sum("begin_date" in url for url in requested_urls), 4)

    def test_new_local_feeds_are_collected_as_optional_and_keep_empty_status(self):
        class Response:
            status = 200
            headers = {"Date": "Sun, 25 Oct 2026 13:00:00 GMT"}
            def __init__(self, payload): self.payload = payload
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps(self.payload).encode()

        urls = []
        def opener(request, timeout=30):
            urls.append(request.full_url)
            query = urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)
            if "ids" in query:
                raise OSError("optional AWC feed unavailable")
            if "product" in query:
                product = query["product"][0]
                payload = ({"data": [{"t": "2026-10-25 12:00", "s": "10", "d": "180", "f": "0"}]}
                           if product == "wind" else
                           {"data": [{"t": "2026-10-25 12:00", "v": "1.2", "f": "0"}]}
                           if product == "water_level" else
                           {"predictions": [{"t": "2026-10-25 14:00", "v": "1.4"}]})
                return Response(payload)
            station, parameter = query["monitoring_location_id"][0], query["parameter_code"][0]
            if parameter == "00045" and station == "USGS-301828090363100":
                return Response({"features": []})
            if parameter == "00060":
                unit, value = "ft^3/s", "100"
            elif parameter == "00045":
                unit, value = "in", "0.02"
            else:
                unit, value = "ft", "2.5"
            return Response({"features": [{"properties": {"monitoring_location_id": station,
                "parameter_code": parameter, "time": "2026-10-25T12:00:00Z", "value": value,
                "unit_of_measure": unit, "approval_status": "Provisional", "time_series_id": station+parameter}}]})

        with tempfile.TemporaryDirectory() as temp:
            report = collector.collect(temp, now=self.received + dt.timedelta(hours=2), opener=opener, sleeper=lambda _: None)
            requested = {(urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("monitoring_location_id", [None])[0],
                          urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("parameter_code", [None])[0])
                         for url in urls}
            self.assertIn(("USGS-07379960", "00045"), requested)
            self.assertIn(("USGS-07379960", "00065"), requested)
            self.assertIn(("USGS-07378810", "00045"), requested)
            self.assertIn(("USGS-07378746", "00065"), requested)
            self.assertNotIn(("USGS-07379960", "00060"), requested)
            self.assertEqual(report["critical_failures"], [])
            self.assertIn("NOAA AWC METAR KNEW", report["shadow_failures"])
            knew = next(item for item in report["sources"] if item["source"] == "NOAA AWC METAR KNEW")
            self.assertEqual(knew["status"], "failed")
            self.assertFalse(knew["critical"])
            rain = next(item for item in report["sources"] if item["source"].endswith("USGS-301828090363100 parameter 00045"))
            self.assertEqual(rain["status"], "empty")
            self.assertFalse(rain["critical"])

    def test_receipt_deduplication_keeps_distinct_sensor_and_parameter_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            row = {"source": "USGS USGS-301828090363100", "station_id": "USGS-301828090363100",
                   "variable": "precipitation", "valid_time": "2026-10-25T12:00:00Z", "value": 0.1,
                   "qc_flags": [], "sensor_id": "sensor-a", "parameter_code": "00045"}
            other_sensor = {**row, "sensor_id": "sensor-b"}
            path, count = collector.append_receipts(pathlib.Path(temp) / "receipts", [row, other_sensor])
            self.assertEqual(count, 2)
            self.assertEqual(len(path.read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()

