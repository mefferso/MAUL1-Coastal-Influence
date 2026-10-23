import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_mchl1_model_support as audit


class CoefficientMappingTests(unittest.TestCase):
    def test_maps_value_and_missingness_coefficients_through_active_mask(self):
        model = {
            "feature_names": ["x", "mchl1_stage_change_6h_native_ft"],
            "active": [True, False, False, True],
            "coefficients": [1.0, 2.5, -3.0],
        }
        self.assertEqual(audit.coefficient_for(model, 1), 0.0)
        self.assertEqual(audit.coefficient_for(model, 1, missingness=True), -3.0)
        self.assertEqual(audit.coefficient_for(model, 0), 2.5)
        self.assertEqual(audit.coefficient_for(model, 0, missingness=True), 0.0)

    def test_models_without_mchl1_are_reported_as_not_in_model(self):
        result = audit.summarize_model_support(
            model_name="phase5a_maul1_only",
            horizon=6,
            model={"feature_names": ["maul1_change_6h"], "active": [True, True], "coefficients": [0.0, 1.0]},
            feature_rows=[{"maul1_change_6h": "0.2"}],
            train_count=1,
        )
        self.assertEqual(result["status"], "no_mchl1_predictors")
        self.assertEqual(result["features"], [])

    def test_extreme_sentinel_derived_changes_are_not_counted_as_usable_support(self):
        result = audit.summarize_model_support(
            model_name="phase5a_coastal",
            horizon=6,
            model={"feature_names": ["mchl1_stage_change_6h_native_ft"],
                   "active": [True, True, True], "coefficients": [0.0, 0.1, 0.0]},
            feature_rows=[
                {"mchl1_stage_change_6h_native_ft": "0.2"},
                {"mchl1_stage_change_6h_native_ft": "4999998.97"},
                {"mchl1_stage_change_6h_native_ft": ""},
            ],
            train_count=3,
        )
        feature = result["features"][0]
        self.assertEqual(feature["observed_rows"], 2)
        self.assertEqual(feature["sentinel_contaminated_rows"], 1)
        self.assertEqual(feature["usable_observed_rows"], 1)


if __name__ == "__main__":
    unittest.main()
