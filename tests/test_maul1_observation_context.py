import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import maul1_observation_context as context

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def payload(rows, site="07380215", code="00065"):
    return json.dumps({"value": {"timeSeries": [{
        "sourceInfo": {"siteCode": [{"value": site}]},
        "variable": {"variableCode": [{"value": code}]},
        "values": [{"value": [
            {"dateTime": stamp, "value": str(value), "qualifiers": qualifiers}
            for stamp, value, qualifiers in rows
        ]}],
    }]}}).encode()


def record(stamp="2026-10-24T11:00:00Z", value=2.5, qualifiers=None):
    return {"valid_time_utc": stamp, "stage_ft": value,
            "qualifiers": qualifiers or [], "provisional": "P" in (qualifiers or [])}


class ObservationContextTests(unittest.TestCase):
    def test_request_uses_exact_28_day_utc_window_and_native_parameter(self):
        args = parse_qs(urlparse(context.request_url(NOW)).query)
        self.assertEqual(args["sites"], ["07380215"])
        self.assertEqual(args["parameterCd"], ["00065"])
        self.assertEqual(args["startDT"], ["2026-09-26T12:00:00Z"])
        self.assertEqual(args["endDT"], ["2026-10-24T12:00:00Z"])
        self.assertEqual(args["siteStatus"], ["all"])

    def test_parser_preserves_quality_and_provenance_and_sorts_out_of_order_rows(self):
        raw = payload([("2026-10-24T11:00:00Z", 2.6, ["P"]),
                       ("2026-09-26T13:00:00Z", 2.4, [])])
        doc = context.build_dataset(raw, NOW, "Sat, 24 Oct 2026 12:00:00 GMT")
        self.assertEqual(doc["coverage_start_utc"], "2026-09-26T13:00:00Z")
        self.assertEqual(doc["coverage_end_utc"], "2026-10-24T11:00:00Z")
        self.assertTrue(doc["observations"][-1]["provisional"])
        self.assertEqual(doc["observations"][-1]["qualifiers"], ["P"])
        self.assertEqual(doc["parameter_code"], "00065")
        self.assertEqual(doc["datum"], "gage height")
        self.assertEqual(len(doc["response_sha256"]), 64)

    def test_rejects_wrong_station_or_parameter_and_empty_series(self):
        for raw in (payload([("2026-10-24T11:00:00Z", 2.5, [])], site="07378500"),
                    payload([("2026-10-24T11:00:00Z", 2.5, [])], code="63160"),
                    payload([])):
            with self.assertRaises(ValueError):
                context.build_dataset(raw, NOW)

    def test_conflicting_duplicate_rows_are_rejected_but_identical_rows_collapse(self):
        stamp = "2026-10-24T11:00:00Z"
        identical = context.build_dataset(payload([(stamp, 2.5, []), (stamp, 2.5, [])]), NOW)
        self.assertEqual(len(identical["observations"]), 1)
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            context.build_dataset(payload([(stamp, 2.5, []), (stamp, 2.6, [])]), NOW)

    def test_validation_rejects_incompatible_datum_duplicate_and_future_observations(self):
        doc = context.build_dataset(payload([("2026-10-24T11:00:00Z", 2.5, [])]), NOW)
        for change in ({"datum": "NAVD88"}, {"parameter_code": "63160"},
                       {"observations": [record(), record()]},
                       {"observations": [record("2026-10-24T13:00:00Z")] }):
            bad = dict(doc, **change)
            with self.assertRaises(ValueError):
                context.validate_dataset(bad)

    def test_partial_observation_coverage_is_retained_without_filling_gaps(self):
        doc = context.build_dataset(payload([("2026-10-24T00:00:00Z", 2.5, []),
                                             ("2026-10-24T11:00:00Z", 2.8, [])]), NOW)
        self.assertEqual(len(doc["observations"]), 2)
        self.assertEqual(doc["coverage_start_utc"], "2026-10-24T00:00:00Z")
        self.assertEqual(doc["coverage_end_utc"], "2026-10-24T11:00:00Z")

    def test_unavailable_or_empty_update_retains_last_valid_snapshot_and_reports_age(self):
        doc = context.build_dataset(payload([("2026-10-23T11:00:00Z", 2.5, [])]), NOW-dt.timedelta(days=1))
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "observations.json"
            path.write_text(json.dumps(doc))
            failed = context.update_dataset(path, lambda url: (_ for _ in ()).throw(OSError("offline")), NOW)
            self.assertEqual(failed["status"], "retained_previous")
            self.assertEqual(failed["dataset_retrieved_utc"], doc["retrieved_utc"])
            empty = context.update_dataset(path, lambda url: (payload([]), None), NOW)
            self.assertEqual(empty["status"], "retained_previous")
            self.assertEqual(json.loads(path.read_text())["observations"], doc["observations"])

    def test_no_existing_dataset_is_reported_unavailable_without_fabricating_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            result = context.update_dataset(pathlib.Path(temp) / "missing.json",
                                            lambda url: (payload([]), None), NOW)
            self.assertEqual(result["status"], "unavailable")
            self.assertFalse((pathlib.Path(temp) / "missing.json").exists())

    def test_unchanged_values_do_not_create_redundant_dataset_commits(self):
        raw = payload([("2026-10-24T11:00:00Z", 2.5, [])])
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "observations.json"
            first = context.update_dataset(path, lambda url: (raw, None), NOW)
            second = context.update_dataset(path, lambda url: (raw, None), NOW+dt.timedelta(minutes=5))
            self.assertEqual(first["status"], "updated")
            self.assertEqual(second["status"], "unchanged")
            self.assertEqual(json.loads(path.read_text())["retrieved_utc"], first["dataset_retrieved_utc"])


if __name__ == "__main__":
    unittest.main()
