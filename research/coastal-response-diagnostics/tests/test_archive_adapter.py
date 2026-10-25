import datetime as dt
import gzip
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from archive_adapter import combine_wind_records, load_hourly_records, record_is_usable, normalize_prospective_observation


class ArchiveAdapterTests(unittest.TestCase):
    def test_hourly_source_coverage_below_eighty_percent_is_unusable(self):
        row = {"station": "NWCL1", "variable": "wind", "value": 10.0, "unit": "knots",
               "datum": "none", "coverage": 7, "missing": False}
        self.assertFalse(record_is_usable(row))
        self.assertTrue(record_is_usable({**row, "coverage": 8}))

    def test_month_specific_archive_cadence_accepts_two_valid_bins_when_two_is_the_source_mode(self):
        row = {"station": "MAUL1", "variable": "stage", "value": 2.0, "unit": "ft",
               "datum": "gage height", "coverage": 2, "expected_source_samples": 2, "missing": False}
        self.assertTrue(record_is_usable(row))
        self.assertFalse(record_is_usable({**row, "coverage": 1}))

    def test_wind_join_requires_all_vector_components_at_same_timestamp(self):
        base = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        records = [
            {"time": base, "station": "NWCL1", "variable": "wind", "value": 10.0, "unit": "knots", "datum": "none", "coverage": 10, "missing": False},
            {"time": base, "station": "NWCL1", "variable": "wind_direction", "value": 90.0, "unit": "degrees from", "datum": "none", "coverage": 10, "missing": False},
            {"time": base, "station": "NWCL1", "variable": "wind_u", "value": -9.0, "unit": "knots", "datum": "none", "coverage": 10, "missing": False},
            {"time": base, "station": "NWCL1", "variable": "wind_v", "value": 0.0, "unit": "knots", "datum": "none", "coverage": 10, "missing": False},
        ]
        row = combine_wind_records(records)[0]
        self.assertTrue(row["valid"])
        self.assertEqual((row["speed_knots"], row["direction_from_deg"]), (10.0, 90.0))
        self.assertEqual(combine_wind_records(records[:-1])[0]["valid"], False)

    def test_prospective_adapter_requires_real_receipt_timestamp(self):
        record = {"source_id": "example", "station": "NWCL1", "variable": "wind",
                  "valid_time_utc": "2024-01-01T00:00:00Z", "received_time_utc": "2024-01-01T00:05:00Z",
                  "value": 10.0, "unit": "knots", "datum": "none", "quality_status": "provider_unflagged"}
        normalized = normalize_prospective_observation(record)
        self.assertEqual(normalized["receipt_latency_seconds"], 300.0)
        del record["received_time_utc"]
        with self.assertRaisesRegex(ValueError, "received_time_utc"):
            normalize_prospective_observation(record)

    def test_loader_estimates_month_specific_expected_source_cadence(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = []
            for hour, value, coverage, missing in ((0, 1.0, 2, False), (1, 2.0, 2, False), (2, None, 0, True)):
                rows.append({"time": f"2024-01-01T{hour:02}:00:00Z", "station": "MAUL1", "variable": "stage",
                             "value": value, "unit": "ft", "datum": "gage height", "coverage": coverage,
                             "missing": missing, "source": "fixture"})
            path = pathlib.Path(folder) / "2024-01.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                json.dump({"records": rows}, stream)
            loaded, hashes = load_hourly_records(folder, "2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z")
            stages = [row for row in loaded if row["variable"] == "stage"]
            self.assertEqual([row["expected_source_samples"] for row in stages], [2, 2, 2])
            self.assertEqual([row["valid"] for row in stages], [True, True, False])
            self.assertIn("2024-01.json.gz", hashes)

    def test_mchl1_and_maul1_navd88_are_not_in_response_source_selection(self):
        from archive_adapter import RESPONSE_KEYS
        self.assertNotIn(("MCHL1", "stage"), RESPONSE_KEYS)
        self.assertNotIn(("MAUL1", "elevation"), RESPONSE_KEYS)
        self.assertIn(("MAUL1", "stage"), RESPONSE_KEYS)


if __name__ == "__main__":
    unittest.main()
