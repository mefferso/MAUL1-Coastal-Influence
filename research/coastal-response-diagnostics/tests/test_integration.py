import datetime as dt
import gzip
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from archive_adapter import combine_wind_records, load_hourly_records
from feature_engine import build_response_features, build_wind_features


class ArchiveToFeatureIntegrationTests(unittest.TestCase):
    def test_synthetic_hourly_archive_flows_through_qc_join_and_response_engine(self):
        with tempfile.TemporaryDirectory() as folder:
            records = []
            for hour, speed, direction, u, v, water, prediction in (
                (0, 10.0, 90.0, -5.0, 0.0, 1.0, 0.5),
                (1, 10.0, 90.0, -5.0, 0.0, 2.0, 0.5),
            ):
                stamp = f"2024-01-01T{hour:02}:00:00Z"
                for variable, value, unit in (("wind", speed, "knots"), ("wind_direction", direction, "degrees from"),
                                              ("wind_u", u, "knots"), ("wind_v", v, "knots"),
                                              ("water", water, "ft"), ("prediction", prediction, "ft")):
                    datum = "MLLW" if variable in {"water", "prediction"} else "none"
                    records.append({"time": stamp, "station": "NWCL1", "variable": variable, "value": value,
                                    "unit": unit, "datum": datum, "coverage": 10, "missing": False,
                                    "source": "deterministic synthetic fixture"})
            path = pathlib.Path(folder) / "2024-01.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                json.dump({"schema_version": "test", "records": records}, stream)
            loaded, hashes = load_hourly_records(folder, "2024-01-01T00:00:00Z", "2024-01-01T02:00:00Z")
            winds = build_wind_features(combine_wind_records(loaded), windows=(1,))
            responses = build_response_features(loaded, change_windows=(1,), baseline_hours=1, min_coverage=0.5)
            self.assertEqual(len(hashes), 1)
            self.assertEqual(winds[0]["stress_u_proxy_kt2"], -50.0)
            self.assertAlmostEqual(responses[0]["nwcl1_residual_mllw_ft"], 0.5)
            self.assertAlmostEqual(responses[1]["nwcl1_residual_change_1h_ft"], 1.0)


if __name__ == "__main__":
    unittest.main()
