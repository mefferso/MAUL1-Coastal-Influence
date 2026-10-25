"""Deterministic tests for NWCL1 receipt ingestion; no internet or fake published archive."""
import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import collect_nwcl1_forcing as collector

UTC = dt.timezone.utc


class TestNWCL1Collector(unittest.TestCase):
    def setUp(self):
        self.received = dt.datetime(2026, 10, 25, 13, 0, tzinfo=UTC)

    def test_wind_from_east_produces_westward_u(self):
        payload = {"data": [{"t": "2026-10-25 12:00", "s": "20", "d": "90", "f": "0"}]}
        rows = collector.records_for_payload("wind", payload, self.received, "digest", "url", "raw/x")
        self.assertEqual(len(rows), 2)
        by_var = {r["variable"]: r for r in rows}
        self.assertAlmostEqual(by_var["wind_u"]["value"], -20)
        self.assertAlmostEqual(by_var["wind_v"]["value"], 0, places=5)
        self.assertEqual(by_var["wind_u"]["retrieved_at"], "2026-10-25T13:00:00Z")

    def test_future_time_skipped(self):
        payload = {"data": [{"t": "2026-10-25 14:00", "v": "2.1"}]}
        self.assertEqual(collector.records_for_payload("water_level", payload, self.received, "digest", "url", "raw/x"), [])

    def test_water_datum_explicit(self):
        payload = {"data": [{"t": "2026-10-25 12:00", "v": "2.1"}]}
        rows = collector.records_for_payload("water_level", payload, self.received, "digest", "url", "raw/x")
        self.assertEqual(rows[0]["datum"], "MLLW")

    def test_provider_errors_rejected(self):
        with self.assertRaises(ValueError):
            collector.records_for_payload("wind", {"error": "unavailable"}, self.received, "d", "u", "p")


if __name__ == "__main__":
    unittest.main()
