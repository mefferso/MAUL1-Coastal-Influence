import unittest
from datetime import datetime, timezone

from event_periods import WINDOWS, dt, max_24h_change


class EventWindowTests(unittest.TestCase):
    def test_transition_pulse_is_separate_from_beryl_gulf_period(self):
        by_id = {w["id"]: w for w in WINDOWS}
        transition = by_id["unattributed_transition_pulse"]
        beryl = by_id["beryl_gulf_to_landfall"]
        self.assertEqual(transition["end"], "2024-07-01T00:00:00Z")
        self.assertEqual(beryl["start"], "2024-07-05T00:00:00Z")
        self.assertLess(dt(transition["end"]), dt(beryl["start"]))

    def test_window_intervals_are_half_open_and_nonoverlapping(self):
        ordered = sorted(WINDOWS, key=lambda w: dt(w["start"]))
        for left, right in zip(ordered, ordered[1:]):
            self.assertEqual(dt(left["end"]), dt(right["start"]))

    def test_max_24h_change_uses_same_station_paired_observations(self):
        hour = datetime(2024, 6, 30, 0, tzinfo=timezone.utc)
        previous = hour.replace(day=29)
        rows = {
            previous: {("MAUL1", "stage"): 2.0},
            hour: {("MAUL1", "stage"): 2.7},
        }
        result = max_24h_change(rows, hour, hour.replace(hour=1), "MAUL1", "stage")
        self.assertAlmostEqual(result["max_increase"], .7)
        self.assertEqual(result["n_pairs"], 1)


if __name__ == "__main__":
    unittest.main()
