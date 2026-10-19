import sys, unittest
sys.path.insert(0,'scripts')
import build

class TestArchive(unittest.TestCase):
 def test_utc_and_offset(self): self.assertEqual(build.iso('2020-01-01T00:00:00-06:00'),'2020-01-01T06:00:00Z')
 def test_reject_wrong_station(self):
  data={'value':{'timeSeries':[{'sourceInfo':{'siteCode':[{'value':'bad'}]},'variable':{'variableCode':[{'value':'00065'}]},'values':[]}]}}
  with self.assertRaises(ValueError): build.parse_usgs(data,'MAUL1')
 def test_no_implicit_datum_conversion(self):
  data={'value':{'timeSeries':[{'sourceInfo':{'siteCode':[{'value':'07380215'}]},'variable':{'variableCode':[{'value':'00065'}]},'values':[{'value':[{'value':'5.38','dateTime':'2020-01-01T00:00:00-06:00','qualifiers':['P']}]}]}]}}
  result=build.parse_usgs(data,'MAUL1')
  self.assertEqual(result[0]['datum'],'gage height');self.assertEqual(result[0]['value'],5.38)
 def test_dedupe(self):
  row=dict(station='MAUL1',variable='stage',time='2020-01-01T00:00:00Z')
  self.assertEqual(len(build.dedupe([row,row])),1)
 def test_coops_error(self):
  with self.assertRaises(ValueError): build.parse_coops({'error':{'message':'no data'}},'water','NAVD88')
 def test_event_windows(self):
  self.assertGreaterEqual(len(build.EVENTS),7)
  for _,start,end in build.EVENTS.values(): self.assertGreaterEqual((build.dt.date.fromisoformat(end)-build.dt.date.fromisoformat(start)).days,8)
if __name__=='__main__': unittest.main()

class TestScientificCalculations(unittest.TestCase):
 def test_wind_wraparound_components(self):
  rows=build.parse_wind({'data':[{'t':'2020-01-01 00:00','s':'10','d':'350','g':'12'},{'t':'2020-01-01 00:06','s':'10','d':'10','g':'12'}]})
  v=[r['value'] for r in rows if r['variable']=='wind_v']
  self.assertTrue(all(x<-9 for x in v))
 def test_residual_only_same_timestamp_and_datum(self):
  base=dict(station='NWCL1',time='2020-01-01T00:00:00Z',datum='MLLW',value=3)
  result=build.residuals([dict(base,variable='water'),dict(base,variable='prediction',value=1)])
  self.assertEqual(result[0]['value'],2)
  self.assertEqual(build.residuals([dict(base,variable='water'),dict(base,variable='prediction',datum='NAVD88')]),[])

class TestHads(unittest.TestCase):
 def test_stage_and_station_validation(self):
  rows=build.parse_hads('station,utc_valid,HGIRGZZ\nMCHL1,2025-04-01 00:00:00,1.25\n')
  self.assertEqual(rows[0]['datum'],'HADS native gage height (unverified)')
  self.assertEqual(rows[0]['value'],1.25)
  with self.assertRaises(ValueError):build.parse_hads('station,utc_valid,HGIRGZZ\nOTHER,2025-04-01 00:00:00,1.25\n')

class TestTrends(unittest.TestCase):
 def test_exact_delta_without_gap_interpolation(self):
  base=dict(station='MAUL1',variable='stage',datum='gage height',unit='ft',source='USGS')
  rows=[dict(base,time='2020-01-01T00:00:00Z',value=1),dict(base,time='2020-01-01T01:00:00Z',value=1.5),dict(base,time='2020-01-01T03:00:00Z',value=2)]
  result=build.changes(rows)
  self.assertEqual([r['value'] for r in result if r['variable']=='stage_change_1h'],[.5])
  self.assertEqual([r['value'] for r in result if r['variable']=='stage_change_3h'],[1])
