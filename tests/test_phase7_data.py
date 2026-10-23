import math
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase7_data import audit_archive, build_clean_experiment, clean_record


class Phase7DataTests(unittest.TestCase):
    def test_clean_record_rejects_known_mchl1_missing_sentinel_only(self):
        row = {
            "station": "MCHL1", "variable": "stage", "time": "2024-01-01T00:00:00Z",
            "value": 9999999.0, "unit": "ft", "datum": "HADS native gage height (unverified)",
            "coverage": 4, "missing": False,
        }

        cleaned, reasons = clean_record(row)

        self.assertIsNone(cleaned["value"])
        self.assertTrue(cleaned["missing"])
        self.assertEqual(reasons, ["known_hads_missing_sentinel"])
        self.assertEqual(cleaned["time"], row["time"])
        self.assertEqual(cleaned["datum"], row["datum"])

    def test_clean_record_rejects_hourly_average_contaminated_by_hads_sentinel(self):
        row = {"station": "MCHL1", "variable": "stage", "time": "t", "value": 4999999.985,
               "unit": "ft", "datum": "HADS native gage height (unverified)",
               "coverage": 4, "missing": False}

        cleaned, reasons = clean_record(row)

        self.assertIsNone(cleaned["value"])
        self.assertEqual(reasons, ["hads_sentinel_contaminated_hourly_stage"])


    def test_clean_record_keeps_legitimate_extreme_stage_and_other_station_value(self):
        maul = {"station": "MAUL1", "variable": "stage", "time": "t", "value": 7.19,
                "unit": "ft", "datum": "gage height", "coverage": 1, "missing": False}
        pass_stage = {**maul, "station": "MCHL1", "value": -1.49,
                      "datum": "HADS native gage height (unverified)"}

        self.assertEqual(clean_record(maul), (maul, []))
        self.assertEqual(clean_record(pass_stage), (pass_stage, []))


    def test_clean_record_marks_nonfinite_numbers_missing(self):
        row = {"station": "DENL1", "variable": "stage", "value": math.inf,
               "unit": "ft", "datum": "gage height", "coverage": 1, "missing": False}

        cleaned, reasons = clean_record(row)

        self.assertIsNone(cleaned["value"])
        self.assertTrue(cleaned["missing"])
        self.assertEqual(reasons, ["non_finite_numeric_value"])

    def test_clean_archive_preserves_source_and_counts_duplicate_hour_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            target = root / "clean"
            source.mkdir()
            rows = [
                {"station": "MCHL1", "variable": "stage", "time": "2024-01-01T00:00:00Z",
                 "value": 9999999.0, "unit": "ft", "datum": "unverified", "coverage": 4, "missing": False},
                {"station": "MCHL1", "variable": "stage", "time": "2024-01-01T00:00:00Z",
                 "value": -1.0, "unit": "ft", "datum": "unverified", "coverage": 4, "missing": False},
            ]
            source_file = source / "2024-01.json.gz"
            source_file.write_bytes(gzip.compress(json.dumps({"records": rows}).encode(), mtime=0))
            original = source_file.read_bytes()

            result = build_clean_experiment(source, target)

            self.assertEqual(source_file.read_bytes(), original)
            self.assertEqual(result["cleaned_values_marked_missing"], {"known_hads_missing_sentinel": 1})
            self.assertEqual(result["duplicate_timestamps"]["MCHL1:stage"], 1)
            cleaned = json.loads(gzip.decompress((target / source_file.name).read_bytes()))
            self.assertTrue(cleaned["records"][0]["missing"])
            self.assertEqual(cleaned["records"][1]["value"], -1.0)

    def test_clean_archive_refuses_output_paths_that_can_overwrite_source(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "hourly"
            source.mkdir()
            source_file = source / "2024-01.json.gz"
            source_file.write_bytes(gzip.compress(json.dumps({"records": []}).encode(), mtime=0))
            original = source_file.read_bytes()

            with self.assertRaises(ValueError):
                build_clean_experiment(source, source)
            with self.assertRaises(ValueError):
                build_clean_experiment(source, source / "nested-clean")

            self.assertEqual(source_file.read_bytes(), original)
