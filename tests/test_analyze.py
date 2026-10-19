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

class TestAnalysisPipeline(unittest.TestCase):
 def test_only_canonical_event_archives_are_inputs(self):
  paths=analyze.canonical_event_paths()
  self.assertTrue(paths)
  self.assertTrue(all('-hourly' not in path.name for path in paths))
  self.assertTrue(all(path.name.endswith('.json.gz') for path in paths))

 def test_repeated_analysis_with_hourly_outputs_is_idempotent(self):
  output=pathlib.Path('site/data/analysis.json')
  with contextlib.redirect_stdout(io.StringIO()): analyze.main()
  first=hashlib.sha256(output.read_bytes()).hexdigest()
  with contextlib.redirect_stdout(io.StringIO()): analyze.main()
  second=hashlib.sha256(output.read_bytes()).hexdigest()
  self.assertEqual(first,second)
  payload=json.loads(output.read_text())
  self.assertTrue(all('hourly_file' in item for item in payload))
