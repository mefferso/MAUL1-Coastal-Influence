import unittest
from datetime import datetime, timezone, timedelta

from analyze_wind_memory import descriptors


class WindMemoryTests(unittest.TestCase):
    def test_issue_bin_is_excluded(self):
        issue = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
        winds = {issue - timedelta(hours=i): (-10.0, 0.0) for i in range(1, 4)}
        winds[issue] = (40.0, 0.0)
        got = descriptors(winds, issue)
        self.assertEqual(got["u_mean_3h_kt"], -10.0)

    def test_missing_hours_reduce_coverage_and_break_runs(self):
        issue = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
        winds = {issue - timedelta(hours=i): (-10.0, 0.0) for i in (1, 3, 4, 5, 6)}
        got = descriptors(winds, issue)
        self.assertAlmostEqual(got["coverage_6h"], 5 / 6)
        self.assertEqual(got["longest_negative_u_run_6h"], 4)

    def test_insufficient_coverage_omits_window(self):
        issue = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
        winds = {issue - timedelta(hours=1): (-10.0, 0.0)}
        self.assertNotIn("u_mean_3h_kt", descriptors(winds, issue))


if __name__ == "__main__":
    unittest.main()
