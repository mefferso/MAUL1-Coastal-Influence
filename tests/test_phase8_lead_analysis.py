import datetime as dt
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase8_lead_analysis import (
    clean_mchl1_context_row,
    first_confirmation,
    forward_response_status,
    expanding_discharge_thresholds,
    first_control_trigger,
    first_pathway_confirmation,
    nearest_upcoming_event,
    representative_cases,
    signal_episodes,
)
from scripts import evidence, phase4

UTC = dt.timezone.utc
HOUR = dt.timedelta(hours=1)


def row(value, datum="gage height", unit="ft", missing=False):
    return {"value": value, "datum": datum, "unit": unit, "coverage": 1,
            "missing": missing, "phase4_quality_excluded": False}


class Phase8LeadAnalysisTests(unittest.TestCase):
    def test_confirmation_time_is_issue_time_after_full_phase4_six_hour_window(self):
        start = dt.datetime(2024, 1, 1, tzinfo=UTC)
        rows = {start + i * HOUR: {"flags": {"coastal": "absent"}} for i in range(6)}
        rows[start + 6 * HOUR] = {"flags": {"coastal": "present"}}

        self.assertEqual(first_confirmation(rows, "coastal", start, start + 6 * HOUR), start + 6 * HOUR)

    def test_signal_only_after_onset_has_negative_lead_not_early_warning(self):
        onset = dt.datetime(2024, 1, 1, 12, tzinfo=UTC)
        rows = {onset + HOUR: {"flags": {"river": "present"}}}

        detected = first_confirmation(rows, "river", onset - 72 * HOUR, onset + 24 * HOUR)

        self.assertEqual((onset - detected).total_seconds() / 3600, -1)

    def test_unknown_gap_breaks_signal_episode_and_multiple_episodes_are_retained(self):
        t0 = dt.datetime(2024, 1, 1, tzinfo=UTC)
        states = ["present", "present", "unknown", "present", "absent", "present"]
        rows = {t0 + i * HOUR: {"flags": {"wind": state}} for i, state in enumerate(states)}

        self.assertEqual(signal_episodes(rows, "wind"), [t0, t0 + 3 * HOUR, t0 + 5 * HOUR])

    def test_close_events_assign_detection_to_nearest_upcoming_event_only(self):
        detection = dt.datetime(2024, 1, 1, tzinfo=UTC)
        events = [{"event_id": "later", "_onset": detection + 20 * HOUR},
                  {"event_id": "nearer", "_onset": detection + 8 * HOUR}]

        self.assertEqual(nearest_upcoming_event(detection, events), "nearer")

    def test_detection_at_onset_can_be_assigned_but_does_not_count_as_positive_lead(self):
        onset = dt.datetime(2024, 1, 1, tzinfo=UTC)
        event = {"event_id": "event", "_onset": onset}

        self.assertEqual(nearest_upcoming_event(onset, [event]), "event")
        self.assertEqual((onset - onset).total_seconds(), 0)

    def test_invalid_mchl1_sentinel_and_contaminated_average_are_removed_only_from_context(self):
        for value in (9_999_999.0, 4_999_999.985):
            source = {"station": "MCHL1", "variable": "stage", "value": value, "missing": False}
            cleaned, removed = clean_mchl1_context_row(source)
            self.assertTrue(removed)
            self.assertIsNone(cleaned["value"])
            self.assertTrue(cleaned["missing"])
            self.assertEqual(source["value"], value)
        legitimate = {"station": "MCHL1", "variable": "stage", "value": -1.49}
        self.assertEqual(clean_mchl1_context_row(legitimate), (legitimate, False))
        other = {"station": "MAUL1", "variable": "stage", "value": 9_999_999.0}
        self.assertEqual(clean_mchl1_context_row(other), (other, False))

    def test_incomplete_six_hour_signal_window_is_not_confirmed(self):
        issue = dt.datetime(2024, 1, 1, 12, tzinfo=UTC)
        index = {("MDLL1", "stage"): {issue - i * HOUR: row(.5, missing=(i == 4)) for i in range(1, 7)}}
        metrics = evidence.metrics(index, issue)
        assessment = evidence.decide(metrics, issue)
        self.assertEqual(assessment["flags"]["lake"], "unknown")

    def test_datum_change_between_baseline_and_signal_window_is_unknown(self):
        issue = dt.datetime(2024, 1, 5, tzinfo=UTC)
        series = {}
        for i in range(72, 24, -1):
            series[issue - i * HOUR] = row(0.0, datum="old datum")
        for i in range(1, 7):
            series[issue - i * HOUR] = row(.5, datum="new datum")
        assessment = evidence.decide(evidence.metrics({("MDLL1", "stage"): series}, issue), issue)
        self.assertEqual(assessment["flags"]["lake"], "unknown")

    def test_issue_screen_does_not_read_observation_at_or_after_issue_time(self):
        issue = dt.datetime(2024, 1, 1, 12, tzinfo=UTC)
        series = {issue - i * HOUR: row(float(i)) for i in range(1, 7)}
        series[issue] = row(999.0)

        current = evidence.window({("NWCL1", "residual"): series}, ("NWCL1", "residual"), issue, 6, "ft")

        self.assertEqual(current["values"], [6.0, 5.0, 4.0, 3.0, 2.0, 1.0])
        self.assertNotIn(999.0, current["values"])

    def test_residual_requires_same_hour_same_datum_water_and_prediction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            hourly = root / "hourly"
            hourly.mkdir()
            water_time = "2024-01-01T00:00:00Z"
            prediction_time = "2024-01-01T01:00:00Z"
            records = [
                {"station": "NWCL1", "variable": "water", "time": water_time, "value": 1.0,
                 "unit": "ft", "datum": "MLLW", "coverage": 1, "missing": False},
                {"station": "NWCL1", "variable": "prediction", "time": prediction_time, "value": .2,
                 "unit": "ft", "datum": "MLLW", "coverage": 1, "missing": False},
            ]
            (hourly / "2024-01.json.gz").write_bytes(gzip.compress(json.dumps({"records": records}).encode()))

            index = phase4.load_inputs(root)

            self.assertTrue(index[("NWCL1", "residual")][dt.datetime(2024, 1, 1, tzinfo=UTC)]["missing"])

    def test_control_followup_distinguishes_response_unknown_and_right_censoring(self):
        detection = dt.datetime(2024, 1, 1, tzinfo=UTC)
        archive_end = detection + 48 * HOUR
        response = {"onset_known": True, "_onset": detection + 5 * HOUR}
        uncertain = {"onset_known": False, "_onset": None,
                     "_trough": detection + 2 * HOUR, "_peak": detection + 4 * HOUR}

        self.assertEqual(forward_response_status(detection, 6, [response], archive_end), "response")
        self.assertEqual(forward_response_status(detection, 6, [uncertain], archive_end), "onset_uncertain")
        self.assertEqual(forward_response_status(detection, 6, [], detection + 5 * HOUR), "right_censored")

    def test_fast_expanding_discharge_quantile_matches_phase4_reference(self):
        start = dt.datetime(2016, 1, 1, tzinfo=UTC)
        discharge = {start + i * HOUR: row(float((i * 37) % 5000), datum="native", unit="cfs")
                     for i in range(1100)}
        index = {("DENL1", "discharge"): discharge}
        issues = [start + 999 * HOUR, start + 1000 * HOUR, start + 1050 * HOUR]

        reference = phase4.replay_thresholds(index, issues)
        optimized = expanding_discharge_thresholds(index, issues)

        for issue in issues:
            self.assertAlmostEqual(optimized[issue]["discharge_high_cfs"],
                                   reference[issue]["discharge_high_cfs"], places=9)

    def test_representative_cases_require_unique_non_censored_positive_credit(self):
        rows = [
            {"event_id": "window-boundary", "onset_known": True, "onset_utc": "2024-01-03T00:00:00Z",
             "classification_screen": "Coastal-supported", "signals": {
                 "coastal": {"timing": "before", "retrospective_lead_hours": 72,
                             "unique_event_credit": True, "unique_event_credit_lead_hours": 72,
                             "lookback_left_censored": False},
                 "river": {"timing": "before", "retrospective_lead_hours": 72,
                           "unique_event_credit": True, "unique_event_credit_lead_hours": 72,
                           "lookback_left_censored": False}}},
            {"event_id": "left-censored", "onset_known": True, "onset_utc": "2024-01-04T00:00:00Z",
             "classification_screen": "Coastal-supported", "signals": {
                 "coastal": {"timing": "before", "retrospective_lead_hours": 72,
                             "unique_event_credit": False, "lookback_left_censored": True},
                 "river": {"timing": "before", "retrospective_lead_hours": 72,
                           "unique_event_credit": False, "lookback_left_censored": True}}},
            {"event_id": "valid", "onset_known": True, "onset_utc": "2024-01-05T00:00:00Z",
             "classification_screen": "River-supported", "signals": {
                 "coastal": {"timing": "before", "retrospective_lead_hours": 20,
                             "unique_event_credit": True, "unique_event_credit_lead_hours": 20,
                             "lookback_left_censored": False},
                 "river": {"timing": "before", "retrospective_lead_hours": 10,
                           "unique_event_credit": True, "unique_event_credit_lead_hours": 10,
                           "lookback_left_censored": False}}},
            {"event_id": "after", "onset_known": True, "onset_utc": "2024-01-06T00:00:00Z",
             "classification_screen": "Indeterminate", "signals": {
                 "coastal": {"timing": "after", "retrospective_lead_hours": -2,
                             "unique_event_credit": True, "unique_event_credit_lead_hours": -2,
                             "lookback_left_censored": False},
                 "river": {"timing": "not_detected", "retrospective_lead_hours": None,
                           "unique_event_credit": False, "lookback_left_censored": False}}},
        ]

        cases = representative_cases(rows)

        coastal = next(case for case in cases if case["selection"].startswith("largest observed coastal"))
        river = next(case for case in cases if case["selection"].startswith("largest observed river"))
        self.assertEqual(coastal["event_id"], "valid")
        self.assertEqual(river["event_id"], "valid")
        both = next(case for case in cases if "both river" in case["selection"])
        self.assertEqual(both["event_id"], "valid")

    def test_first_confirmed_pathway_selects_earliest_confirmation_not_closest_to_onset(self):
        signals = {
            "coastal": {"timing": "before", "retrospective_lead_hours": 48},
            "river": {"timing": "before", "retrospective_lead_hours": 6},
            "residual": {"timing": "after", "retrospective_lead_hours": -2},
        }

        self.assertEqual(first_pathway_confirmation(signals), "coastal")

    def test_active_signal_at_control_start_is_first_trigger_even_if_episode_restarts_later(self):
        start = dt.datetime(2024, 1, 1, tzinfo=UTC)
        issues = [start + i * HOUR for i in range(4)]
        rows = {time: {"flags": {"wind": state}} for time, state in zip(issues, ("present", "unknown", "absent", "present"))}

        self.assertEqual(first_control_trigger(issues, rows, [issues[3]], "wind"), start)


if __name__ == "__main__":
    unittest.main()
