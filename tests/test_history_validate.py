import unittest
import sys
sys.path.insert(0,'scripts')
import history
import history_validate
import pathlib
import tempfile


class TestHourlyDerivation(unittest.TestCase):
 def test_hourly_bucket_index_groups_observations_once_for_month_derivation(self):
  rows=[{'time':'2024-02-01T00:15:00Z','station':'MAUL1','variable':'stage','value':1,'unit':'ft','datum':'gage height'},
   {'time':'2024-02-01T00:45:00Z','station':'MAUL1','variable':'stage','value':2,'unit':'ft','datum':'gage height'}]
  buckets=history.hourly_buckets(rows)
  self.assertEqual(len(buckets),1)
  self.assertEqual(len(buckets[('MAUL1','stage','2024-02-01T00:00:00Z')]),2)

 def test_hourly_wind_direction_is_derived_from_components_not_angle_average(self):
  raw=[{'schema_version':'3A.1','station':'NWCL1','month_start':'2024-02-01T00:00:00Z','month_end_exclusive':'2024-03-01T00:00:00Z','rows':[
   {'time':'2024-02-01T00:00:00Z','station':'NWCL1','variable':'wind_u','value':1.736,'unit':'knots','datum':'none'},
   {'time':'2024-02-01T00:00:00Z','station':'NWCL1','variable':'wind_v','value':-9.848,'unit':'knots','datum':'none'},
   {'time':'2024-02-01T00:30:00Z','station':'NWCL1','variable':'wind_u','value':-1.736,'unit':'knots','datum':'none'},
   {'time':'2024-02-01T00:30:00Z','station':'NWCL1','variable':'wind_v','value':-9.848,'unit':'knots','datum':'none'}]}]
  result=history.hourly_month(raw,'2024-02')
  direction=next(row for row in result['records'] if row['station']=='NWCL1' and row['variable']=='wind_direction' and row['time']=='2024-02-01T00:00:00Z')
  self.assertAlmostEqual(direction['value'],0.0,places=1)

 def test_hourly_month_keeps_empty_hours_missing(self):
  raw=[{'schema_version':'3A.1','station':'MAUL1','month_start':'2024-01-01T00:00:00Z','month_end_exclusive':'2024-03-01T00:00:00Z','rows':[
   {'time':'2024-01-31T23:00:00Z','station':'MAUL1','variable':'stage','value':1.0,'unit':'ft','datum':'gage height'},
   {'time':'2024-02-01T00:15:00Z','station':'MAUL1','variable':'stage','value':2.0,'unit':'ft','datum':'gage height'},
   {'time':'2024-02-01T02:15:00Z','station':'MAUL1','variable':'stage','value':4.0,'unit':'ft','datum':'gage height'}]}]
  result=history.hourly_month(raw,'2024-02')
  levels=[row for row in result['records'] if row['station']=='MAUL1' and row['variable']=='stage']
  self.assertEqual([row['time'] for row in levels[:3]],['2024-02-01T00:00:00Z','2024-02-01T01:00:00Z','2024-02-01T02:00:00Z'])
  self.assertEqual([row['value'] for row in levels[:3]],[2.0,None,4.0])
  self.assertEqual(levels[1]['coverage'],0)

 def test_hourly_change_does_not_cross_a_missing_hour(self):
  raw=[{'schema_version':'3A.1','station':'MAUL1','month_start':'2024-02-01T00:00:00Z','month_end_exclusive':'2024-03-01T00:00:00Z','rows':[
   {'time':'2024-02-01T00:00:00Z','station':'MAUL1','variable':'stage','value':1.0,'unit':'ft','datum':'gage height'},
   {'time':'2024-02-01T02:00:00Z','station':'MAUL1','variable':'stage','value':4.0,'unit':'ft','datum':'gage height'}]}]
  result=history.hourly_month(raw,'2024-02')
  self.assertFalse(any(row['variable']=='stage_change_1h' for row in result['records']))

class TestHistoryValidation(unittest.TestCase):
 def test_rebuild_writes_hourly_and_reports_without_altering_raw_partition(self):
  payload={'schema_version':'3A.1','station':'MAUL1','month_start':'2024-02-01T00:00:00Z','month_end_exclusive':'2024-03-01T00:00:00Z','rows':[{'time':'2024-02-01T00:00:00Z','station':'MAUL1','variable':'stage','value':1.0,'unit':'ft','datum':'gage height'}]}
  with tempfile.TemporaryDirectory() as temporary:
   root=pathlib.Path(temporary)
   path=history.partition_path(root,'MAUL1','2024-02')
   history.write_partition(path,payload)
   history._write_manifest(root,{'schema_version':'3A.1','months':{'2024-02':{'MAUL1':{'status':'retrieved','row_count':1,'path':str(path.relative_to(root))}}}})
   history.rebuild_hourly_reports(root)
   self.assertTrue((root/'hourly'/'2024-02.json.gz').exists())
   self.assertTrue((root/'coverage.json').exists())
   self.assertTrue((root/'wind-comparison.json').exists())
   self.assertTrue((root/'quality.json').exists())
   self.assertEqual(history.load_partition(path)['rows'],payload['rows'])

 def test_quality_validation_reports_duplicates_units_datums_and_jumps(self):
  rows=[
   {'time':'2024-02-01T00:00:00Z','station':'MAUL1','variable':'stage','value':1,'unit':'ft','datum':'gage height'},
   {'time':'2024-02-01T00:00:00Z','station':'MAUL1','variable':'stage','value':2,'unit':'ft','datum':'gage height'},
   {'time':'2024-02-01T01:00:00Z','station':'MAUL1','variable':'stage','value':20,'unit':'m','datum':'NAVD88'},
  ]
  findings=history_validate.validate_rows(rows)
  kinds={item['kind'] for item in findings}
  self.assertTrue({'duplicate_timestamp','unit_change','datum_change','suspicious_jump'} <= kinds)

 def test_wind_comparison_handles_direction_wraparound_without_averaging_sources(self):
  primary=[{'time':'2024-02-01T00:00:00Z','variable':'wind','value':10,'unit':'knots','source':'CO-OPS'}, {'time':'2024-02-01T00:00:00Z','variable':'wind_direction','value':359,'unit':'degrees from','source':'CO-OPS'}]
  independent=[{'time':'2024-02-01T00:00:00Z','variable':'wind','value':10,'unit':'knots','source':'NDBC'}, {'time':'2024-02-01T00:00:00Z','variable':'wind_direction','value':1,'unit':'degrees from','source':'NDBC'}]
  report=history_validate.compare_wind(primary,independent)
  self.assertEqual(report['overlap_records'],1)
  self.assertEqual(report['direction_error_degrees'][0],2.0)
  self.assertFalse(report['averaged_sources'])

 def test_coverage_report_exposes_year_month_and_retrieval_state(self):
  manifest={'months':{'2024-02':{'MAUL1':{'status':'retrieved','row_count':2},'NWCL1-NDBC':{'status':'retrieval_error','row_count':0}}}}
  hourly={'records':[{'time':'2024-02-01T00:00:00Z','station':'MAUL1','variable':'stage','value':1,'coverage':1,'missing':False}]}
  report=history.coverage_report(manifest,hourly)
  self.assertEqual(report['months'][0]['month'],'2024-02')
  self.assertEqual(report['stations']['MAUL1']['valid_months'],1)
  self.assertEqual(report['stations']['NWCL1-NDBC']['retrieval_errors'],1)

if __name__=='__main__': unittest.main()
