import json
import pathlib
import tempfile
import unittest

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import archive_completeness as completeness


class TestArchiveCompleteness(unittest.TestCase):
    def test_coverage_latency_revisions_recovery_and_issue_availability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            receipts = root / "research/prospective-forcing-archive/receipts"
            receipts.mkdir(parents=True)
            records = [
                {"source":"USGS s", "station_id":"s", "parameter_code":"00065", "variable":"gage_height", "valid_time":"2026-10-31T00:00:00Z", "retrieved_at":"2026-10-31T00:05:00Z", "value":1, "status":"provisional", "qc_flags":[], "acquisition_mode":"prospective"},
                {"source":"USGS s", "station_id":"s", "parameter_code":"00065", "variable":"gage_height", "valid_time":"2026-10-31T06:00:00Z", "retrieved_at":"2026-10-31T12:00:00Z", "value":2, "status":"provisional", "qc_flags":[], "acquisition_mode":"delayed_recovery"},
                {"source":"USGS s", "station_id":"s", "parameter_code":"00065", "variable":"gage_height", "valid_time":"2026-10-31T06:00:00Z", "retrieved_at":"2026-10-31T12:01:00Z", "value":2, "status":"observed", "qc_flags":["approved"], "acquisition_mode":"delayed_recovery"},
                {"source":"USGS s", "station_id":"s", "parameter_code":"00065", "variable":"gage_height", "valid_time":"2026-10-31T12:00:00Z", "retrieved_at":"2026-10-31T12:05:00Z", "value":2, "status":"provisional", "qc_flags":[], "acquisition_mode":"prospective"},
            ]
            (receipts / "r.jsonl").write_text("".join(json.dumps(x)+"\n" for x in records))
            report = completeness.build_report(root, issue_times=["2026-10-31T08:00:00Z"])
            series = report["series"][0]
            self.assertEqual(series["unique_valid_timestamps"], 3)
            self.assertEqual(series["max_gap_seconds"], 21600)
            self.assertEqual(series["latency_seconds"]["max"], 21660)
            self.assertEqual(series["repeated_value_transitions"], 1)
            self.assertEqual(series["revision_valid_times"], 1)
            self.assertEqual(series["delayed_recovery_records"], 2)
            self.assertEqual(report["issue_availability"][0]["available_receipts"], 1)
            self.assertEqual(report["issue_availability"][0]["available_features"][0]["variable"], "gage_height")
            summary=completeness.render_summary(report)
            self.assertIn("Feature availability at issues", summary)
            self.assertIn("gage_height", summary)
            self.assertNotIn("2026-10-31T08:00:00Z", summary)


if __name__ == "__main__":
    unittest.main()
