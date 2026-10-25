import json
import statistics
import unittest
from pathlib import Path


CLAIMS = json.loads((Path(__file__).parent / "presentation_claims.json").read_text())


class PresentationClaimTests(unittest.TestCase):
    def test_delay_summary_is_arithmetic_but_not_event_validation(self):
        delays = [row["delay_hours"] for row in CLAIMS["water_sites"]]
        summary = CLAIMS["deck_summary"]
        self.assertAlmostEqual(statistics.mean(delays), summary["delay_mean_hours"])
        self.assertEqual(statistics.median(delays), summary["delay_median_hours"])
        self.assertEqual(statistics.mode(delays), summary["delay_mode_hours"])

    def test_reported_six_days_is_not_150_hours(self):
        wind = CLAIMS["wind_plot"]
        self.assertEqual(wind["claimed_hours_over_threshold"], 150)
        self.assertAlmostEqual(wind["arithmetic_days_from_hours"], 150 / 24)
        self.assertNotEqual(wind["claimed_days"], wind["arithmetic_days_from_hours"])

    def test_water_duration_annotations_include_hour_day_conflicts(self):
        conflicts = [row for row in CLAIMS["water_sites"]
                     if abs(row["water_hours"] / 24 - row["slide_water_days"]) > .1]
        self.assertEqual({row["site"] for row in conflicts},
                         {"Lakefront Airport", "Amite River at Hwy 22 Maurepas", "Blind River in SW Maurepas"})

    def test_wind_source_is_one_shared_reference_and_not_reproducible(self):
        wind = CLAIMS["wind_plot"]
        self.assertEqual(wind["source_count"], 1)
        self.assertEqual(wind["reused_for_water_sites"], 10)
        self.assertIsNone(wind["exact_threshold_interval"])
        self.assertIsNone(wind["measurement_averaging_period"])


if __name__ == "__main__":
    unittest.main()
