import datetime as dt
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import phase5a


UTC = dt.timezone.utc
HOUR = dt.timedelta(hours=1)


def row(stamp, value, *, station='MAUL1', variable='stage', unit='ft', datum='gage height',
        coverage=1, missing=False, excluded=False):
    return dict(time=phase5a.iso(stamp), station=station, variable=variable,
                unit=unit, datum=datum, value=value, coverage=coverage,
                missing=missing, phase4_quality_excluded=excluded)


class Phase5ATests(unittest.TestCase):
    def test_issue_uses_only_completed_hourly_bins(self):
        issue = dt.datetime(2020, 1, 1, 6, tzinfo=UTC)
        index = {('MAUL1', 'stage'): {
            issue - HOUR: row(issue - HOUR, 2.0),
            issue: row(issue, 9.0),
        }}
        self.assertEqual(phase5a.latest_completed_bin(index, ('MAUL1', 'stage'), issue)['value'], 2.0)

    def test_invalid_or_unverified_observation_is_preserved_as_missing(self):
        issue = dt.datetime(2020, 1, 1, 6, tzinfo=UTC)
        index = {('MAUL1', 'stage'): {
            issue - HOUR: row(issue - HOUR, 2.0, datum=''),
        }}
        self.assertIsNone(phase5a.latest_completed_bin(index, ('MAUL1', 'stage'), issue))

    def test_stage_change_requires_same_native_datum_and_exact_lag(self):
        issue = dt.datetime(2020, 1, 1, 6, tzinfo=UTC)
        index = {('MAUL1', 'stage'): {
            issue - HOUR: row(issue - HOUR, 2.5),
            issue - 7 * HOUR: row(issue - 7 * HOUR, 2.0, datum='gage height 2'),
        }}
        self.assertIsNone(phase5a.change_at_issue(index, ('MAUL1', 'stage'), issue, 6))
        index[('MAUL1', 'stage')][issue - 7 * HOUR]['datum'] = 'gage height'
        self.assertEqual(phase5a.change_at_issue(index, ('MAUL1', 'stage'), issue, 6), 0.5)

    def test_issue_features_are_invariant_to_future_mutation(self):
        issue = dt.datetime(2020, 1, 1, 6, tzinfo=UTC)
        index = {('MAUL1', 'stage'): {
            issue - 2 * HOUR: row(issue - 2 * HOUR, 2.0),
            issue - HOUR: row(issue - HOUR, 2.2),
        }}
        before = phase5a.issue_features(index, issue)
        index[('MAUL1', 'stage')][issue + HOUR] = row(issue + HOUR, 1000.0)
        after = phase5a.issue_features(index, issue)
        self.assertEqual(before, after)

    def test_persistence_is_native_latest_stage(self):
        self.assertEqual(phase5a.persistence_forecast(2.375), 2.375)

    def test_trend_forecast_is_shrunk_and_training_bounded(self):
        self.assertEqual(phase5a.trend_forecast(2.0, 0.6, 6, 12, shrink=0.25, cap_per_hour=0.05), 2.15)

    def test_temporal_split_applies_feature_lookback_and_embargo(self):
        boundary = dt.datetime(2023, 1, 1, tzinfo=UTC)
        issue = boundary + dt.timedelta(hours=144)
        self.assertEqual(phase5a.assign_split(issue, issue + 6 * HOUR), 'holdout')
        self.assertEqual(phase5a.assign_split(boundary - dt.timedelta(days=5), boundary - dt.timedelta(days=4)), 'calibration')
        self.assertEqual(phase5a.assign_split(boundary + HOUR, boundary + 7 * HOUR), 'excluded_split_seam')

    def test_metrics_and_zero_persistence_denominator(self):
        metrics = phase5a.metric_bundle([1.0, 2.0], [2.0, 2.0], persistence=[3.0, 2.0])
        self.assertEqual(metrics['mae_ft'], 0.5)
        self.assertEqual(metrics['bias_ft'], 0.5)
        self.assertAlmostEqual(metrics['mae_skill_vs_persistence'], 0.5)
        zero = phase5a.metric_bundle([1.0, 1.0], [1.0, 1.0], persistence=[1.0, 1.0])
        self.assertIsNone(zero['mae_skill_vs_persistence'])
        self.assertEqual(zero['skill_status'], 'zero_persistence_mae')

    def test_paired_comparison_uses_identical_issues(self):
        rows = [
            {'issue_time_utc': 'a', 'actual_gage_height_ft': 1.0, 'persistence': 1.0, 'model': 2.0},
            {'issue_time_utc': 'b', 'actual_gage_height_ft': 2.0, 'persistence': 2.0, 'model': None},
            {'issue_time_utc': 'c', 'actual_gage_height_ft': None, 'persistence': 3.0, 'model': 3.0},
        ]
        paired = phase5a.paired_rows(rows, ['persistence', 'model'])
        self.assertEqual([r['issue_time_utc'] for r in paired], ['a'])

    def test_ridge_fit_reports_imputation_instead_of_hiding_missing_inputs(self):
        import numpy as np
        x = np.asarray([[0.0, 1.0], [1.0, np.nan], [2.0, 3.0], [3.0, np.nan]])
        y = np.asarray([0.0, 1.0, 2.0, 3.0])
        model = phase5a.fit_ridge(x, y, ['stage_change', 'river_change'], alpha=1.0)
        pred, missing_count = phase5a.predict_ridge(model, np.asarray([[4.0, np.nan]]))
        self.assertTrue(math.isfinite(float(pred[0])))
        self.assertEqual(int(missing_count[0]), 1)
        self.assertIn('river_change', model['feature_names'])


if __name__ == '__main__':
    unittest.main()
