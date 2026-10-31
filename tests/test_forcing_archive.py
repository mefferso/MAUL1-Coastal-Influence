"""Tests for prospective forcing receipt validation (no network needed)."""
import copy
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import validate_forcing_archive as archive


def sample():
    return {
        "schema_version": "forcing-1",
        "station_id": "NWCL1",
        "source": "NOAA CO-OPS 8761927",
        "variable": "wind_u",
        "unit": "knots",
        "datum": "not_applicable",
        "valid_time": "2026-10-25T12:00:00Z",
        "retrieved_at": "2026-10-25T12:17:00Z",
        "value": -8.5,
        "status": "provisional",
        "raw_id": "noaa-coops:8761927:wind:2026-10-25T12:00Z",
        "qc_flags": [],
    }


class TestForcingArchive(unittest.TestCase):
    def test_valid_receipt(self):
        archive.validate(sample())

    def test_acquisition_mode_is_a_known_archive_class(self):
        row=sample()
        row["acquisition_mode"]="delayed_recovery"
        archive.validate(row)
        row["acquisition_mode"]="guessed_historical"
        with self.assertRaises(ValueError):
            archive.validate(row)

    def test_missing_receipt(self):
        row = sample()
        del row["retrieved_at"]
        with self.assertRaises(ValueError):
            archive.validate(row)

    def test_receipt_before_valid_time(self):
        row = sample()
        row["retrieved_at"] = "2026-10-25T11:00:00Z"
        with self.assertRaises(ValueError):
            archive.validate(row)

    def test_timezone_required(self):
        row = sample()
        row["valid_time"] = "2026-10-25T12:00:00"
        with self.assertRaises(ValueError):
            archive.validate(row)

    def test_no_implicit_unit_conversion(self):
        row = sample()
        row["unit"] = "mph"
        with self.assertRaises(ValueError):
            archive.validate(row)

    def test_missing_values_are_null(self):
        row = sample()
        row["status"] = "missing"
        row["value"] = None
        archive.validate(row)
        row["value"] = -8.5
        with self.assertRaises(ValueError):
            archive.validate(row)

    def test_duplicate_receipt_rejected(self):
        import json
        row = sample()
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "batch.jsonl"
            path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
            with self.assertRaises(ValueError):
                archive.validate_file(path)

    def test_distinct_receipts_permitted(self):
        import json
        row1 = sample()
        row2 = copy.deepcopy(row1)
        row2["retrieved_at"] = "2026-10-25T12:30:00Z"
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "batch.jsonl"
            path.write_text(json.dumps(row1) + "\n" + json.dumps(row2) + "\n")
            self.assertEqual(archive.validate_file(path), 2)

    def test_future_tide_prediction_is_not_an_observation(self):
        row = sample()
        row.update(record_type="prediction", variable="tide_prediction", unit="ft", datum="MLLW",
                   status="predicted", valid_time="2026-10-25T14:00:00Z")
        archive.validate(row)
        row["record_type"] = "observation"
        with self.assertRaises(ValueError):
            archive.validate(row)


if __name__ == "__main__":
    unittest.main()

