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

 def test_onset_uses_trailing_baseline_and_no_future_rows(self):
  rows=[{'time':f'2020-01-01T{h:02d}:00:00Z','value':(0 if h<6 else 10),'coverage':1} for h in range(8)]
  onset=analyze.detect_onset(rows,threshold=2.0,baseline_points=3,persistence=2)
  self.assertEqual(onset['onset_time'],'2020-01-01T07:00:00Z')
  self.assertEqual(analyze.detect_onset(rows[:7],threshold=2.0,baseline_points=3,persistence=2)['onset_time'],None)

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
  self.assertEqual(derived[-1]['vector_u_change'],3)
  self.assertEqual({r['window_hours'] for r in result if 'window_hours' in r},{3,6,12,24})
