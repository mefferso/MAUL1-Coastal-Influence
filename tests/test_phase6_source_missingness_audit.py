import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_phase6_source_missingness as audit


class Phase6SourceMissingnessAuditTests(unittest.TestCase):
    def test_reports_source_sentinels_qc_and_residual_pair_eligibility(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            examples = {
                "MAUL1": [{"station":"MAUL1","source":"USGS NWIS IV","variable":"stage","time":"2026-01-01T00:00:00Z","value":-999999,"unit":"ft","datum":"gage height","quality":["A"]}],
                "DENL1": [{"station":"DENL1","source":"USGS NWIS IV","variable":"discharge","time":"2026-01-01T00:00:00Z","value":10,"unit":"cfs","datum":"native","quality":["A"]}],
                "MDLL1": [{"station":"MDLL1","source":"USGS NWIS IV","variable":"stage","time":"2026-01-01T00:00:00Z","value":1,"unit":"ft","datum":"gage height","quality":["A"]}],
                "NWCL1": [
                    {"station":"NWCL1","source":"NOAA CO-OPS 8761927","variable":"water","time":"2026-01-01T00:00:00Z","value":1.0,"unit":"ft","datum":"MLLW","quality":"0,0,0,0"},
                    {"station":"NWCL1","source":"NOAA CO-OPS 8761927","variable":"water","time":"2026-01-01T00:00:00Z","value":1.1,"unit":"ft","datum":"MLLW","quality":"1,0,0,0"},
                    {"station":"NWCL1","source":"NOAA CO-OPS 8761927","variable":"prediction","time":"2026-01-01T00:00:00Z","value":0.5,"unit":"ft","datum":"MLLW","quality":""},
                ],
                "MCHL1": [{"station":"MCHL1","source":"HADS","variable":"stage","time":"2026-01-01T00:00:00Z","value":9999999.0,"unit":"ft","datum":"unverified","quality":"unverified"}],
                "NWCL1-NDBC": [{"station":"NWCL1-NDBC","source":"NDBC","variable":"wind","time":"2026-01-01T00:00:00Z","value":192.440605,"unit":"knots","datum":"none","quality":"NDBC standard met"}],
            }
            for station, rows in examples.items():
                path = root / "site/data/history/raw" / station / "2026-01.json.gz"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(gzip.compress(json.dumps({"rows": rows}).encode(), mtime=0))

            result = audit.audit_source_missingness(root)

        self.assertEqual(result["sentinel_counts"]["usgs_negative_numeric"], 1)
        self.assertEqual(result["sentinel_counts"]["hads_exact_missing"], 1)
        self.assertEqual(result["sentinel_counts"]["ndbc_speed_or_gust_99_mps"], 1)
        self.assertEqual(result["nwcl1_residual_pairing"]["exact_mllw_pairs"], 1)
        self.assertEqual(result["nwcl1_residual_pairing"]["qc_eligible_exact_pairs"], 1)
        self.assertEqual(result["nwcl1_residual_pairing"]["flagged_water_rows"], 1)


if __name__ == "__main__":
    unittest.main()
