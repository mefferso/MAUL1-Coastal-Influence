import datetime as dt
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import phase6
import phase6_sources

class Phase6SourceTests(unittest.TestCase):
    def test_quality_flags_are_retained_but_rejected_from_features(self):
        self.assertTrue(phase6.quality_is_usable([]))
        self.assertTrue(phase6.quality_is_usable(["P"]))
        self.assertFalse(phase6.quality_is_usable(["R"]))
        self.assertTrue(phase6.quality_is_usable("0,0,0,0"))
        self.assertTrue(phase6.quality_is_usable("0,0"))
        self.assertTrue(phase6.quality_is_usable("P,0"))
        self.assertFalse(phase6.quality_is_usable("0,1,0"))
        self.assertFalse(phase6.quality_is_usable("0,R,0"))
        self.assertFalse(phase6.quality_is_usable("invalid"))

    def test_future_retrieval_cannot_enter_issue_features(self):
        base={"station":"MAUL1","source":"USGS","parameter":"stage","value":2.4,"units":"ft","datum":"gage height",
              "valid_time_utc":"2026-10-22T11:30:00Z","retrieved_utc":"2026-10-22T11:45:00Z","qc":[],"eligible_completed_hour":True}
        future=dict(base,value=8.0,retrieved_utc="2026-10-22T12:30:00Z")
        snapshot={"observations":[base,future]}
        features,_=phase6.feature_snapshot(snapshot,dt.datetime(2026,10,22,12,15,tzinfo=dt.timezone.utc))
        self.assertEqual(features["maul1_stage_native_ft"],2.4)

    def test_coastal_source_can_be_recent_but_miss_model_hour(self):
        issued=dt.datetime(2026,10,22,15,54,tzinfo=dt.timezone.utc)
        hour=dt.datetime(2026,10,22,13,0,tzinfo=dt.timezone.utc)
        index={("NWCL1","water"):{hour:{"value":1.155,"datum":"MLLW","unit":"ft"}}}
        diagnostic=phase6.feature_availability({"nwcl1_residual_mllw_ft":None},index,issued)
        self.assertEqual(diagnostic["expected_latest_bin_utc"],"2026-10-22T14:00:00Z")
        self.assertFalse(diagnostic["stations"]["NWCL1"]["expected_bin_present"])
        self.assertEqual(diagnostic["stations"]["NWCL1"]["lag_from_expected_hours"],1)
        self.assertEqual(diagnostic["missing_features"]["coastal"],["nwcl1_residual_mllw_ft"])

    def test_completed_coastal_hour_is_distinct_from_residual_pair(self):
        issued=dt.datetime(2026,10,22,15,54,tzinfo=dt.timezone.utc)
        hour=dt.datetime(2026,10,22,14,0,tzinfo=dt.timezone.utc)
        index={("NWCL1","water"):{hour:{"value":1.155}},
               ("NWCL1","residual"):{}}
        diagnostic=phase6.feature_availability({"nwcl1_residual_mllw_ft":None},index,issued)
        self.assertTrue(diagnostic["stations"]["NWCL1"]["expected_bin_present"])
        self.assertFalse(diagnostic["stations"]["NWCL1_residual"]["expected_bin_present"])

    def test_source_lookback_covers_72_hour_change_plus_completed_bin(self):
        requested=[]
        def empty(url):
            requested.append(url)
            return (json.dumps({"value":{"timeSeries":[]}}).encode()
                    if "waterservices" in url else json.dumps({"data":[]}).encode(), None)
        phase6_sources.fetch_snapshot(dt.datetime(2026,10,22,16,tzinfo=dt.timezone.utc), empty)
        usgs=[url for url in requested if "waterservices" in url]
        coops=[url for url in requested if "tidesandcurrents" in url]
        self.assertEqual(len(usgs),3)
        self.assertTrue(all("P4D" in url for url in usgs))
        self.assertEqual(len(coops),3)
        self.assertTrue(all("begin_date=20261018" in url for url in coops))

    def test_mchl1_source_is_captured_but_never_used_without_qc(self):
        requested=[]
        def candidate(url):
            requested.append(url)
            if "waterservices" in url:
                return json.dumps({"value":{"timeSeries":[]}}).encode(),None
            if "tidesandcurrents" in url:
                return json.dumps({"data":[]}).encode(),None
            if "hads.py" in url:
                return (b"station,utc_valid,HGIRGZZ\n"
                        b"MCHL1,2026-10-22 14:00,1.25\n"
                        b"MCHL1,2026-10-22 14:15,1.30\n"),None
            raise AssertionError(url)
        snap=phase6_sources.fetch_snapshot(dt.datetime(2026,10,22,16,tzinfo=dt.timezone.utc),candidate)
        self.assertEqual(len([u for u in requested if "hads.py" in u]),1)
        self.assertIn("stations=MCHL1",requested[-1])
        self.assertIn("sts=2026-10-18T16",requested[-1])
        source=next(x for x in snap["sources"] if x["station"]=="MCHL1")
        self.assertEqual(source["status"],"retrieved_unverified")
        self.assertFalse(source["forecast_eligible"])
        self.assertEqual(source["coverage"]["valid_timestamp_count"],2)
        self.assertEqual(source["coverage"]["maximum_gap_minutes"],15)
        self.assertEqual(source["coverage"]["latest_valid_utc"],"2026-10-22T14:15:00Z")
        self.assertGreater(source["coverage"]["latest_age_minutes"],0)
        obs=[o for o in snap["observations"] if o["station"]=="MCHL1"]
        self.assertEqual(len(obs),2)
        self.assertTrue(all(o["qc"]=="unverified" for o in obs))
        self.assertTrue(all(o["datum"]=="HADS native gage height (unverified)" for o in obs))
        self.assertTrue(all(o["response_sha256"]==source["response_sha256"] for o in obs))
        self.assertFalse(phase6.quality_is_usable(obs[0]["qc"]))
        features,_=phase6.feature_snapshot(snap,dt.datetime(2026,10,22,16,30,tzinfo=dt.timezone.utc))
        self.assertIsNone(features.get("mchl1_stage_change_6h_native_ft"))

    def test_mchl1_coverage_empty_and_irregular(self):
        self.assertEqual(phase6_sources.mchl1_coverage([],"2026-10-22T16:00:00Z")["valid_timestamp_count"],0)
        rows=[{"time":"2026-10-22T14:00:00Z"},{"time":"2026-10-22T14:00:00Z"},
              {"time":"2026-10-22T14:45:00Z"}]
        result=phase6_sources.mchl1_coverage(rows,"2026-10-22T16:00:00Z")
        self.assertEqual(result["valid_timestamp_count"],2)
        self.assertEqual(result["maximum_gap_minutes"],45)
        self.assertEqual(result["observation_span_hours"],.75)
        self.assertEqual(result["latest_age_minutes"],75)

    def test_wrong_mchl1_station_is_rejected_and_isolated(self):
        def bad(url):
            if "waterservices" in url:
                return json.dumps({"value":{"timeSeries":[]}}).encode(),None
            if "hads.py" in url:
                return b"station,utc_valid,HGIRGZZ\n85420LA,2026-10-22 14:00,1.25\n",None
            return json.dumps({"data":[]}).encode(),None
        snap=phase6_sources.fetch_snapshot(dt.datetime(2026,10,22,16,tzinfo=dt.timezone.utc),bad)
        self.assertEqual(next(x for x in snap["sources"] if x["station"]=="MCHL1")["status"],"error")
        self.assertFalse(any(o["station"]=="MCHL1" for o in snap["observations"]))

    def test_empty_source_responses_are_explicit(self):
        def empty(url):
            return (json.dumps({"value":{"timeSeries":[]}}).encode() if "waterservices" in url else json.dumps({"data":[]}).encode(),None)
        result=phase6_sources.fetch_snapshot(dt.datetime(2026,10,22,12,tzinfo=dt.timezone.utc),empty)
        self.assertEqual(len(result["sources"]),7)
        self.assertTrue(all(x["status"] in {"empty","error"} for x in result["sources"]))
        self.assertEqual(result["mchl1_substitution"],"prohibited; USACE 85420 excluded")

if __name__ == "__main__": unittest.main()
