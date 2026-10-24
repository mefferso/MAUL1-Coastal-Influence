import datetime as dt
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import model_lab


UTC = dt.timezone.utc


def row(issue, target, *, split="calibration", actual=2.0, stage=1.9,
        change6=0.1, persistence=1.9, challenger=2.0, event_ids=()):
    return {
        "issue_time": dt.datetime.fromisoformat(issue).replace(tzinfo=UTC),
        "target_time": dt.datetime.fromisoformat(target).replace(tzinfo=UTC),
        "split": split, "actual": actual, "maul1_stage_native_ft": stage,
        "maul1_change_6h_ft": change6, "persistence_ft": persistence,
        "challenger_ft": challenger, "event_ids": list(event_ids),
    }


class ModelLabTests(unittest.TestCase):
    def test_baseline_parity_canonicalizes_floating_residuals_at_declared_tolerance(self):
        self.assertEqual(model_lab.canonical_parity_difference(3.0e-18), 0.0)
        self.assertEqual(model_lab.canonical_parity_difference(1.0e-8), 1.0e-8)

    def test_committed_report_is_historical_only_and_has_provenance_for_all_horizons(self):
        path = pathlib.Path(__file__).resolve().parents[1] / "site/data/research/model-lab.json"
        report = json.loads(path.read_text())
        self.assertEqual(report["schema"], "maul1.model-lab.report.v1")
        self.assertEqual(report["status"], "Research / Shadow Evaluation / Not Operational")
        self.assertTrue(report["summary"]["all_rows_are_historical_hindcasts"])
        self.assertTrue(report["summary"]["prospective_archive_modified"] is False)
        self.assertEqual(report["challenger_protocol"]["model_version"], "model-lab-bounded-damped-trend-v1")
        self.assertEqual(report["baseline_reproduction"]["status"], "matched")
        self.assertEqual(len(report["case_studies"]), 3)
        self.assertFalse(report["promotion_criteria"]["challenger_promoted"])
        for horizon in ("6", "12", "24"):
            self.assertEqual(report["horizons"][horizon]["metrics"]["bounded_damped_trend_ft"]["n"],
                             report["challenger_headline"][horizon]["bounded_damped_trend_ft"]["n"])
            self.assertTrue(report["horizons"][horizon]["annual_and_seasonal"])
        self.assertEqual(report["provenance"]["target"],
                         "USGS MAUL1 station 07380215 parameter 00065, ft, native gage height")

    def test_training_targets_are_purged_before_validation(self):
        start = dt.datetime(2020, 1, 1, tzinfo=UTC)
        values = [
            row("2019-12-27T00:00:00", "2019-12-27T06:00:00"),
            row("2019-12-28T00:00:00", "2019-12-28T23:59:00"),
            row("2019-12-29T00:00:00", "2020-01-01T00:00:00"),
            row("2020-01-01T00:00:00", "2020-01-01T06:00:00"),
            row("2019-12-27T00:00:00", "2019-12-27T06:00:00", split="holdout"),
        ]
        indexes = model_lab.training_indices(values, start, embargo_hours=72)
        self.assertEqual(indexes, [0, 1])

    def test_challenger_uses_only_issue_time_maul1_changes_and_has_bounded_fallback(self):
        self.assertEqual(model_lab.CHALLENGER_FEATURES, ("maul1_stage_native_ft", "maul1_change_6h_ft"))
        self.assertEqual(model_lab.CHALLENGER_METHOD, "bounded_damped_trend_ft")
        self.assertNotIn("astronomical_prediction_change_mllw_ft", model_lab.CHALLENGER_FEATURES)
        self.assertNotIn("actual", model_lab.CHALLENGER_FEATURES)
        self.assertEqual(model_lab.damped_trend(2.0, None, 24, {"shrink": .5, "cap_per_hour": .1}), 2.0)
        self.assertAlmostEqual(model_lab.damped_trend(2.0, 6.0, 24, {"shrink": .5, "cap_per_hour": .1}), 3.2)

    def test_paired_comparison_preserves_issue_target_identity_and_excludes_missing(self):
        values = [
            row("2020-01-01T00:00:00", "2020-01-01T06:00:00"),
            row("2020-01-01T01:00:00", "2020-01-01T07:00:00", challenger=None),
            row("2020-01-01T00:00:00", "2020-01-01T06:00:00", persistence=None),
        ]
        paired = model_lab.paired_rows(values, ("persistence_ft", "challenger_ft"))
        self.assertEqual(len(paired), 1)
        self.assertEqual(paired[0]["issue_time"], values[0]["issue_time"])
        self.assertEqual(paired[0]["target_time"], values[0]["target_time"])

    def test_metrics_skill_and_block_bootstrap_are_deterministic(self):
        actual = [2.0, 3.0, 4.0]
        forecast = [2.5, 2.5, 3.0]
        persistence = [2.0, 2.0, 2.0]
        result = model_lab.metrics(actual, forecast, persistence)
        self.assertEqual(result["n"], 3)
        self.assertAlmostEqual(result["mae_ft"], 2.0 / 3.0)
        self.assertAlmostEqual(result["rmse_ft"], (1.5 / 3) ** .5)
        self.assertAlmostEqual(result["bias_ft"], -1.0 / 3.0)
        self.assertAlmostEqual(result["skill_vs_persistence"], 1.0 / 3.0)
        first = model_lab.block_bootstrap_mae_difference(actual, forecast, persistence, seed=12, replicates=30, block=2)
        second = model_lab.block_bootstrap_mae_difference(actual, forecast, persistence, seed=12, replicates=30, block=2)
        self.assertEqual(first, second)

    def test_empty_metrics_are_unavailable_and_incompatible_native_datum_is_rejected(self):
        self.assertEqual(model_lab.metrics([], [], []), {
            "n": 0, "mae_ft": None, "rmse_ft": None, "bias_ft": None,
            "skill_vs_persistence": None,
        })
        row = {"value": 2.5, "coverage": 1, "missing": False,
               "phase4_quality_excluded": False, "unit": "ft", "datum": "gage height"}
        self.assertTrue(model_lab.phase5a.valid_observation(row, "ft", "gage height"))
        self.assertFalse(model_lab.phase5a.valid_observation(row, "ft", "NAVD88"))
        self.assertFalse(model_lab.phase5a.valid_observation(row, "m", "gage height"))

    def test_event_metrics_count_unique_event_groups_not_overlapping_rows(self):
        values = [
            row("2020-01-01T00:00:00", "2020-01-01T06:00:00", event_ids=("event-a",)),
            row("2020-01-01T01:00:00", "2020-01-01T07:00:00", event_ids=("event-a",)),
            row("2020-01-02T00:00:00", "2020-01-02T06:00:00", event_ids=("event-b",)),
        ]
        result = model_lab.event_group_metrics(values, "challenger_ft")
        self.assertEqual(result["event_count"], 2)
        self.assertEqual(result["events"]["event-a"]["forecast_count"], 2)

    def test_phase6_rise_targets_group_within_24_hours_and_withhold_below_five(self):
        origin = dt.datetime(2020, 1, 1, tzinfo=UTC)
        rows = []
        for hour in (0, 24, 72, 120, 168, 216, 264):
            valid = origin + dt.timedelta(hours=hour)
            issue = valid - dt.timedelta(hours=24)
            rows.append({"issue_time": issue, "target_time": valid, "split": "holdout",
                         "actual": 2.5, "maul1_stage_native_ft": 2.0,
                         "challenger_ft": 2.6})
        summary = model_lab.phase6_qualifying_rise_summary(rows, "challenger_ft")
        self.assertEqual(summary["definition"], "outcome-defined 24h rises of at least 0.50 ft; targets within 24h grouped")
        self.assertEqual(summary["event_count"], 6)
        self.assertEqual(summary["detected_events"], 6)
        self.assertIn("not physical", summary["interpretation"])
        withheld = model_lab.phase6_qualifying_rise_summary(rows[:4], "challenger_ft")
        self.assertEqual(withheld["status"], "insufficient_independent_events")
        self.assertNotIn("detected_events", withheld)

    def test_future_feature_perturbation_cannot_change_challenger_prediction(self):
        config = {"shrink": .25, "cap_per_hour": .05}
        issue_row = {"maul1_stage_native_ft": 2.3, "maul1_change_6h_ft": .12,
                     "actual": 2.4, "astronomical_prediction_change_mllw_ft": 3.0,
                     "mchl1_stage_change_24h_native_ft": 99.0}
        before = model_lab.challenger_prediction(issue_row, 12, config)
        issue_row.update(actual=-100.0, astronomical_prediction_change_mllw_ft=-999.0,
                         mchl1_stage_change_24h_native_ft=-999.0)
        after = model_lab.challenger_prediction(issue_row, 12, config)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
