import datetime as dt
import unittest
from scripts.probe_mchl1_usgs_overlap import hads_rows, usgs_rows, compare

class OverlapTests(unittest.TestCase):
    def test_hads_rejects_wrong_station(self):
        with self.assertRaises(ValueError):
            hads_rows(b"station,utc_valid,HGIRGZZ\nOTHER,2026-09-01 00:00:00,1.1\n")
    def test_usgs_parser_and_comparison(self):
        payload=b'{"value":{"timeSeries":[{"sourceInfo":{"siteCode":[{"value":"073802302"}]},"variable":{"variableCode":[{"value":"00065"}]},"values":[{"value":[{"dateTime":"2026-09-01T00:00:00Z","value":"1.0"},{"dateTime":"2026-09-01T06:00:00Z","value":"1.2"}]}]}]}}'
        a=usgs_rows(payload)
        h=hads_rows(b"station,utc_valid,HGIRGZZ\nMCHL1,2026-09-01 00:00:00,3.0\nMCHL1,2026-09-01 06:00:00,3.2\n")
        c=compare(h,a)
        self.assertEqual(c["matched_exact_valid_times"],2)
        self.assertEqual(c["median_native_stage_difference_ft"],2.0)
        self.assertEqual(c["stage_changes"]["6h"]["matched_changes"],1)
        self.assertEqual(c["stage_changes"]["6h"]["median_change_difference_ft"],0)
    def test_no_interpolation(self):
        a={dt.datetime(2026,9,1,tzinfo=dt.timezone.utc):1.0}
        b={dt.datetime(2026,9,1,0,15,tzinfo=dt.timezone.utc):1.0}
        self.assertEqual(compare(a,b)["matched_exact_valid_times"],0)

if __name__=="__main__":
    unittest.main()
