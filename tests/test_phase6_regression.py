import datetime as dt
import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import phase5a
import phase6_forecast


ROOT = Path(__file__).resolve().parents[1]


class Phase6TimingRegressionTests(unittest.TestCase):
    def test_new_record_states_feature_anchor_contract_explicitly(self):
        actual = dt.datetime(2026, 10, 22, 13, 53, 11, tzinfo=dt.timezone.utc)
        anchor = actual.replace(minute=0, second=0)
        record = phase6_forecast.make_record(
            actual, actual.replace(minute=53, second=9),
            {"maul1_stage_native_ft": 2.5}, {}, model_anchor_time=anchor)

        self.assertEqual(record["feature_anchor_time_utc"], "2026-10-22T13:00:00Z")
        self.assertEqual(record["valid_time_basis"], "feature_anchor_plus_horizon")
        self.assertEqual(record["forecasts"]["6"]["valid_time_utc"], "2026-10-22T19:00:00Z")
        self.assertAlmostEqual(record["forecasts"]["6"]["effective_lead_hours"], 5.113611, places=5)

    def test_first_authentic_issue_is_an_immutable_old_contract_fixture(self):
        path = ROOT / "site/data/prospective/archive/issues/d4935e479e83311c.json"
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "ec468750e739cbb07e234e1277c16850d77b44f2d081291efbb63dd70fa78feb")
        record = json.loads(raw)
        self.assertEqual(record["nominal_issue_time_utc"], "2026-10-22T13:53:09Z")
        self.assertEqual(record["actual_issue_time_utc"], "2026-10-22T13:53:11Z")
        self.assertNotIn("model_anchor_time_utc", record)
        self.assertEqual(record["forecasts"]["6"]["valid_time_utc"], "2026-10-22T19:53:11Z")
        self.assertEqual(record["forecasts"]["12"]["valid_time_utc"], "2026-10-23T01:53:11Z")
        self.assertEqual(record["forecasts"]["24"]["valid_time_utc"], "2026-10-23T13:53:11Z")

    def test_phase5_target_reference_is_exact_hourly_issue_plus_horizon(self):
        issue = dt.datetime(2026, 10, 22, 13, tzinfo=dt.timezone.utc)
        issue_hour = int(issue.timestamp() // 3600)
        for horizon in phase5a.HORIZONS:
            target_hour = int(phase5a._target_times(np.array([issue_hour]), horizon)[0])
            target = dt.datetime.fromtimestamp(target_hour * 3600, tz=dt.timezone.utc)
            self.assertEqual(target, issue + dt.timedelta(hours=horizon))


if __name__ == "__main__":
    unittest.main()
