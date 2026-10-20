import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, 'scripts')
import validate_phase3b as phase3b


def episode(identifier, station, variable, role, onset, duration=1, status='detected'):
    return {'episode_id': identifier, 'station': station, 'variable': variable,
            'role': role, 'status': status, 'onset_utc': onset,
            'onset_known': bool(onset), '_cluster_start': onset,
            'duration_hours': duration, 'qualifying_signal': status == 'detected'}


class TestPhase3BValidation(unittest.TestCase):
    def test_new_canal_residual_is_derived_only_from_same_datum_hourly_pairs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            import gzip
            (root/'hourly').mkdir()
            rows = [
                {'time':'2020-09-01T00:00:00Z','station':'NWCL1','variable':'water','value':1.5,'coverage':4,'datum':'MLLW'},
                {'time':'2020-09-01T00:00:00Z','station':'NWCL1','variable':'prediction','value':0.5,'coverage':4,'datum':'MLLW'},
                {'time':'2020-09-01T01:00:00Z','station':'NWCL1','variable':'water','value':1.7,'coverage':4,'datum':'MLLW'},
                {'time':'2020-09-01T01:00:00Z','station':'NWCL1','variable':'prediction','value':0.6,'coverage':4,'datum':'NAVD88'},
            ]
            with gzip.open(root/'hourly'/'2020-09.json.gz','wt',encoding='utf-8') as stream:
                json.dump({'records':rows},stream)
            residuals = [r for r in phase3b.load_hourly(root) if r['variable']=='residual']
            self.assertEqual(residuals[0]['value'],1.0)
            self.assertEqual(residuals[0]['datum'],'MLLW')
            self.assertIsNone(residuals[1]['value'])
            self.assertTrue(residuals[1]['missing'])

    def test_overlapping_cross_station_episodes_share_one_independence_group(self):
        events = [episode('target-1','MAUL1','stage','target','2020-09-20T12:00:00Z',4),
                  episode('target-2','MAUL1','stage','target','2020-09-22T00:00:00Z',3),
                  episode('river-1','DENL1','discharge','river_timing','2020-09-20T06:00:00Z',2)]
        groups = phase3b.cluster_episodes(events,72)
        self.assertEqual(len(groups),1)
        self.assertEqual(groups[0]['detected_target_episode_count'],2)
        self.assertEqual(groups[0]['timing_match_count'],1)
        self.assertEqual(groups[0]['matches'][0]['lead_hours'],6)

    def test_coincident_signal_is_not_reported_as_advance_notice(self):
        events = [episode('target','MAUL1','stage','target','2020-09-20T12:00:00Z'),
                  episode('lake','MDLL1','stage','independent_lake_timing','2020-09-20T12:00:00Z')]
        group = phase3b.cluster_episodes(events,72)[0]
        self.assertEqual(group['status'],'coincident_signals_without_advance')
        self.assertEqual(group['timing_match_count'],0)
        self.assertEqual(group['coincident_predictor_episode_ids'],['lake'])

    def test_mchl1_support_is_retained_without_automatic_lead_match(self):
        target = episode('target','MAUL1','stage','target','2020-09-20T12:00:00Z')
        support = episode('pass','MCHL1','stage','support','2020-09-20T08:00:00Z')
        group = phase3b.cluster_episodes([target,support],72)[0]
        self.assertEqual(group['detected_support_episode_count'],1)
        self.assertEqual(group['timing_match_count'],0)
        self.assertEqual(group['support_episode_ids'],['pass'])

    def test_unknown_target_onset_remains_uncertain_not_matched(self):
        target = episode('target','MAUL1','stage','target',None,status='already_underway')
        target['_cluster_start'] = '2020-09-20T00:00:00Z'
        predictor = episode('river','DENL1','discharge','river_timing','2020-09-20T01:00:00Z')
        group = phase3b.cluster_episodes([target,predictor],72)[0]
        self.assertEqual(group['status'],'target_onset_uncertain')
        self.assertEqual(group['timing_match_count'],0)
        self.assertIn('onset_uncertain',group['uncertainty_flags'])

    def test_event_separation_sensitivity_and_fixed_temporal_split_keep_groups_whole(self):
        events = [episode('target-1','MAUL1','stage','target','2022-12-27T00:00:00Z',3),
                  episode('river-1','DENL1','discharge','river_timing','2022-12-27T01:00:00Z',2),
                  episode('target-2','MAUL1','stage','target','2023-01-04T00:00:00Z',3)]
        groups_48 = phase3b.cluster_episodes(events,48)
        groups_72 = phase3b.cluster_episodes(events,72)
        self.assertEqual(len(groups_48),2)
        self.assertEqual(len(groups_72),2)
        split = phase3b.temporal_split(groups_72)
        self.assertEqual({item['subset'] for item in split},{'calibration_2016_2022','holdout_2023_2026'})
        seam = [{'event_group_id':'seam','start_utc':'2022-12-31T00:00:00Z','end_utc':'2023-01-02T00:00:00Z'}]
        self.assertEqual(phase3b.temporal_split(seam)[0]['subset'],'excluded_split_seam')

    def test_navd88_threshold_never_counts_native_gage_height(self):
        stamp = dt.datetime(2020,9,22,tzinfo=dt.timezone.utc)
        index = {('MAUL1','stage'):{stamp:{'value':5.1,'datum':'gage height','coverage':1}},
                 ('MAUL1','elevation'):{stamp:{'value':4.04,'datum':'NAVD88','coverage':1}}}
        audit = phase3b.navd88_threshold_audit(index)
        self.assertEqual(audit['eligible_observations_at_or_above_threshold'],1)
        self.assertEqual(audit['native_00065_values_at_or_above_4ft_excluded_from_threshold_test'],1)

    def test_detector_series_are_split_at_datum_transitions(self):
        rows = [{'time':'2020-01-01T00:00:00Z','datum':'MLLW','value':1.0,'coverage':1},
                {'time':'2020-01-01T01:00:00Z','datum':'MLLW','value':1.1,'coverage':1},
                {'time':'2020-01-01T02:00:00Z','datum':'NAVD88','value':2.2,'coverage':1},
                {'time':'2020-01-01T03:00:00Z','datum':'NAVD88','value':2.3,'coverage':1}]
        segments = phase3b.split_datum_segments(rows)
        self.assertEqual([len(segment) for segment in segments],[2,2])
        self.assertEqual(segments[0][-1]['datum'],'MLLW')
        self.assertEqual(segments[1][0]['datum'],'NAVD88')

    def test_observation_gaps_are_counted_and_missing_hours_not_filled(self):
        start = dt.datetime(2024,1,1,tzinfo=dt.timezone.utc)
        index = {('MAUL1','stage'):{start:{'value':1.0,'coverage':1},
                                    start+dt.timedelta(hours=2):{'value':1.2,'coverage':1}}}
        coverage = phase3b.window_coverage(index,('MAUL1','stage'),start,start+dt.timedelta(hours=3))
        self.assertEqual(coverage['valid_hours'],2)
        self.assertEqual(coverage['missing_hours'],1)
        self.assertIsNone(index[('MAUL1','stage')].get(start+dt.timedelta(hours=1)))

    def test_retrieval_failure_is_reported_separately_from_hourly_absence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root/'coverage.json').write_text(json.dumps({'months':[]}))
            manifest = {'months': {'2016-01': {'MCHL1': {'status':'retrieval_error','row_count':0}}}}
            coverage = {'MCHL1:stage': {'valid_hours':0,'missing_hours':0,
                                        'not_yet_observed_hours':0,'expected_hours':0}}
            audit = phase3b.coverage_audit(root,coverage,manifest,{})
            self.assertEqual(audit['monthly_source_status_counts']['MCHL1']['retrieval_error'],1)
            self.assertEqual(audit['missing_intervals']['MCHL1:stage'],[])
            self.assertEqual(audit['hourly_variables']['MCHL1:stage']['monthly_source_states'],
                             {'retrieval_error':1})

    def test_derived_residual_coverage_keeps_partial_month_expected_hours(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root/'coverage.json').write_text(json.dumps({'months':[{
                'month':'2026-10','hourly_coverage':{'NWCL1':{
                    'water':{'expected_hours':3,'reporting_hours':2},
                    'prediction':{'expected_hours':3,'reporting_hours':2}}}}]}))
            index = {('NWCL1','residual'):{
                dt.datetime(2026,10,1,tzinfo=dt.timezone.utc):{'value':0.1,'coverage':1,'datum':'MLLW'},
                dt.datetime(2026,10,1,1,tzinfo=dt.timezone.utc):{'value':None,'coverage':0,'datum':'MLLW'}}}
            audit = phase3b.coverage_audit(root,{}, {'months':{}}, index)
            residual = audit['hourly_variables']['NWCL1:residual']
            self.assertEqual(residual['expected_hours'],3)
            self.assertEqual(residual['reported_hours'],2)
            self.assertEqual(residual['valid_hours'],1)
            self.assertEqual(residual['missing_hours'],1)
            self.assertEqual(residual['not_yet_observed_hours'],1)

    def test_match_lead_distribution_is_event_level_and_explicit(self):
        report = phase3b.lead_summaries([{'predictor_station':'DENL1','lead_hours':6},
                                        {'predictor_station':'DENL1','lead_hours':12}])
        self.assertEqual(report['DENL1']['n_event_group_matches'],2)
        self.assertEqual(report['DENL1']['median_hours'],9)
        self.assertEqual(report['DENL1']['strictly_positive_advance_matches'],2)

    def test_external_event_context_does_not_change_archive_threshold_eligibility(self):
        beta = phase3b.NCEI_CONTEXT['case_records']['beta-2020']
        self.assertIn('4.04 ft NAVD88',beta[0]['reported_context'])
        self.assertEqual(phase3b.NCEI_CONTEXT['source'],
                         'NOAA NCEI Storm Events Database detail CSV, independent documentary context only')

    def test_quiet_control_needs_full_core_series_coverage_and_no_candidate_signal(self):
        coverage = {'month':'2024-01','hourly_coverage':{}}
        for station,variable in [('MAUL1','stage'),('DENL1','discharge'),('NWCL1','residual'),('MDLL1','stage')]:
            coverage['hourly_coverage'].setdefault(station,{})[variable] = {
                'expected_hours':744,'reporting_hours':744,'valid_hours':744}
        manifest = {'2024-01': {'MCHL1':{'status':'retrieval_error','row_count':0}}}
        quiet = phase3b.negative_control_months([coverage],manifest,[])
        self.assertEqual(quiet['quiet_control_count'],1)
        self.assertEqual(quiet['excluded_month_count'],0)
        signal = episode('candidate','DENL1','discharge','river_timing','2024-01-15T12:00:00Z')
        excluded = phase3b.negative_control_months([coverage],manifest,[signal])
        self.assertEqual(excluded['quiet_control_count'],0)
        self.assertIn('candidate',excluded['excluded_months'][0]['candidate_episode_ids'])

    def test_quiet_control_coverage_uses_derived_new_canal_residual(self):
        coverage = {'month':'2024-01','hourly_coverage':{'NWCL1':{
            'water':{'expected_hours':2,'reporting_hours':2,'valid_hours':2},
            'prediction':{'expected_hours':2,'reporting_hours':2,'valid_hours':2}}}}
        for station,variable in [('MAUL1','stage'),('DENL1','discharge'),('MDLL1','stage')]:
            coverage['hourly_coverage'].setdefault(station,{})[variable] = {
                'expected_hours':2,'reporting_hours':2,'valid_hours':2}
        index = {('NWCL1','residual'):{
            dt.datetime(2024,1,1,tzinfo=dt.timezone.utc):{'value':0.1,'coverage':1,'datum':'MLLW'},
            dt.datetime(2024,1,1,1,tzinfo=dt.timezone.utc):{'value':0.2,'coverage':1,'datum':'MLLW'}}}
        quiet = phase3b.negative_control_months([coverage],{'2024-01':{}},[],index=index)
        self.assertEqual(quiet['quiet_control_count'],1)
        self.assertEqual(quiet['quiet_control_months'][0]['coverage']['NWCL1:residual']['valid_hours'],2)


if __name__ == '__main__':
    unittest.main()
