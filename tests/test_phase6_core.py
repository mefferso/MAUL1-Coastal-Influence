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

    def test_v2_compact_evidence_round_trip_and_legacy_read(self):
        source={"observations":[{"station":"NWCL1","valid_time_utc":"2026-10-22T15:00:00Z",
                                 "datum":"MLLW","value":1.25}],"sources":[{"station":"NWCL1"}]}
        record=phase6_forecast.make_record(
            dt.datetime(2026,10,22,16,10,tzinfo=dt.timezone.utc),
            dt.datetime(2026,10,22,16,tzinfo=dt.timezone.utc),
            {"maul1_stage_native_ft":2.5,"source_snapshot":source,
             "features":{"maul1_stage_native_ft":2.5},"availability":{}}, {})
        with tempfile.TemporaryDirectory() as folder:
            archive=Path(folder)
            compact=phase6_forecast.compact_with_immutable_snapshot(record,archive)
            self.assertNotIn("source_snapshot",compact["snapshot"])
            self.assertEqual(compact["schema"],"phase6.forecast.v2")
            self.assertEqual(phase6_forecast.recover_source_snapshot(compact,archive),source)
            self.assertEqual(phase6_forecast.recover_source_snapshot(record,archive),source)
            path=phase6_forecast.write_immutable(compact,archive)
            with self.assertRaises(FileExistsError):
                phase6_forecast.write_immutable(compact,archive)
            saved=json.loads(path.read_text())
            self.assertEqual(saved["issuance_id"],record["issuance_id"])
            self.assertEqual(phase6_forecast.recover_source_snapshot(saved,archive),source)
            self.assertEqual(list((archive/"snapshots").glob("*.json.gz")).__len__(),1)
            self.assertLess(path.stat().st_size,10000)

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

    def test_metrics_report_maul1_input_age_and_target_observation_delay(self):
        rows = [
            {"forecast_change_ft": .2, "observed_change_ft": .1,
             "issue_maul1_age_hours": .5, "observation_delay_minutes": 15},
            {"forecast_change_ft": .4, "observed_change_ft": .1,
             "issue_maul1_age_hours": 1.5, "observation_delay_minutes": 75},
        ]
        metrics = phase6_metrics.compute_metrics(rows)
        self.assertEqual(metrics["input_age_effect"]["le_1h"]["n"], 1)
        self.assertAlmostEqual(metrics["input_age_effect"]["gt_1h"]["mae_ft"], .3)
        self.assertEqual(metrics["observation_latency_minutes"]["n"], 2)
        self.assertEqual(metrics["observation_latency_minutes"]["median"], 45)

    def test_verification_completeness_separates_due_unverified_and_future_targets(self):
        record = {"mode": "authentic", "issuance_id": "i1", "forecasts": {
            "6": {"valid_time_utc": "2026-10-23T10:00:00Z", "models": {
                "m": {"status": "issued"}, "abstained": {"status": "abstained"}}},
            "12": {"valid_time_utc": "2026-10-23T18:00:00Z", "models": {
                "m": {"status": "issued"}}},
        }}
        verified = {("i1", 6, "m")}
        result = phase6_metrics.verification_completeness(
            [record], verified, "2026-10-23T12:00:00Z"
        )
        self.assertEqual(result["m:6h"]["issued"], 1)
        self.assertEqual(result["m:6h"]["matured"], 1)
        self.assertEqual(result["m:6h"]["verified"], 1)
        self.assertEqual(result["abstained:6h"]["abstained"], 1)
        self.assertEqual(result["m:12h"]["not_yet_due"], 1)


class Phase6EvidenceReadinessMetricTests(unittest.TestCase):
    def test_comparison_metrics_count_only_complete_model_pairs(self):
        rows = [
            {"forecast_change_ft": 0.4, "observed_change_ft": 0.2, "persistence_change_ft": 0.0},
            {"forecast_change_ft": 0.1, "observed_change_ft": 0.3, "persistence_change_ft": 0.0},
            {"forecast_change_ft": 0.8, "observed_change_ft": None, "persistence_change_ft": 0.0},
            {"forecast_change_ft": 0.6, "observed_change_ft": 0.1, "persistence_change_ft": None},
        ]
        metrics = phase6_metrics.compute_metrics(rows)
        self.assertEqual(metrics["n"], 3)
        self.assertAlmostEqual(metrics["mae_ft"], 0.3)
        self.assertAlmostEqual(metrics["skill_vs_persistence"], 0.2)
        self.assertAlmostEqual(metrics["mae_persistence_ft"], 0.25)
        self.assertEqual(metrics["persistence_comparison"]["paired_n"], 2)
        self.assertAlmostEqual(metrics["persistence_comparison"]["model_rmse_ft"], 0.2)
        self.assertAlmostEqual(metrics["persistence_comparison"]["persistence_rmse_ft"], (0.065) ** 0.5)
        self.assertAlmostEqual(metrics["persistence_comparison"]["rmse_difference_ft"], 0.2-(0.065)**0.5)
        self.assertAlmostEqual(metrics["persistence_comparison"]["persistence_bias_ft"], -0.25)
        self.assertAlmostEqual(metrics["persistence_comparison"]["bias_difference_ft"], 0.25)
        self.assertEqual(metrics["rises"]["0.50"]["hits"], 0)

    def test_readiness_maturity_excludes_simulations_and_separates_missing_predictions(self):
        authentic = {"mode": "authentic", "issuance_id": "a", "forecasts": {
            "6": {"valid_time_utc": "2026-10-23T10:00:00Z", "models": {
                "paired": {"status": "issued"}, "abstained": {"status": "abstained"},
                "unavailable": {"status": "unavailable"}}},
            "12": {"valid_time_utc": "2026-10-23T18:00:00Z", "models": {
                "paired": {"status": "issued"}}},
        }}
        simulation = {"mode": "simulation", "issuance_id": "s", "forecasts": {
            "6": {"valid_time_utc": "2026-10-23T10:00:00Z", "models": {"paired": {"status": "issued"}}}}}
        result = phase6_metrics.verification_completeness(
            [authentic, simulation], {("a", 6, "paired")}, "2026-10-23T12:00:00Z")
        self.assertEqual(result["paired:6h"], {
            "forecast_slots": 1, "issued": 1, "abstained": 0, "other_unavailable": 0,
            "matured": 1, "verified": 1, "due_unverified": 0, "not_yet_due": 0})
        self.assertEqual(result["abstained:6h"]["abstained"], 1)
        self.assertEqual(result["unavailable:6h"]["other_unavailable"], 1)
        self.assertEqual(result["paired:12h"]["not_yet_due"], 1)

    def test_existing_24_hour_group_boundary_and_threshold_are_retained(self):
        rows = []
        for stamp in ("2026-10-01T00:00:00Z", "2026-10-02T00:00:00Z",
                      "2026-10-03T00:00:00Z", "2026-10-04T00:00:01Z"):
            rows.append({"valid_time_utc": stamp, "actual_issue_time_utc": "2026-09-30T00:00:00Z",
                         "observed_change_ft": 0.50, "forecast_change_ft": 0.0})
        rows.append({"valid_time_utc": "2026-10-05T00:00:00Z", "actual_issue_time_utc": "2026-09-30T00:00:00Z",
                     "observed_change_ft": 0.49, "forecast_change_ft": 1.0})
        result = phase6_metrics.summarize_qualifying_events(rows)
        self.assertEqual(result["event_count"], 2)
        self.assertEqual(result["status"], "insufficient_independent_events")
        self.assertNotIn("missed_events", result)


if __name__ == "__main__":
    unittest.main()
