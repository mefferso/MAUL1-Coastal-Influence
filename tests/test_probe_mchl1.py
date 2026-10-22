import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import probe_mchl1


class MCHL1ProbeTests(unittest.TestCase):
    def test_endpoint_identity_and_valid_utc_range(self):
        start = dt.datetime(2026, 10, 21, tzinfo=dt.timezone.utc)
        url = probe_mchl1.request_url(start, start + dt.timedelta(hours=24))
        self.assertIn("stations=MCHL1", url)
        self.assertIn("sts=2026-10-21T00%3A00Z", url)
        self.assertNotIn("85420", url)

    def test_candidate_data_never_authorizes_forecast_use(self):
        result=probe_mchl1.assess_response(
            b"station,utc_valid,HGIRGZZ\nMCHL1,2026-10-22T12:00:00Z,1.2\n")
        self.assertEqual(result["station_values"], ["MCHL1"])
        self.assertTrue(result["has_stage_column"])
        self.assertFalse(result["approved_for_forecasting"])

    def test_actual_timestamp_coverage_and_missing_values(self):
        body=(b"station,utc_valid,HGIRGZZ\n"
              b"MCHL1,2026-10-22T12:00:00Z,1.2\n"
              b"MCHL1,2026-10-22T12:15:00Z,M\n"
              b"MCHL1,2026-10-22T12:45:00Z,1.3\n")
        report=probe_mchl1.assess_response(body)
        self.assertEqual(report["valid_timestamp_count"],3)
        self.assertEqual(report["finite_stage_cell_count"],2)
        self.assertEqual(report["max_observed_gap_minutes"],30)
        self.assertEqual(report["observation_span_hours"],.75)
        self.assertEqual(report["latest_valid_utc"],"2026-10-22T12:45:00Z")
        self.assertFalse(report["approved_for_forecasting"])

    def test_empty_and_wrong_station_are_not_approved(self):
        self.assertFalse(probe_mchl1.assess_response(b"")["approved_for_forecasting"])
        result=probe_mchl1.assess_response(b"station,utc_valid,HGIRGZZ\n85420LA,2026-10-22T12:00:00Z,1.2\n")
        self.assertFalse(result["station_id_matches"])
        self.assertFalse(result["approved_for_forecasting"])


if __name__ == "__main__":
    unittest.main()
