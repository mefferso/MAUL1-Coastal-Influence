"""Scientific failure modes: assertions exercise observations, never event names."""
import copy
import datetime as dt
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import evidence

T = dt.datetime(2020, 9, 20, tzinfo=dt.timezone.utc)


def observations(river=True, lake=True, wind=True):
    index = {}
    for station, variable, datum, unit in evidence.SERIES:
        rows = index.setdefault((station, variable), {})
        for h in range(-150, 1):
            stamp = T + dt.timedelta(hours=h)
            active = h >= -18
            value = 0.0
            if station == 'DENL1': value = 15000.0 if river and active else 1000.0
            elif variable == 'residual': value = 1.0 if active else 0.0
            elif station in ('MDLL1', 'MCHL1'): value = 1.0 if lake and active else 0.0
            elif variable == 'wind_u': value = -10.0 if wind and active else 2.0
            elif variable == 'wind_v': value = 0.0
            elif station == 'MAUL1': value = (h+18)/18 if active else 0.0
            rows[stamp] = {'time': evidence.iso(stamp), 'station': station,
                           'variable': variable, 'value': value, 'datum': datum,
                           'unit': unit, 'coverage': 4, 'missing': False}
    return index


class EvidenceTests(unittest.TestCase):
    def test_independent_paths_and_compound_requirements(self):
        self.assertEqual(evidence.assess(observations(), T)['category'], 'Compound-supported')
        self.assertEqual(evidence.assess(observations(river=False), T)['category'], 'Coastal-supported')
        self.assertEqual(evidence.assess(observations(lake=False), T)['category'], 'River-supported')

    def test_no_coastal_label_from_residual_alone(self):
        result = evidence.assess(observations(False, False, False), T)
        self.assertEqual(result['category'], 'Indeterminate')
        self.assertEqual(result['flags']['lake'], 'absent')
        self.assertTrue(result['contradictory'])

    def test_missing_observations_are_unknown(self):
        index = observations(False)
        del index[('MDLL1', 'stage')]
        result = evidence.assess(index, T)
        self.assertEqual(result['flags']['lake'], 'unknown')
        self.assertEqual(result['category'], 'Indeterminate')
        self.assertTrue(result['missing'])

    def test_failed_quality_cannot_support_coast(self):
        index = observations(False)
        for row in index[('MDLL1', 'stage')].values(): row['phase4_quality_excluded'] = True
        self.assertEqual(evidence.assess(index, T)['flags']['lake'], 'unknown')

    def test_opposing_wind_is_conflicting_evidence(self):
        result = evidence.assess(observations(False, True, False), T)
        self.assertEqual(result['flags']['wind'], 'absent')
        self.assertEqual(result['category'], 'Indeterminate')
        self.assertTrue(result['contradictory'])

    def test_completed_hour_cutoff_and_future_mutation(self):
        index = observations()
        expected = evidence.assess(index, T)
        index[('DENL1','discharge')][T]['value'] = 10000000
        for rows in index.values():
            rows[T + dt.timedelta(hours=1)] = dict(next(iter(rows.values())), value=1e9)
        self.assertEqual(evidence.assess(index, T), expected)
        self.assertEqual(expected['latest_completed_bin_end_utc'], evidence.iso(T))
        self.assertLess(expected['max_observation_bin_start_utc'], evidence.iso(T))

    def test_native_datum_transition_is_not_a_lake_rise(self):
        index = observations(False)
        for stamp, row in index[('MDLL1','stage')].items():
            if stamp < T-dt.timedelta(hours=18): row['datum'] = 'other native datum'
        self.assertEqual(evidence.assess(index, T)['flags']['lake'], 'unknown')

    def test_non_ft_lake_observations_are_rejected(self):
        index = observations(False)
        for row in index[('MDLL1','stage')].values(): row['unit'] = 'm'
        self.assertEqual(evidence.assess(index, T)['category'], 'Indeterminate')

    def test_no_DENL1_change_does_not_exclude_local_runoff(self):
        result = evidence.assess(observations(False,False,False), T)
        self.assertEqual(result['flags']['river'], 'absent')
        self.assertIn('tributary', ' '.join(result['uncertainty']))

    def test_forcing_without_target_response_is_retained(self):
        index = observations()
        for row in index[('MAUL1','stage')].values(): row['value'] = 0
        result = evidence.assess(index, T)
        self.assertEqual(result['category'], 'Compound-supported')
        self.assertEqual(result['flags']['response'], 'not_detected')

    def test_unknown_other_path_is_explicit_not_exclusive_attribution(self):
        index = observations()
        del index[('MDLL1','stage')]
        result = evidence.assess(index, T)
        self.assertEqual(result['category'], 'River-supported')
        self.assertEqual(result['flags']['coastal'], 'unknown')
        self.assertFalse(result['coverage_sufficient'])

    def test_nan_and_partial_current_coverage_are_unknown(self):
        index = observations(False)
        row = index[('MDLL1','stage')][T-dt.timedelta(hours=1)]
        row['value'] = float('nan')
        self.assertEqual(evidence.assess(index, T)['flags']['lake'], 'unknown')

    def test_wind_metrics_preserve_vector_direction_and_persistence(self):
        result = evidence.assess(observations(), T)
        wind = result['metrics']['wind']
        self.assertAlmostEqual(wind['speed_of_mean_vector_knots'],10)
        self.assertAlmostEqual(wind['direction_from_degrees'],90)
        self.assertAlmostEqual(wind['directional_persistence'],1)

    def test_positive_residual_must_increase_and_persist(self):
        index = observations(False)
        for row in index[('NWCL1','residual')].values(): row['value']=1
        self.assertEqual(evidence.assess(index,T)['category'], 'Indeterminate')


if __name__ == '__main__': unittest.main()
