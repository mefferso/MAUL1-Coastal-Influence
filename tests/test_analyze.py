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
