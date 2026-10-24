import datetime as dt
import unittest

import audit


UTC = dt.timezone.utc


def row(issue_hour, *, forecast_change=0.0, observed_change=0.0):
    issue = dt.datetime(2024, 1, 1, tzinfo=UTC) + dt.timedelta(hours=issue_hour)
    target = issue + dt.timedelta(hours=24)
    return {
        "issue_time": issue,
        "target_time": target,
        "stage_ft": 2.0,
        "actual_change_ft": observed_change,
        "forecast_change_ft": forecast_change,
        "predicted_change_ft": forecast_change,
        "phase5b_coastal_tidal_change_ft": forecast_change,
        "available": True,
    }


class RiseFailureAuditTests(unittest.TestCase):
    def test_phase6_grouping_keeps_targets_at_24_hour_separation_together(self):
        rows = [
            row(0, observed_change=.51),
            row(24, observed_change=.62),
            row(49, observed_change=.55),
            row(100, observed_change=.55),
            row(200, observed_change=.55),
            row(300, observed_change=.55),
        ]
        groups = audit.group_qualifying_targets(rows)
        self.assertEqual(len(groups), 5)
        self.assertEqual(groups[0]["qualified_window_count"], 2)
        self.assertEqual(groups[1]["qualified_window_count"], 1)

    def test_event_detection_requires_threshold_forecast_on_qualifying_targets(self):
        rows = [
            row(0, forecast_change=.49, observed_change=.8),
            row(1, forecast_change=.6, observed_change=.3),
            row(100, forecast_change=.49, observed_change=.8),
            row(200, forecast_change=.49, observed_change=.8),
            row(300, forecast_change=.49, observed_change=.8),
            row(400, forecast_change=.49, observed_change=.8),
        ]
        groups = audit.group_qualifying_targets(rows)
        self.assertEqual(len(groups), 5)
        self.assertFalse(groups[0]["detected"])

    def test_phase6_withholds_event_list_below_five_independent_groups(self):
        rows = [row(i * 100, observed_change=.6) for i in range(4)]
        self.assertEqual(audit.group_qualifying_targets(rows), [])

    def test_false_alert_cluster_uses_issue_time_gaps_and_target_response(self):
        rows = [
            row(0, forecast_change=.7, observed_change=.1),
            row(24, forecast_change=.6, observed_change=.2),
            row(49, forecast_change=.8, observed_change=.6),
            row(74, forecast_change=.7, observed_change=.1),
        ]
        clusters = audit.cluster_alerts(rows)
        self.assertEqual(len(clusters), 3)
        self.assertEqual(clusters[0]["alert_count"], 2)
        self.assertTrue(clusters[0]["false_alarm"])
        self.assertFalse(clusters[1]["false_alarm"])
        self.assertTrue(clusters[2]["false_alarm"])

    def test_underforecast_bins_are_descriptive_not_causal(self):
        self.assertEqual(audit.failure_label(.45), "near_threshold_underforecast_not_causal")
        self.assertEqual(audit.failure_label(.10), "large_subthreshold_forecast_not_causal")
        self.assertEqual(audit.failure_label(.55), "threshold_target_after_first_qualifying_target_not_physical_onset")
        self.assertEqual(audit.failure_label(.55, detected=True), "target_alert_matched")
        self.assertIn("not_causal", audit.failure_label(.45))


class ArchivedResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.events, cls.clusters, cls.timelines = audit.build_audit()

    def test_published_counts_reproduce_and_late_matches_are_separated(self):
        result = self.report["definition_reproduction"]
        self.assertEqual((result["phase6_groups"], result["detected_groups"], result["missed_groups"]),
                         (109, 28, 81))
        self.assertEqual(result["phase5b_false_alert_clusters"], 48)
        self.assertEqual(result["all_alert_clusters"], 78)
        self.assertTrue(result["matches_existing_model_lab_groups"])
        self.assertTrue(result["matches_existing_model_lab_false_clusters"])
        counts = self.report["failure_mechanism_counts"]
        self.assertEqual(counts["threshold_target_after_first_qualifying_target_not_physical_onset"], 2)
        self.assertEqual(counts["large_subthreshold_forecast_not_causal"], 57)
        self.assertEqual(counts["near_threshold_underforecast_not_causal"], 22)

    def test_temporal_groups_are_not_mislabeled_as_independent_physical_events(self):
        audit_result = self.report["group_independence_audit"]
        self.assertEqual(audit_result["phase3b_response_events_overlapping_multiple_phase6_groups"], 21)
        self.assertIn("not proven independent physical", audit_result["interpretation"])

    def test_output_rows_are_event_and_alert_episode_level_and_keep_utc_pairs(self):
        self.assertEqual(len(self.events), 109)
        self.assertEqual(len(self.clusters), 78)
        self.assertEqual(len([row for row in self.clusters if row["false_alarm"]]), 48)
        for row in self.events:
            self.assertIn("T", row["first_qualifying_target_utc"])
            self.assertIn("Z", row["first_issue_time_utc"])
            self.assertEqual(row["interpretation"].startswith("Observed covariate"), True)

    def test_retrospective_causality_guardrails_and_native_datum_are_recorded(self):
        safeguards = self.report["causal_safeguards"]
        self.assertTrue(safeguards["no_new_models_trained"])
        self.assertTrue(safeguards["no_future_observation_features_used"])
        self.assertEqual(safeguards["maul1_datum"], "native gage height")
        self.assertEqual(safeguards["nwcl1_residual_datum"], "MLLW")
        self.assertIn("receipt time", self.report["archive_coverage"]["receipt_time_coverage"])
        self.assertIn("source_sha256", self.report["provenance"])

    def test_phase3b_overlap_is_not_claimed_as_same_event_identity(self):
        groups = [{"event_id": "rise-1", "first_target_utc": "2024-01-02T00:00:00Z",
                   "last_target_utc": "2024-01-02T04:00:00Z"}]
        responses = [{"event_id": "response-1", "trough_utc": "2024-01-01T12:00:00Z",
                      "recovery_end_utc": "2024-01-04T00:00:00Z"}]
        overlap = audit.overlapping_response_events(groups[0], responses)
        self.assertEqual(overlap, ["response-1"])


if __name__ == "__main__":
    unittest.main()
