import datetime as dt
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from feature_engine import DEFAULT_SECTORS, build_response_features, build_wind_features

UTC = dt.timezone.utc


def wind_record(hour, speed=10.0, direction=90.0, **changes):
    row = {
        "time": (dt.datetime(2024, 1, 1, tzinfo=UTC) + dt.timedelta(hours=hour)).isoformat(),
        "station": "NWCL1",
        "variable": "wind",
        "speed_knots": speed,
        "direction_from_deg": direction,
        "unit": "knots",
        "datum": "none",
        "coverage": 10,
        "valid": True,
    }
    row.update(changes)
    return row


class WindFeatureTests(unittest.TestCase):
    def test_meteorological_direction_maps_to_flow_to_components(self):
        rows = build_wind_features([wind_record(0, 10, 90)], windows=(1,))
        self.assertAlmostEqual(rows[0]["wind_u_east_knots"], -10.0, places=8)
        self.assertAlmostEqual(rows[0]["wind_v_north_knots"], 0.0, places=8)
        self.assertAlmostEqual(rows[0]["stress_u_proxy_kt2"], -100.0, places=8)

    def test_default_east_and_southeast_sectors_are_distinct_at_boundary(self):
        records = [wind_record(0, 10, 112.5)]
        rows = build_wind_features(records, windows=(1,), speed_thresholds=(5,))
        self.assertEqual(rows[0]["duration_easterly_ge5kt_1h"], 0)
        self.assertEqual(rows[0]["duration_southeasterly_ge5kt_1h"], 1)

    def test_hourly_vector_average_is_not_rescaled_to_scalar_mean_speed(self):
        record = wind_record(0, 10, 90, u_east_knots=-5, v_north_knots=0)
        rows = build_wind_features([record], windows=(1,))
        self.assertEqual(rows[0]["wind_u_east_knots"], -5)
        self.assertEqual(rows[0]["stress_u_proxy_kt2"], -50)
        self.assertEqual(rows[0]["directional_persistence_1h"], 0.5)

    def test_directional_integral_requires_coverage_and_does_not_fill_missing_hours(self):
        records = [wind_record(0), wind_record(1, valid=False), wind_record(2)]
        rows = build_wind_features(records, windows=(3,), min_coverage=0.8)
        self.assertIsNone(rows[-1]["integrated_stress_u_proxy_3h_kt2h"])
        complete = build_wind_features([wind_record(0), wind_record(1), wind_record(2)], windows=(3,))
        self.assertAlmostEqual(complete[-1]["integrated_stress_u_proxy_3h_kt2h"], -300.0, places=6)

    def test_directional_duration_and_run_break_at_missing_bin(self):
        records = [wind_record(0), wind_record(1, valid=False), wind_record(2)]
        rows = build_wind_features(records, windows=(3,), sectors={"easterly": (45, 135)}, speed_thresholds=(8,), min_coverage=0.6)
        self.assertEqual(rows[-1]["duration_easterly_ge8kt_3h"], 2)
        self.assertEqual(rows[-1]["longest_run_easterly_ge8kt_3h"], 1)

    def test_circular_direction_shift_handles_north_wrap_and_detects_reversal(self):
        rows = build_wind_features([wind_record(0, 10, 359), wind_record(1, 10, 1), wind_record(2, 10, 181)], windows=(1,))
        self.assertEqual(rows[1]["direction_shift_deg_1h"], 2)
        self.assertTrue(rows[2]["direction_reversal_1h"])
        self.assertEqual(rows[2]["wind_relaxation_knots_1h"], 0)


class WaterResponseTests(unittest.TestCase):
    def test_nwcl1_residual_requires_same_hour_same_datum_pair(self):
        base = dt.datetime(2024, 1, 1, tzinfo=UTC)
        records = []
        for hour in range(3):
            stamp = (base + dt.timedelta(hours=hour)).isoformat()
            records.extend([
                {"time": stamp, "station": "NWCL1", "variable": "water", "value": 1 + hour, "unit": "ft", "datum": "MLLW"},
                {"time": stamp, "station": "NWCL1", "variable": "prediction", "value": 0.5, "unit": "ft", "datum": "NAVD88" if hour == 2 else "MLLW"},
            ])
        rows = build_response_features(records, change_windows=(1,), baseline_hours=2, min_coverage=0.5)
        self.assertAlmostEqual(rows[0]["nwcl1_residual_mllw_ft"], 0.5)
        self.assertIsNone(rows[2]["nwcl1_residual_mllw_ft"])

    def test_residual_columns_reject_same_but_non_mllw_datum(self):
        base = dt.datetime(2024, 1, 1, tzinfo=UTC)
        records = []
        for hour in range(2):
            stamp = (base + dt.timedelta(hours=hour)).isoformat()
            records.extend([
                {"time": stamp, "station": "NWCL1", "variable": "water", "value": 1 + hour, "unit": "ft", "datum": "NAVD88"},
                {"time": stamp, "station": "NWCL1", "variable": "prediction", "value": 0.5, "unit": "ft", "datum": "NAVD88"},
            ])
        rows = build_response_features(records, change_windows=(1,), baseline_hours=1, min_coverage=0.5)
        self.assertIsNone(rows[0]["nwcl1_residual_mllw_ft"])
        self.assertIsNone(rows[1]["nwcl1_residual_change_1h_ft"])

    def test_cross_station_absolute_levels_are_never_subtracted(self):
        base = dt.datetime(2024, 1, 1, tzinfo=UTC)
        records = []
        for hour in range(4):
            stamp = (base + dt.timedelta(hours=hour)).isoformat()
            records.append({"time": stamp, "station": "MDLL1", "variable": "stage", "value": 100 + hour, "unit": "ft", "datum": "gage height"})
            records.append({"time": stamp, "station": "MAUL1", "variable": "stage", "value": 2 + 2 * hour, "unit": "ft", "datum": "gage height"})
        rows = build_response_features(records, change_windows=(1,), baseline_hours=2, min_coverage=0.5)
        self.assertAlmostEqual(rows[-1]["mdll1_stage_change_1h_ft"], 1.0)
        self.assertAlmostEqual(rows[-1]["maul1_stage_change_1h_native_ft"], 2.0)
        self.assertNotIn("mdll1_minus_maul1_ft", rows[-1])

    def test_missing_hours_do_not_create_stage_tendency(self):
        base = dt.datetime(2024, 1, 1, tzinfo=UTC)
        records = [
            {"time": base.isoformat(), "station": "MAUL1", "variable": "stage", "value": 2.0, "unit": "ft", "datum": "gage height"},
            {"time": (base + dt.timedelta(hours=2)).isoformat(), "station": "MAUL1", "variable": "stage", "value": 3.0, "unit": "ft", "datum": "gage height"},
        ]
        rows = build_response_features(records, change_windows=(1,), baseline_hours=2, min_coverage=0.5)
        self.assertIsNone(rows[1]["maul1_stage_change_1h_native_ft"])


if __name__ == "__main__":
    unittest.main()
