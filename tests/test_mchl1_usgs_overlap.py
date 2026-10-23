import datetime as dt
import unittest
from scripts.probe_mchl1_usgs_overlap import hads_rows, hads_quality_metadata, usgs_rows, usgs_quality_metadata, compare

class OverlapTests(unittest.TestCase):
    def test_hads_rejects_wrong_station(self):
        with self.assertRaises(ValueError):
            hads_rows(b"station,utc_valid,HGIRGZZ\nOTHER,2026-09-01 00:00:00,1.1\n")

    def test_hads_quality_metadata_counts_provider_qualifiers_without_interpreting_them(self):
        body=b"station,utc_valid,HGIRGZZ,qc\nMCHL1,2026-09-01 00:00:00,1.1,A\nMCHL1,2026-09-01 00:15:00,1.2,\n"
        result=hads_quality_metadata(body)
        self.assertEqual(result["raw_row_count"],2)
        self.assertEqual(result["qualifier_value_counts"]["qc"],{"<empty>":1,"A":1})
    def test_usgs_parser_and_comparison(self):
        payload=b'{"value":{"timeSeries":[{"sourceInfo":{"siteCode":[{"value":"073802302"}]},"variable":{"variableCode":[{"value":"00065"}]},"values":[{"value":[{"dateTime":"2026-09-01T00:00:00Z","value":"1.0"},{"dateTime":"2026-09-01T06:00:00Z","value":"1.2"}]}]}]}}'
        a=usgs_rows(payload)
        h=hads_rows(b"station,utc_valid,HGIRGZZ\nMCHL1,2026-09-01 00:00:00,3.0\nMCHL1,2026-09-01 06:00:00,3.2\n")
        c=compare(h,a)
        self.assertEqual(c["matched_exact_valid_times"],2)
        self.assertEqual(c["median_native_stage_difference_ft"],2.0)
        self.assertEqual(c["stage_changes"]["6h"]["matched_changes"],1)
        self.assertEqual(c["stage_changes"]["6h"]["median_change_difference_ft"],0)
        self.assertEqual(c["source_reporting"]["MCHL1"]["median_interval_minutes"],360)
        self.assertEqual(c["source_reporting"]["USGS-073802302"]["reading_count"],2)

    def test_comparison_reports_interval_gaps_and_half_window_offset_shift(self):
        start=dt.datetime(2026,9,1,tzinfo=dt.timezone.utc)
        hads={start+dt.timedelta(minutes=15*i):v for i,v in enumerate((1.1,1.2,1.3,2.3))}
        usgs={start+dt.timedelta(minutes=15*i):v for i,v in enumerate((1.0,1.1,1.2,1.2))}
        result=compare(hads,usgs)
        self.assertEqual(result["source_reporting"]["MCHL1"]["dominant_interval_minutes"],15)
        self.assertEqual(result["source_reporting"]["MCHL1"]["estimated_missing_between_endpoints"],0)
        self.assertEqual(result["offset_half_window_shift_ft"],0.5)
    def test_no_interpolation(self):
        a={dt.datetime(2026,9,1,tzinfo=dt.timezone.utc):1.0}
        b={dt.datetime(2026,9,1,0,15,tzinfo=dt.timezone.utc):1.0}
        self.assertEqual(compare(a,b)["matched_exact_valid_times"],0)

    def test_usgs_quality_metadata_preserves_qualifier_counts(self):
        payload=b'{"value":{"timeSeries":[{"sourceInfo":{"siteCode":[{"value":"073802302"}]},"variable":{"variableCode":[{"value":"00065"}]},"values":[{"value":[{"dateTime":"2026-09-01T00:00:00Z","value":"1.0","qualifiers":["P"]},{"dateTime":"2026-09-01T01:00:00Z","value":"1.1","qualifiers":[]}]}]}]}}'
        result=usgs_quality_metadata(payload)
        self.assertEqual(result["raw_row_count"],2)
        self.assertEqual(result["qualifier_value_counts"],{"<none reported>":1,"P":1})

if __name__=="__main__":
    unittest.main()
