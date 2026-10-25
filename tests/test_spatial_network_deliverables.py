import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site/data/research/spatial-network/network-stations.geojson"
MAP = ROOT / "site/data/research/spatial-network/network-map.html"
MEMO = ROOT / "docs/spatial-forcing-feasibility.md"

class SpatialNetworkDeliverableTests(unittest.TestCase):
    def test_geojson_has_existing_and_candidate_network(self):
        doc = json.loads(DATA.read_text())
        self.assertEqual(doc["type"], "FeatureCollection")
        ids = {f["properties"]["station_id"] for f in doc["features"]}
        self.assertTrue({"DENL1", "NWCL1", "MDLL1", "MCHL1", "MAUL1"} <= ids)
        self.assertTrue({"FREL1", "BCFL1", "LKPL1", "WEGL1", "85575LA", "073802302"} <= ids)
        for feature in doc["features"]:
            coords = feature["geometry"]["coordinates"]
            self.assertEqual(feature["geometry"]["type"], "Point")
            self.assertTrue(-92 <= coords[0] <= -89 and 29 <= coords[1] <= 32)
            for key in ("family", "network_role", "source_url", "independence_note", "datum_status", "exposure"):
                self.assertIn(key, feature["properties"])

    def test_map_is_static_feasibility_view_with_all_features(self):
        html = MAP.read_text()
        data = json.loads(DATA.read_text())
        self.assertIn("L.tileLayer", html)
        self.assertIn("© OpenStreetMap contributors", html)
        self.assertIn("feasibility only", html.lower())
        self.assertIn("not model inputs", html.lower())
        for feature in data["features"]:
            self.assertIn(feature["properties"]["station_id"], html)
        self.assertNotIn("fetch(", html.lower())

    def test_memo_covers_scientific_guardrails_and_three_families(self):
        memo = MEMO.read_text().lower()
        for text in ("rainfall and tributary", "wind-field", "spatial lake, pass and river water levels", "datum", "00065", "63160", "event-blocked", "2023+", "receipt", "false-alert", "incremental"):
            self.assertIn(text, memo)
        self.assertIn("https://", memo)

if __name__ == "__main__":
    unittest.main()
