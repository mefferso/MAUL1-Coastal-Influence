import datetime as dt
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import phase6
import phase6_sources

class Phase6SourceTests(unittest.TestCase):
    def test_future_retrieval_cannot_enter_issue_features(self):
        base={"station":"MAUL1","source":"USGS","parameter":"stage","value":2.4,"units":"ft","datum":"gage height",
              "valid_time_utc":"2026-10-22T11:30:00Z","retrieved_utc":"2026-10-22T11:45:00Z","qc":[],"eligible_completed_hour":True}
        future=dict(base,value=8.0,retrieved_utc="2026-10-22T12:30:00Z")
        snapshot={"observations":[base,future]}
        features,_=phase6.feature_snapshot(snapshot,dt.datetime(2026,10,22,12,15,tzinfo=dt.timezone.utc))
        self.assertEqual(features["maul1_stage_native_ft"],2.4)

    def test_empty_source_responses_are_explicit(self):
        def empty(url):
            return (json.dumps({"value":{"timeSeries":[]}}).encode() if "waterservices" in url else json.dumps({"data":[]}).encode(),None)
        result=phase6_sources.fetch_snapshot(dt.datetime(2026,10,22,12,tzinfo=dt.timezone.utc),empty)
        self.assertEqual(len(result["sources"]),7)
        self.assertTrue(all(x["status"] in {"empty","unavailable"} for x in result["sources"]))
        self.assertEqual(result["mchl1_substitution"],"prohibited; USACE 85420 excluded")

if __name__ == "__main__": unittest.main()
