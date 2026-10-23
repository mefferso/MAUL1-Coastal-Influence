import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from scripts.probe_mchl1_usgs_overlap import hads_rows, hads_quality_metadata, usgs_rows, usgs_quality_metadata, compare, reporting_intervals, usgs_query_date_bounds, retry_after_seconds, validate_window

class OverlapTests(unittest.TestCase):
    def test_long_span_mode_accepts_multiyear_request_but_keeps_short_probe_bounds(self):
        self.assertTrue(validate_window(dt.date(2022, 5, 1), dt.date(2026, 10, 1), allow_long=True))
        self.assertFalse(validate_window(dt.date(2022, 5, 1), dt.date(2026, 10, 1)))
        self.assertFalse(validate_window(dt.date(2022, 5, 1), dt.date(2030, 1, 1), allow_long=True))

    def test_hads_rejects_wrong_station(self):
        with self.assertRaises(ValueError):
            hads_rows(b"station,utc_valid,HGIRGZZ\nOTHER,2026-09-01 00:00:00,1.1\n")

    def test_hads_quality_metadata_counts_provider_qualifiers_without_interpreting_them(self):
        body=b"station,utc_valid,HGIRGZZ,qc\nMCHL1,2026-09-01 00:00:00,1.1,A\nMCHL1,2026-09-01 00:15:00,1.2,\n"
        result=hads_quality_metadata(body)
        self.assertEqual(result["raw_row_count"],2)
        self.assertEqual(result["qualifier_value_counts"]["qc"],{"<empty>":1,"A":1})

    def test_hads_missing_sentinel_is_counted_but_never_a_stage(self):
        body=b"station,utc_valid,HGIRGZZ\nMCHL1,2026-09-01 00:00:00,1.1\nMCHL1,2026-09-01 00:15:00,9999999.0\n"
        self.assertEqual(len(hads_rows(body)),1)
        self.assertEqual(hads_quality_metadata(body)["missing_sentinel_rows"],1)
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

    def test_comparison_reports_yearly_agreement_and_missingness_summaries(self):
        first=dt.datetime(2022,12,31,23,0,tzinfo=dt.timezone.utc)
        second=dt.datetime(2023,1,1,0,0,tzinfo=dt.timezone.utc)
        result=compare({first:1.0,second:1.1},{first:1.0,second:1.0},first,second+dt.timedelta(hours=1))
        self.assertEqual(result["calendar_years"]["2022"]["matched_exact_valid_times"],1)
        self.assertEqual(result["calendar_years"]["2023"]["matched_exact_valid_times"],1)
        self.assertEqual(result["calendar_years"]["2023"]["exact_value_agreement_count"],0)
        self.assertEqual(result["calendar_years"]["2023"]["median_native_stage_difference_ft"],0.1)

    def test_reporting_summary_counts_missing_window_edge_slots(self):
        start=dt.datetime(2026,9,1,tzinfo=dt.timezone.utc)
        end=start+dt.timedelta(hours=1)
        values={start+dt.timedelta(minutes=15*i):1.0 for i in (1,2,3)}
        result=reporting_intervals(values,start,end)
        self.assertEqual(result["expected_window_readings"],4)
        self.assertEqual(result["missing_window_readings"],1)
        self.assertEqual(result["window_coverage_percent"],75.0)

    def test_usgs_site_local_query_is_padded_around_exact_utc_window(self):
        self.assertEqual(usgs_query_date_bounds(dt.date(2022,12,20),dt.date(2022,12,25)),
                         ("2022-12-19","2022-12-25"))

    def test_hads_rate_limit_delay_uses_retry_after_or_bounded_backoff(self):
        self.assertEqual(retry_after_seconds({"Retry-After":"45"},0),45)
        self.assertEqual(retry_after_seconds({},0),60)
        self.assertEqual(retry_after_seconds({},1),120)
        self.assertEqual(retry_after_seconds({"Retry-After":"900"},0),180)
    def test_no_interpolation(self):
        a={dt.datetime(2026,9,1,tzinfo=dt.timezone.utc):1.0}
        b={dt.datetime(2026,9,1,0,15,tzinfo=dt.timezone.utc):1.0}
        self.assertEqual(compare(a,b)["matched_exact_valid_times"],0)

    def test_usgs_quality_metadata_preserves_qualifier_counts(self):
        payload=b'{"value":{"timeSeries":[{"sourceInfo":{"siteCode":[{"value":"073802302"}]},"variable":{"variableCode":[{"value":"00065"}]},"values":[{"value":[{"dateTime":"2026-09-01T00:00:00Z","value":"1.0","qualifiers":["P"]},{"dateTime":"2026-09-01T01:00:00Z","value":"1.1","qualifiers":[]}]}]}]}}'
        result=usgs_quality_metadata(payload)
        self.assertEqual(result["raw_row_count"],2)
        self.assertEqual(result["qualifier_value_counts"],{"<none reported>":1,"P":1})

    def test_offline_raw_reanalysis_preserves_provenance_and_excludes_hads_sentinel(self):
        from scripts.probe_mchl1_usgs_overlap import run_window
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"2026-09-01_2026-09-05_mchl1.csv").write_text(
                "station,utc_valid,HGIRGZZ\nMCHL1,2026-09-01 00:00:00,1.0\n"
                "MCHL1,2026-09-01 00:15:00,9999999.0\n")
            payload={"value":{"timeSeries":[{"sourceInfo":{"siteCode":[{"value":"073802302"}]},
                "variable":{"variableCode":[{"value":"00065"}]},"values":[{"value":[
                    {"dateTime":"2026-09-01T00:00:00Z","value":"1.0","qualifiers":["A"]}]}]}]}}
            (root/"2026-09-01_2026-09-05_usgs_073802302.json").write_text(json.dumps(payload))
            report=run_window("2026-09-01","2026-09-05",raw_input_dir=root)
        self.assertEqual(report["comparison"]["matched_exact_valid_times"],1)
        self.assertEqual(report["sources"]["MCHL1"]["quality_metadata"]["missing_sentinel_rows_in_window"],1)

if __name__=="__main__":
    unittest.main()
