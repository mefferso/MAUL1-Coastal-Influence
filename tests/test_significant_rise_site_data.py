import json
import pathlib
import unittest
import csv

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import build_significant_rise_site_data as builder


ROOT = pathlib.Path(__file__).resolve().parents[1]


class SignificantRiseSiteDataTests(unittest.TestCase):
    def test_compact_payload_is_reproducible_and_has_four_selected_cases(self):
        expected = builder.build(ROOT)
        committed = json.loads((ROOT / "site/data/research/significant-rise.json").read_text())
        self.assertEqual(committed, expected)
        self.assertEqual(committed["schema"], "maul1.significant-rise-model-lab.v1")
        self.assertEqual(committed["evidence_label"], "Retrospective / Development Evidence")
        self.assertEqual(len(committed["representative_events"]), 4)

    def test_provenance_datum_and_no_leakage_safeguards_are_explicit(self):
        report = builder.build(ROOT)["summary"]
        safeguards = report["causal_safeguards"]
        self.assertTrue(safeguards["no_future_observation_features_used"])
        self.assertTrue(safeguards["no_new_models_trained"])
        self.assertEqual(safeguards["maul1_datum"], "native gage height")
        self.assertEqual(safeguards["nwcl1_residual_datum"], "MLLW")
        self.assertFalse(report["provenance"]["prospective_archives_modified"])
        self.assertEqual(report["definition_reproduction"]["phase6_groups"], 109)
        self.assertEqual(report["definition_reproduction"]["detected_groups"], 28)
        self.assertEqual(report["definition_reproduction"]["missed_groups"], 81)

    def test_timeline_pairs_preserve_issue_target_alignment_and_gaps(self):
        payload = builder.build(ROOT)
        required = {"issue_time_utc", "valid_time_utc", "issue_maul1_stage_native_ft",
                    "actual_valid_maul1_stage_native_ft", "features", "phase5b_coastal_tidal_stage_native_ft"}
        for event in payload["representative_events"]:
            self.assertTrue(event["timeline_rows"])
            for row in event["timeline_rows"]:
                self.assertTrue(required <= row.keys())
                self.assertLess(row["issue_time_utc"], row["valid_time_utc"])
                self.assertEqual(row["horizon_hours"], 24)
        self.assertIn("source_sha256", payload["summary"]["provenance"])

    def test_rebuilt_event_export_is_complete_not_a_truncated_preview(self):
        path = ROOT / "research/rise-failure-audit/event-diagnostics.csv"
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 109)
        self.assertEqual(rows[0]["event_id"], "rise-001")
        self.assertEqual(rows[-1]["event_id"], "rise-109")
        self.assertNotIn("truncated output", path.read_text()[:200].lower())


if __name__ == "__main__":
    unittest.main()
