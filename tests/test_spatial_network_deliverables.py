import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site/data/research/spatial-network/network-stations.geojson"
OVERLAP = ROOT / "site/data/research/mchl1-usgs-overlap/comparison.json"
MAP = ROOT / "site/data/research/spatial-network/network-map.html"
MEMO = ROOT / "docs/spatial-forcing-feasibility.md"

class SpatialNetworkDeliverableTests(unittest.TestCase):
    def test_geojson_has_existing_and_candidate_network(self):
        doc = json.loads(DATA.read_text())
        self.assertEqual(doc["type"], "FeatureCollection")
        ids = {f["properties"]["station_id"] for f in doc["features"]}
        self.assertTrue({"DENL1", "NWCL1", "MDLL1", "MCHL1", "MAUL1"} <= ids)
        self.assertTrue({"FREL1", "BCFL1", "LKPL1", "WEGL1", "85575LA", "073802302", "KASD"} <= ids)
        for feature in doc["features"]:
            coords = feature["geometry"]["coordinates"]
            self.assertEqual(feature["geometry"]["type"], "Point")
            self.assertTrue(-92 <= coords[0] <= -89 and 29 <= coords[1] <= 32)
            for key in ("family", "network_role", "source_url", "independence_note", "datum_status", "exposure"):
                self.assertIn(key, feature["properties"])

    def test_duplicate_sources_render_as_shadow_and_place_labels_in_the_right_lakes(self):
        doc = json.loads(DATA.read_text())
        by_id = {f["properties"]["station_id"]: f for f in doc["features"]}
        self.assertEqual(by_id["073802302"]["properties"]["network_role"], "shadow_duplicate")
        html = MAP.read_text()
        self.assertIn("label('Lake Pontchartrain',30.23,-90.22)", html)
        self.assertIn("label('Lake Maurepas',30.18,-90.58)", html)

    def test_monthly_archive_and_hads_rain_elements_are_represented(self):
        memo = MEMO.read_text()
        self.assertIn("130 monthly hourly files", memo)
        self.assertIn("4,137,183", memo)
        self.assertIn("full UTC calendar months", memo)
        doc = json.loads(DATA.read_text())
        by_id = {f["properties"]["station_id"]: f["properties"] for f in doc["features"]}
        self.assertIn("PC", by_id["PVLL1"]["elements"])
        self.assertIn("US", by_id["PVLL1"]["elements"])
        self.assertIn("UD", by_id["TSPL1"]["elements"])
        self.assertIn("PC", by_id["TSPL1"]["elements"])

    def test_embedded_map_features_match_download_layer(self):
        html = MAP.read_text()
        embedded = html.split("const stations=", 1)[1].split(";\nconst map=", 1)[0]
        self.assertEqual(json.loads(embedded), json.loads(DATA.read_text())["features"])

    def test_pass_overlap_counts_match_project_archive(self):
        memo = MEMO.read_text()
        doc = json.loads(DATA.read_text())
        pass_note = next(f["properties"]["qc_status"] for f in doc["features"] if f["properties"]["station_id"] == "MCHL1")
        project = json.loads(OVERLAP.read_text())
        counts = [period["comparison"]["matched_exact_valid_times"] for period in project["periods"]]
        self.assertEqual(counts, [373, 479])
        self.assertIn("373 valid times", memo)
        self.assertIn("479 valid times", memo)
        self.assertIn("852 paired times total", memo)
        self.assertIn("373 valid times", pass_note)
        self.assertIn("479", pass_note)

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
