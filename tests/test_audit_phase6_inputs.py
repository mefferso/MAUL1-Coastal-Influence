import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_phase6_inputs

class AuditInputTests(unittest.TestCase):
    def test_distinguishes_missing_diagnostics_from_observed_lag(self):
        old={"mode":"authentic","issuance_id":"old","actual_issue_time_utc":"2026-10-22T16:00:00Z","sources":[]}
        new={"mode":"authentic","issuance_id":"new","actual_issue_time_utc":"2026-10-22T17:00:00Z",
             "sources":[{"station":"MCHL1","status":"retrieved_unverified",
                         "observation_count":382,"forecast_eligible":False}],
             "feature_diagnostics":{"stations":{"NWCL1":{"expected_bin_present":False,"lag_from_expected_hours":1},
                                                "NWCL1_residual":{"expected_bin_present":False,"lag_from_expected_hours":1}},
                                    "missing_features":{"river":["mchl1_stage_change_6h_native_ft"],
                                                        "coastal":["nwcl1_residual_mllw_ft"]}}}
        result=audit_phase6_inputs.summarize([new,old,{"mode":"simulation"}])
        self.assertEqual(result["authentic_issuance_count"],2)
        self.assertEqual(result["nwcl1_water_missing_expected_bin_count"],1)
        self.assertEqual(result["mchl1_retrieved_unverified_count"],1)
        self.assertIsNone(result["recent_issuances"][0]["nwcl1_expected_bin_present"])
        self.assertFalse(result["recent_issuances"][1]["mchl1_forecast_eligible"])
        self.assertEqual(result["recent_issuances"][1]["missing_mchl1_features"],["mchl1_stage_change_6h_native_ft"])

if __name__=="__main__":
    unittest.main()
