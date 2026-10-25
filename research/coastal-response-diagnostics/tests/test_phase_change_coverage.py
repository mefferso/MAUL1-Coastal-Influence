import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from run_diagnostics import _lag_profiles, _observed_peak_timing, _stage_change


class PhaseChangeCoverageTests(unittest.TestCase):
    def test_sparse_phase_endpoints_do_not_get_reported_as_phase_change(self):
        rows = [
            {"time": "2016-08-11T00:00:00Z", "station": "MAUL1", "variable": "stage", "valid": True,
             "value": 2.0, "unit": "ft", "datum": "gage height"},
            {"time": "2016-08-11T09:00:00Z", "station": "MAUL1", "variable": "stage", "valid": True,
             "value": 3.0, "unit": "ft", "datum": "gage height"},
        ]
        result = _stage_change(rows, "MAUL1", "stage", "within station", expected_hours=24)
        self.assertEqual(result["valid_hours"], 2)
        self.assertAlmostEqual(result["coverage_fraction"], 2 / 24)
        self.assertIsNone(result["change"])

    def test_lag_profile_uses_wind_only_inside_the_declared_source_phase(self):
        case = {"phases": [{"id": "source", "start_utc": "2024-01-01T00:00:00Z",
                             "end_utc": "2024-01-01T06:00:00Z", "role": "forcing", "attribution": "test"}],
                "lag_source_phase_ids": ["source"]}
        base = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
        stamps = [(base + dt.timedelta(hours=hour)).isoformat().replace("+00:00", "Z") for hour in range(0, 160, 6)]
        wind = [{"time": stamp, "integrated_stress_u_proxy_24h_kt2h": 1.0,
                 "integrated_stress_v_proxy_24h_kt2h": 2.0} for stamp in stamps]
        response = [{"time": stamp, "maul1_stage_change_6h_native_ft": float(index),
                     "mdll1_stage_change_6h_ft": 0.0, "nwcl1_residual_change_6h_ft": 0.0,
                     "denl1_discharge_change_6h_cfs": 0.0} for index, stamp in enumerate(stamps)]
        profile = _lag_profiles(case, wind, response)[0]["lag_hours"][0]
        self.assertEqual(profile["targets"]["maul1_stage_change_6h_native_ft"]["eastward"]["paired_6h_blocks"], 1)

    def test_peak_timing_uses_catalog_response_interval_not_preceding_high_stage(self):
        case = {"phases": [{"start_utc": "2024-01-01T00:00:00Z", "end_utc": "2024-01-01T04:00:00Z"}],
                "response_catalog": {"event_id": "test", "onset_utc": "2024-01-01T01:00:00Z",
                                     "recovery_end_utc": "2024-01-01T04:00:00Z"}}
        records = [{"time": f"2024-01-01T{hour:02}:00:00Z", "station": "MAUL1", "variable": "stage",
                    "valid": True, "value": value, "unit": "ft", "datum": "gage height"}
                   for hour, value in enumerate((100.0, 2.0, 3.0, 4.0))]
        result = _observed_peak_timing(case, records, [])
        self.assertEqual(result["maul1_max_native_00065_stage"]["value"], 4.0)
        self.assertEqual(result["maul1_max_native_00065_stage"]["time_utc"], "2024-01-01T03:00:00Z")
        self.assertEqual(result["window_start_utc"], "2024-01-01T01:00:00Z")

    def test_phase_change_is_available_at_eighty_percent_coverage(self):
        rows = [{"time": f"2024-01-01T{hour:02}:00:00Z", "station": "MAUL1", "variable": "stage",
                 "valid": True, "value": 2 + hour, "unit": "ft", "datum": "gage height"}
                for hour in range(8)]
        result = _stage_change(rows, "MAUL1", "stage", "within station", expected_hours=10)
        self.assertEqual(result["coverage_fraction"], 0.8)
        self.assertEqual(result["change"], 7.0)


if __name__ == "__main__":
    unittest.main()
