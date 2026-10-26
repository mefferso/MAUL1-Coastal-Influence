import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_phase6_verification_sensitivity as sensitivity


class VerificationSensitivityTests(unittest.TestCase):
    def test_exact_match_excludes_nearby_observation(self):
        target = "2026-10-22T19:00:00Z"
        observations = [
            {"valid_time_utc": "2026-10-22T18:45:00Z", "value_ft": 2.0},
            {"valid_time_utc": target, "value_ft": 2.1},
        ]
        self.assertEqual(sensitivity.match_observation(target, observations, 0)["value_ft"], 2.1)

    def test_thirty_minute_match_chooses_nearest_and_rejects_ties_deterministically(self):
        target = "2026-10-22T19:00:00Z"
        observations = [
            {"valid_time_utc": "2026-10-22T19:15:00Z", "value_ft": 2.15},
            {"valid_time_utc": "2026-10-22T18:45:00Z", "value_ft": 2.0},
        ]
        self.assertEqual(sensitivity.match_observation(target, observations, 30)["value_ft"], 2.15)
        self.assertIsNone(sensitivity.match_observation(target, observations, 14))

    def test_match_respects_archived_ingestion_cutoff(self):
        target = "2026-10-22T19:00:00Z"
        observation = {"valid_time_utc": target, "value_ft": 2.0,
                       "ingested_utc": "2026-10-22T19:01:00Z"}
        self.assertIsNone(sensitivity.match_observation(
            target, [observation], 30, as_of="2026-10-22T19:00:30Z"))


if __name__ == "__main__":
    unittest.main()
