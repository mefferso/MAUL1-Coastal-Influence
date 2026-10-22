import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import phase5b


UTC = dt.timezone.utc


class Phase5BTests(unittest.TestCase):
    def test_harmonic_features_are_utc_periodic_and_aligned(self):
        t = dt.datetime(2020, 1, 1, 0, tzinfo=UTC)
        a = phase5b.harmonic_features(t)
        b = phase5b.harmonic_features(t + dt.timedelta(hours=24))
        self.assertLess(abs(a['diurnal_sin'] - b['diurnal_sin']), 1e-10)
        c = phase5b.harmonic_features(t + dt.timedelta(hours=12.42))
        self.assertLess(abs(a['semidiurnal_sin'] - c['semidiurnal_sin']), 1e-10)
        self.assertEqual(set(a), {'diurnal_sin', 'diurnal_cos', 'semidiurnal_sin',
                                  'semidiurnal_cos', 'spring_neap_sin', 'spring_neap_cos'})

    def test_astronomical_valid_time_archive_is_not_proven_issue_time_available(self):
        finding = phase5b.assess_prediction_availability({
            'source': 'NOAA CO-OPS Data API', 'product': 'predictions',
            'valid_time_coverage': ['2016-01-01T00:00:00Z'],
        })
        self.assertFalse(finding['verified_advance_availability'])
        self.assertIn('capture', finding['reason'].lower())

    def test_astronomical_input_requires_same_documented_datum(self):
        self.assertTrue(phase5b.datum_compatible({'unit': 'ft', 'datum': 'MLLW', 'value': 1.0}, 'ft', 'MLLW'))
        self.assertFalse(phase5b.datum_compatible({'unit': 'ft', 'datum': 'gage height'}, 'ft', 'MLLW'))
        self.assertFalse(phase5b.datum_compatible({'unit': 'ft', 'datum': ''}, 'ft', 'MLLW'))

    def test_forecast_valid_time_is_issue_plus_horizon(self):
        issue = dt.datetime(2024, 2, 1, 6, tzinfo=UTC)
        self.assertEqual(phase5b.forecast_valid_time(issue, 12), issue + dt.timedelta(hours=12))

    def test_gating_uses_only_issue_features_and_not_future_outcomes(self):
        result = phase5b.gated_forecast(2.0, 0.02, threshold=0.05, advanced=2.4)
        self.assertEqual(result, (2.0, 'persistence'))
        self.assertEqual(phase5b.gated_forecast(2.0, 0.08, threshold=0.05, advanced=2.4), (2.4, 'advanced'))
        self.assertEqual(phase5b.gated_forecast(2.0, None, threshold=0.05, advanced=2.4),
                         (2.0, 'persistence_missing_issue_feature'))
        self.assertEqual(phase5b.gated_forecast(2.0, 0.08, threshold=0.05, advanced=None),
                         (2.0, 'persistence_missing_advanced'))

    def test_rising_bias_reports_signed_and_underforecast_tail(self):
        result = phase5b.rising_bias_metrics([2.2, 3.0, 2.5], [2.0, 2.6, 2.6])
        self.assertEqual(result['n'], 3)
        self.assertAlmostEqual(result['mean_signed_error_ft'], -1.0 / 6)
        self.assertAlmostEqual(result['underforecast_fraction'], 2 / 3)
        self.assertAlmostEqual(result['mean_underforecast_magnitude_ft'], 0.3)

    def test_missing_issue_stage_is_not_classified_as_outcome_rising(self):
        self.assertFalse(phase5b.is_rising_outcome({'actual': 2.0, 'maul1_stage_native_ft': None}))

    def test_primary_report_excludes_retrospective_astronomical_sensitivity(self):
        self.assertNotIn('maul1_astro_retrospective', phase5b.causal_report_methods(
            {'maul1_periodic': {}, 'maul1_astro_retrospective': {}}))

    def test_zero_native_stage_is_not_treated_as_missing_when_adding_delta(self):
        self.assertEqual(phase5b.add_delta_to_stage(0.0, 0.25), 0.25)

    def test_interval_calibration_excludes_missing_model_predictions(self):
        result = phase5b.empirical_interval_radius([1.0, 2.0], [1.5, float('nan')])
        self.assertEqual(result, {'half_width_ft': 0.5, 'calibration_residual_n': 1})

    def test_event_group_metrics_collapse_overlapping_forecasts_per_event(self):
        rows = [
            {'event_id': 'a', 'actual': 1.0, 'forecast': 1.0},
            {'event_id': 'a', 'actual': 2.0, 'forecast': 1.0},
            {'event_id': 'b', 'actual': 4.0, 'forecast': 2.0},
        ]
        result = phase5b.event_group_metrics(rows)
        self.assertEqual(result['event_count'], 2)
        self.assertEqual(result['events']['a']['forecast_count'], 2)
        self.assertEqual(result['events']['a']['mae_ft'], 0.5)

    def test_annual_metrics_keep_years_as_separate_verification_groups(self):
        rows = [
            {'issue_time': dt.datetime(2023, 1, 1, tzinfo=UTC), 'actual': 1.0, 'persistence_ft': 1.0, 'model': 2.0},
            {'issue_time': dt.datetime(2024, 1, 1, tzinfo=UTC), 'actual': 2.0, 'persistence_ft': 2.0, 'model': 2.5},
        ]
        self.assertEqual(list(phase5b.annual_metrics(rows, ['model'])), ['2023', '2024'])

    def test_training_targets_end_before_embargo_cutoff(self):
        boundary = dt.datetime(2023, 1, 1, tzinfo=UTC)
        cutoff = boundary-dt.timedelta(hours=72)
        rows = [
            {'split': 'calibration', 'actual': 1., 'target_time': boundary-dt.timedelta(hours=73), 'maul1_stage_native_ft': 1.},
            {'split': 'calibration', 'actual': 1., 'target_time': boundary-dt.timedelta(hours=72), 'maul1_stage_native_ft': 1.},
            {'split': 'calibration', 'actual': 1., 'target_time': boundary-dt.timedelta(hours=71), 'maul1_stage_native_ft': 1.},
        ]
        self.assertEqual(phase5b._training_rows(rows, cutoff), [0])

    def test_case_study_builder_compares_aligned_phase5a_and_phase5b_forecasts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            case_dir = root / 'site/data/history/phase5a'
            case_dir.mkdir(parents=True)
            issue = '2020-01-01T00:00:00Z'
            (case_dir / 'case-studies.json').write_text(json.dumps([{
                'case_id': 'beta', 'calibration_or_holdout': 'calibration (not independent)',
                'horizons': {'6': {'issue_times_utc': [issue], 'actual_gage_height_ft': [2.0],
                                   'forecasts': {'persistence': [1.0], 'maul1_only': [1.5],
                                                 'maul1_plus_coastal': [1.4]}}}
            }]))
            row = {'issue_time': dt.datetime(2020, 1, 1, tzinfo=UTC), 'actual': 2.0,
                   'maul1_stage_native_ft': 1.0, 'maul1_plus_river_ft': 1.6,
                   'maul1_periodic': 1.7, 'maul1_coastal_tidal': 1.6,
                   'full_multivariable': 1.5, 'gated_full': 1.4}
            result = phase5b._case_studies(root, {6: [row], 24: []})
            self.assertAlmostEqual(result['priority_cases'][0]['horizons']['6']['comparison_metrics']
                                   ['phase5b_full']['mae_ft'], 0.5)

    def test_block_bootstrap_is_deterministic(self):
        args = ([1., 2., 3., 2., 1.], [1.2, 1.8, 3.4, 2., .9])
        self.assertEqual(phase5b.block_bootstrap_mae(*args, seed=5, replicates=25, block=2),
                         phase5b.block_bootstrap_mae(*args, seed=5, replicates=25, block=2))


if __name__ == '__main__':
    unittest.main()
