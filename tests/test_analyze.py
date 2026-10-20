import contextlib
import hashlib
import io
import json
import pathlib
import sys,unittest
sys.path.insert(0,'scripts')
import analyze
class TestLag(unittest.TestCase):
 def test_positive_lag_source_leads_target(self):
  from datetime import datetime,timedelta,timezone
  start=datetime(2020,1,1,tzinfo=timezone.utc)
  times=[(start+timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M:%SZ') for i in range(60)]
  source={t:(i*i%31) for i,t in enumerate(times[:55])}
  target={t:source[times[i-5]] for i,t in enumerate(times[5:],5)}
  self.assertEqual(analyze.lag_correlation(source,target,range(-8,9))['lag_hours'],5)
 def test_sparse_returns_none(self):
  self.assertIsNone(analyze.lag_correlation({'2020-01-01T00:00:00Z':1},{},range(5)))

class TestHourlyAndOnset(unittest.TestCase):
 def test_hourly_aggregation_uses_actual_observations_without_interpolation(self):
  rows=[
   {'time':'2020-01-01T00:10:00Z','value':1,'station':'MAUL1','variable':'stage','unit':'ft','datum':'gage height'},
   {'time':'2020-01-01T00:40:00Z','value':3,'station':'MAUL1','variable':'stage','unit':'ft','datum':'gage height'},
   {'time':'2020-01-01T02:10:00Z','value':5,'station':'MAUL1','variable':'stage','unit':'ft','datum':'gage height'},
  ]
  result=analyze.aggregate_hourly(rows,'MAUL1','stage','2020-01-01T00:00:00Z','2020-01-01T03:00:00Z')
  self.assertEqual([r['value'] for r in result],[2,None,5])
  self.assertEqual([r['coverage'] for r in result],[2,0,1])

 def test_onset_requires_long_positive_baseline_and_no_future_rows(self):
  from datetime import datetime,timedelta,timezone
  rows=[]; start=datetime(2020,1,1,tzinfo=timezone.utc)
  value=0.0
  for h in range(80):
   if h < 72: value=0.1*(h%2)
   else: value += 1.0
   rows.append({'time':(start+timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ'),'value':value,'coverage':1})
  onset=analyze.detect_onset(rows,threshold=2.0,baseline_hours=72,min_baseline_points=48,persistence=3)
  self.assertEqual(onset['onset_time'],'2020-01-04T02:00:00Z')
  self.assertEqual(onset['status'],'detected')
  self.assertIsNone(analyze.detect_onset(rows[:74],threshold=2.0,baseline_hours=72,min_baseline_points=48,persistence=3)['onset_time'])

 def test_falling_series_is_not_a_rising_onset(self):
  from datetime import datetime,timedelta,timezone
  start=datetime(2020,1,1,tzinfo=timezone.utc)
  rows=[{'time':(start+timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ'),'value':100-h*0.5,'coverage':1} for h in range(80)]
  result=analyze.detect_onset(rows,baseline_hours=72,min_baseline_points=48,persistence=3)
  self.assertIsNone(result['onset_time'])

 def test_missing_hour_breaks_persistence_and_is_reported(self):
  from datetime import datetime,timedelta,timezone
  start=datetime(2020,1,1,tzinfo=timezone.utc); rows=[]
  for h in range(77):
   rows.append({'time':(start+timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ'),'value':0.1*(h%2) if h<72 else h-71,'coverage':0 if h==74 else 1})
  result=analyze.detect_onset(rows,threshold=1.5,baseline_hours=72,min_baseline_points=48,persistence=3)
  self.assertIsNone(result['onset_time']); self.assertEqual(result['status'],'gap')

 def test_near_zero_mad_is_uncertain_not_a_detection(self):
  from datetime import datetime,timedelta,timezone
  start=datetime(2020,1,1,tzinfo=timezone.utc)
  rows=[{'time':(start+timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ'),'value':(0 if h<72 else h),'coverage':1} for h in range(80)]
  result=analyze.detect_onset(rows,threshold=2.0,baseline_hours=72,min_baseline_points=48,persistence=3)
  self.assertIsNone(result['onset_time']); self.assertEqual(result['status'],'uncertain')

 def test_short_archive_with_rise_is_marked_already_underway(self):
  from datetime import datetime,timedelta,timezone
  start=datetime(2020,1,1,tzinfo=timezone.utc)
  rows=[{'time':(start+timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ'),'value':h,'coverage':1} for h in range(8)]
  result=analyze.detect_onset(rows,baseline_hours=72,min_baseline_points=48,persistence=3)
  self.assertEqual(result['status'],'already_underway')
  self.assertIsNone(result['onset_time'])

 def test_lead_is_detected_timing_not_reliable_prediction(self):
  from datetime import datetime,timedelta,timezone
  start=datetime(2020,1,1,tzinfo=timezone.utc)
  series=[{'time':(start+timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ'),'value':0.1*(h%2) if h<72 else h-71,'coverage':1} for h in range(80)]
  result=analyze.compare_onsets(series,series,threshold=2.0,baseline_hours=72,min_baseline_points=48,persistence=3)
  self.assertEqual(result['threshold_sigma'],2.0)
  self.assertEqual(result['status'],'detected_not_validated')
  self.assertNotEqual(result['status'],'reliable')

 def test_datum_change_blocks_trailing_signal(self):
  rows=[
   {'time':'2020-01-01T00:00:00Z','value':1,'datum':'gage height','coverage':1},
   {'time':'2020-01-01T01:00:00Z','value':2,'datum':'NAVD88','coverage':1},
  ]
  self.assertEqual(analyze.trailing_change(rows,1),[])

 def test_wind_vector_has_requested_trailing_windows(self):
  from datetime import datetime,timedelta,timezone
  rows=[]
  for hour in range(30):
   stamp=(datetime(2020,1,1,tzinfo=timezone.utc)+timedelta(hours=hour)).strftime('%Y-%m-%dT%H:%M:%SZ')
   rows.extend([
    {'time':stamp,'station':'NWCL1','variable':'wind_u','value':hour,'unit':'knots','datum':'none'},
    {'time':stamp,'station':'NWCL1','variable':'wind_v','value':0,'unit':'knots','datum':'none'},
   ])
  result=analyze.vector_hourly(rows,'2020-01-01T00:00:00Z','2020-01-02T06:00:00Z')
  derived=[r for r in result if r.get('window_hours')==3]
  self.assertEqual(derived[-1]['vector_u_mean'],28)
  self.assertEqual(derived[-1]['directional_persistence'],1)
  self.assertEqual({r['window_hours'] for r in result if 'window_hours' in r},{3,6,12,24})

class TestIndependentEpisodes(unittest.TestCase):
 def _series(self, values, start='2020-01-01T00:00:00Z', datum='gage height', coverage=1):
  from datetime import datetime,timedelta,timezone
  origin=datetime.fromisoformat(start.replace('Z','+00:00')).astimezone(timezone.utc)
  return [
   {'time':(origin+timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'value':value,'coverage':coverage,'unit':'ft','datum':datum}
   for i,value in enumerate(values)
  ]

 def test_fixed_baseline_finds_two_separated_positive_target_episodes(self):
  values=[]; level=10.0
  for hour in range(96):
   if hour < 72:
    level += (0.01,-0.02,0.03,-0.01,0.0)[hour % 5]
   elif hour in (72,73,74):
    level += 0.30
   elif 75 <= hour <= 80:
    level += 0.0
   elif hour in (81,82,83):
    level += 0.30
   values.append(round(level,3))
  episodes=analyze.detect_episodes(self._series(values),station='MAUL1',variable='stage',min_rise=0.25)
  detected=[episode for episode in episodes if episode['status']=='detected']
  self.assertEqual(len(detected),2)
  self.assertEqual(detected[0]['onset_utc'],'2020-01-04T00:00:00Z')
  self.assertEqual(detected[1]['onset_utc'],'2020-01-04T09:00:00Z')
  self.assertGreaterEqual(detected[0]['duration_hours'],3)
  self.assertGreaterEqual(detected[0]['rise'],0.25)
  self.assertEqual(detected[0]['datum_status'],'native_gage_height')
  self.assertFalse(detected[0]['navd88_threshold_eligible'])

 def test_long_hourly_series_uses_bounded_baseline_windows(self):
  values=[100.0]
  for hour in range(1,10000):
   values.append(values[-1]+(0.001 if hour % 2 else -0.001))
  episodes=analyze.detect_episodes(self._series(values),station='MAUL1',variable='stage',min_rise=0.25)
  self.assertTrue(any(episode['status']=='no_signal' for episode in episodes))
  self.assertFalse(any(episode['status']=='detected' for episode in episodes))

 def test_falling_or_short_changes_do_not_create_response_episode(self):
  values=[10.0]
  for hour in range(1,96): values.append(values[-1]-(0.1 if hour >= 72 else 0.01))
  episodes=analyze.detect_episodes(self._series(values),station='MAUL1',variable='stage',min_rise=0.25)
  self.assertFalse(any(episode['status']=='detected' for episode in episodes))

  values=[10.0]*72+[10.3,10.6]
  episodes=analyze.detect_episodes(self._series(values),station='MAUL1',variable='stage',min_rise=0.25)
  self.assertFalse(any(episode['status']=='detected' for episode in episodes))

 def test_missing_hour_is_explicit_gap_not_nonconsecutive_persistence(self):
  values=[]; level=10.0
  for hour in range(80):
   level += ((0.01,-0.02,0.03,-0.01,0.0)[hour % 5] if hour < 72 else 0.3)
   values.append(round(level,3))
  rows=self._series(values)
  rows[74]['coverage']=0; rows[74]['value']=None
  episodes=analyze.detect_episodes(rows,station='MAUL1',variable='stage',min_rise=0.25)
  self.assertTrue(any(episode['status']=='gap' for episode in episodes))
  self.assertFalse(any(episode['status']=='detected' and episode['onset_utc']=='2020-01-04T00:00:00Z' for episode in episodes))

 def test_archive_start_rise_is_retained_as_already_underway(self):
  rows=self._series([10+i*0.3 for i in range(8)])
  episodes=analyze.detect_episodes(rows,station='MAUL1',variable='stage',min_rise=0.25)
  self.assertTrue(any(episode['status']=='already_underway' for episode in episodes))
  self.assertTrue(all(episode['onset_known'] is False for episode in episodes if episode['status']=='already_underway'))

 def test_predictor_series_cannot_change_target_episode_selection(self):
  target=self._series([10.0]*72+[10.3,10.6,10.9,10.9],datum='gage height')
  first=analyze.detect_episodes(target,station='MAUL1',variable='stage',min_rise=0.25)
  predictor=self._series([100.0]*72+[1000,1,1000,1],datum='none')
  second=analyze.detect_episodes(target,station='MAUL1',variable='stage',min_rise=0.25)
  self.assertEqual(first,second)
  self.assertNotEqual(predictor[73]['value'],target[73]['value'])

class TestEpisodeMatching(unittest.TestCase):
 def test_predictor_before_target_is_a_detected_timing_match(self):
  result=analyze.match_episodes(
   [{'episode_id':'maul-1','onset_utc':'2020-01-05T10:00:00Z','status':'detected'}],
   [{'episode_id':'den-1','onset_utc':'2020-01-05T05:00:00Z','status':'detected','station':'DENL1'}],
   max_lead_hours=72)
  self.assertEqual(len(result['matches']),1)
  self.assertEqual(result['matches'][0]['lead_hours'],5.0)
  self.assertEqual(result['matches'][0]['status'],'detected_not_validated')

 def test_post_onset_predictor_is_unmatched_and_not_a_negative_lead(self):
  result=analyze.match_episodes(
   [{'episode_id':'maul-1','onset_utc':'2020-01-05T10:00:00Z','status':'detected'}],
   [{'episode_id':'den-1','onset_utc':'2020-01-05T12:00:00Z','status':'detected','station':'DENL1'}],
   max_lead_hours=72)
  self.assertFalse(result['matches'])
  self.assertEqual(result['unmatched_predictors'][0]['status'],'post_target')
  self.assertFalse(any('lead_hours' in item for item in result['unmatched_predictors']))

 def test_one_predictor_episode_cannot_be_counted_for_two_targets(self):
  result=analyze.match_episodes(
   [{'episode_id':'maul-1','onset_utc':'2020-01-05T10:00:00Z','status':'detected'},
    {'episode_id':'maul-2','onset_utc':'2020-01-06T10:00:00Z','status':'detected'}],
   [{'episode_id':'den-1','onset_utc':'2020-01-05T05:00:00Z','status':'detected','station':'DENL1'}],
   max_lead_hours=72)
  self.assertEqual(len(result['matches']),1)
  self.assertEqual(len(result['unmatched_targets']),1)

 def test_unknown_target_onset_is_explicitly_unmatched(self):
  result=analyze.match_episodes(
   [{'episode_id':'maul-1','onset_utc':None,'status':'already_underway'}],
   [{'episode_id':'den-1','onset_utc':'2020-01-05T05:00:00Z','status':'detected','station':'DENL1'}],
   max_lead_hours=72)
  self.assertFalse(result['matches'])
  self.assertEqual(result['unmatched_targets'][0]['status'],'target_onset_unknown')

 def test_sally_and_beta_share_a_dependent_window_group(self):
  self.assertEqual(analyze.event_independence_group('sally-2020'), 'sally-beta-2020')
  self.assertEqual(analyze.event_independence_group('beta-2020'), 'sally-beta-2020')
  self.assertIsNone(analyze.event_independence_group('front-2025-04'))

class TestAnalysisPipeline(unittest.TestCase):
 def test_only_canonical_event_archives_are_inputs(self):
  paths=analyze.canonical_event_paths()
  self.assertTrue(paths)
  self.assertTrue(all('-hourly' not in path.name for path in paths))
  self.assertTrue(all(path.name.endswith('.json.gz') for path in paths))

 def test_repeated_analysis_with_hourly_outputs_is_idempotent(self):
  output=pathlib.Path('site/data/analysis.json')
  verification=pathlib.Path('site/data/verification.json')
  with contextlib.redirect_stdout(io.StringIO()): analyze.main()
  first=hashlib.sha256(output.read_bytes()).hexdigest()
  verification_first=hashlib.sha256(verification.read_bytes()).hexdigest()
  with contextlib.redirect_stdout(io.StringIO()): analyze.main()
  second=hashlib.sha256(output.read_bytes()).hexdigest()
  verification_second=hashlib.sha256(verification.read_bytes()).hexdigest()
  self.assertEqual(first,second)
  self.assertEqual(verification_first,verification_second)
  payload=json.loads(output.read_text())
  self.assertTrue(all('hourly_file' in item for item in payload))

 def test_verification_references_are_internal_and_case_studies_are_present(self):
  payload=json.loads(pathlib.Path('site/data/verification.json').read_text())
  self.assertEqual(payload['matching_windows_hours']['DENL1']['lead_max'],72)
  self.assertEqual(payload['matching_windows_hours']['NWCL1']['lead_max'],18)
  self.assertEqual(payload['matching_windows_hours']['MDLL1']['lead_max'],18)
  for event in payload['events']:
   self.assertEqual(set(event['sensitivity_checks']),{'1.5','2.0','2.5'})
  self.assertEqual({item['event_id'] for item in payload['case_studies']},
   {'flood-2016','beta-2020','front-2024-11','front-2025-04','laura-2020','front-2024-10'})
  for event in payload['events']:
   target_ids={item['episode_id'] for item in event['target_episodes']}
   predictor_ids={item['episode_id'] for group in event['predictor_episodes'].values() for item in group}
   for match in event['matches']:
    self.assertIn(match['target_episode_id'],target_ids)
    self.assertIn(match['predictor_episode_id'],predictor_ids)
    self.assertEqual(match['status'],'detected_not_validated')
    self.assertGreaterEqual(match['lead_hours'],0)
   self.assertNotIn('reliable',json.dumps(event).lower())
