import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import phase6_forecast
import phase6_metrics
import phase6_verify


class Phase6CoreTests(unittest.TestCase):
    def test_forecast_timestamps_and_create_only_archive(self):
        issue = dt.datetime(2026, 10, 22, 12, 17, tzinfo=dt.timezone.utc)
        record = phase6_forecast.make_record(issue, issue.replace(minute=0), {"maul1_stage_native_ft": 2.5}, {})
        self.assertEqual(record["forecasts"]["6"]["valid_time_utc"], "2026-10-22T18:17:00Z")
        with tempfile.TemporaryDirectory() as tmp:
            path = phase6_forecast.write_immutable(record, tmp)
            with self.assertRaises(FileExistsError):
                phase6_forecast.write_immutable(record, tmp)
            self.assertTrue(path.exists())

    def test_off_hour_issuance_targets_model_grid_not_wall_clock(self):
        actual = dt.datetime(2026, 10, 22, 13, 53, 11, tzinfo=dt.timezone.utc)
        anchor = actual.replace(minute=0, second=0)
        record = phase6_forecast.make_record(actual, anchor, {"maul1_stage_native_ft": 2.5}, {}, model_anchor_time=anchor)
        self.assertEqual(record["model_anchor_time_utc"], "2026-10-22T13:00:00Z")
        self.assertEqual(record["forecasts"]["6"]["valid_time_utc"], "2026-10-22T19:00:00Z")
        self.assertAlmostEqual(record["forecasts"]["6"]["effective_lead_hours"], 5.113611, places=5)
        with self.assertRaises(ValueError):
            phase6_forecast.make_record(actual, anchor, {}, {}, model_anchor_time=actual + dt.timedelta(minutes=1))

    def test_future_observation_is_not_verified_and_revisions_append(self):
        issue = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        record = {"issuance_id": "x", "forecasts": {"6": {"valid_time_utc": "2026-01-01T06:00:00Z", "models": {"coastal": {"status": "issued", "predicted_stage_native_ft": 2.}}}}}
        future = [{"valid_time_utc": "2026-01-01T06:00:00Z", "ingested_utc": "2026-01-01T07:00:00Z", "value_ft": 2.2}]
        self.assertEqual(phase6_verify.verify(record, future, "2026-01-01T06:30:00Z"), [])
        first = phase6_verify.verify(record, future, "2026-01-01T08:00:00Z")
        self.assertEqual(first[0]["revision"], 1)
        self.assertEqual(phase6_verify.verify(record, future, "2026-01-01T09:00:00Z", first), [])
        corrected = [dict(future[0], value_ft=2.3)]
        second = phase6_verify.verify(record, corrected, "2026-01-01T10:00:00Z", first)
        self.assertEqual(second[0]["revision"], 2)

    def test_qualifying_24h_event_grouping_and_guard(self):
        rows=[]
        for day in (1,2,5,9,13):
            rows.append({"valid_time_utc":f"2026-10-{day:02d}T18:00:00Z",
                         "actual_issue_time_utc":f"2026-10-{day:02d}T12:00:00Z",
                         "observed_change_ft":0.6,"forecast_change_ft":0.7})
        report=phase6_metrics.summarize_qualifying_events(rows)
        self.assertEqual(report["event_count"], 4)
        self.assertEqual(report["status"], "insufficient_independent_events")
        rows.append({"valid_time_utc":"2026-10-17T18:00:00Z",
                     "actual_issue_time_utc":"2026-10-17T12:00:00Z",
                     "observed_change_ft":0.8,"forecast_change_ft":0.7})
        report=phase6_metrics.summarize_qualifying_events(rows)
        self.assertEqual(report["event_count"], 5)
        self.assertEqual(report["detected_events"], 5)
        self.assertEqual(report["events"][0]["lead_to_first_qualifying_target_hours"], 6)

    def test_rise_confusion_and_small_sample_event_guard(self):
        rows = [{"forecast_change_ft": .4, "observed_change_ft": .3, "event_id": "e"}]
        metrics = phase6_metrics.compute_metrics(rows)
        self.assertEqual(metrics["rises"]["0.25"]["hits"], 1)
        self.assertEqual(metrics["events"]["status"], "insufficient_independent_events")


if __name__ == "__main__":
    unittest.main()
