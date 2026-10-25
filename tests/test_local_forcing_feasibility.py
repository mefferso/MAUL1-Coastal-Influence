import json
import sys
from pathlib import Path
import unittest

PACKAGE = Path(__file__).resolve().parents[1] / "research" / "local-forcing-feasibility"
sys.path.insert(0, str(PACKAGE))

import coverage
import usgs_acquisition


class AcquisitionTests(unittest.TestCase):
    def test_request_is_allowlisted_and_bounded(self):
        url = usgs_acquisition.request_url("USGS-07378810", "00065", 24)
        self.assertIn("monitoring_location_id=USGS-07378810", url)
        self.assertIn("parameter_code=00065", url)
        self.assertIn("datetime=PT24H", url)
        with self.assertRaises(ValueError):
            usgs_acquisition.request_url("USGS-07378810", "00060", 24)
        with self.assertRaises(ValueError):
            usgs_acquisition.request_url("USGS-07378810", "00065", 169)

    def test_raw_provider_properties_and_receipt_provenance_are_preserved(self):
        feature = {"type": "Feature", "properties": {
            "time": "2026-10-25T12:00:00Z", "value": "0.12", "parameter_code": "00045",
            "unit_of_measure": "in", "qualifier": ["P"], "approvals_status": ["Working"],
            "last_modified": "2026-10-25T12:01:00Z",
        }}
        body = json.dumps({"features": [feature], "timeStamp": "2026-10-25T12:02:00Z"}).encode()
        moments = iter(["2026-10-25T12:02:01Z", "2026-10-25T12:02:02Z"])
        result = usgs_acquisition.fetch_series(
            "USGS-07378810", "00045", get=lambda url: (200, body), now=lambda: next(moments)
        )
        self.assertEqual(result["status"], "retrieved")
        self.assertEqual(result["features"], [feature])
        self.assertEqual(result["received_at_utc"], "2026-10-25T12:02:02Z")
        self.assertEqual(len(result["response_sha256"]), 64)

    def test_provider_failure_is_explicit_and_does_not_erase_other_series(self):
        result = usgs_acquisition.fetch_series(
            "USGS-07378810", "00065", get=lambda url: (_ for _ in ()).throw(TimeoutError("timeout")),
            now=lambda: "2026-10-25T12:00:00Z",
        )
        self.assertEqual(result["status"], "retrieval_error")
        self.assertEqual(result["error_type"], "TimeoutError")
        self.assertEqual(result["features"], [])

    def test_snapshot_is_explicitly_separate_from_issuance_and_verification(self):
        payload = usgs_acquisition.collect(
            get=lambda url: (200, b'{"features":[]}'), now=lambda: "2026-10-25T12:00:00Z", pause_seconds=0
        )
        self.assertEqual(payload["record_classification"], "research-only; not a forecast issuance or verification record")
        self.assertEqual(len(payload["results"]), 7)
        self.assertTrue(all(item["status"] == "no_observations" for item in payload["results"]))


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.features = [
            {"properties": {"time": "2026-10-25T10:00:00-05:00", "value": "1.1", "unit_of_measure": "ft", "approvals_status": ["Approved"]}},
            {"properties": {"time": "2026-10-25T16:00:00Z", "value": "bad", "qualifier": ["P"], "approvals_status": ["Working"]}},
            {"properties": {"time": "not-a-time", "value": None}},
        ]

    def test_coverage_counts_invalid_qc_and_irregular_gaps_without_filling(self):
        summary = coverage.summarize_coverage(self.features)
        self.assertEqual(summary["feature_count"], 3)
        self.assertEqual(summary["timestamped_feature_count"], 2)
        self.assertEqual(summary["invalid_or_missing_timestamp_count"], 1)
        self.assertEqual(summary["invalid_or_missing_value_count"], 2)
        self.assertEqual(summary["approval_status_counts"]["approved"], 1)
        self.assertEqual(summary["approval_status_counts"]["working_or_provisional"], 1)
        self.assertEqual(summary["median_observation_interval_seconds"], 3600)

    def test_event_alignment_is_utc_strictly_pre_issue_and_keeps_raw_rows(self):
        selected = coverage.align_before_issue(self.features, "2026-10-25T16:00:00Z", 2)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["properties"]["value"], "1.1")
        self.assertEqual(selected[0]["properties"]["unit_of_measure"], "ft")

    def test_event_summary_does_not_admit_post_issue_observations(self):
        events = [{"event_id": "outcome-group-1", "issue_time_utc": "2026-10-25T16:00:00Z", "first_qualifying_target_utc": "2026-10-25T17:00:00Z"}]
        results = coverage.event_coverage(events, self.features, hours=2)
        self.assertEqual(results[0]["available_row_count"], 1)
        self.assertEqual(results[0]["latest_observation_time_utc"], "2026-10-25T10:00:00-05:00")
        self.assertEqual(results[0]["window_start_utc"], "2026-10-25T14:00:00Z")
        self.assertEqual(results, coverage.event_coverage(events, self.features, hours=2))


if __name__ == "__main__":
    unittest.main()
