import datetime as dt
import gzip
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, 'scripts')
import discover


class TestContinuousDiscovery(unittest.TestCase):
 def test_load_hourly_keeps_only_discovery_series(self):
  records=[
   {'time':'2024-01-01T00:00:00Z','station':'MAUL1','variable':'stage','value':1.0},
   {'time':'2024-01-01T00:00:00Z','station':'DENL1','variable':'discharge','value':100.0},
   {'time':'2024-01-01T00:00:00Z','station':'NWCL1','variable':'residual','value':0.1},
   {'time':'2024-01-01T00:00:00Z','station':'MDLL1','variable':'stage','value':2.0},
   {'time':'2024-01-01T00:00:00Z','station':'MAUL1','variable':'elevation','value':3.0},
  ]
  with tempfile.TemporaryDirectory() as temporary:
   root=pathlib.Path(temporary); hourly=root/'hourly'; hourly.mkdir()
   with gzip.open(hourly/'2024-01.json.gz','wt',encoding='utf-8') as stream:
    json.dump({'records':records},stream)
   loaded=discover._load_hourly(root)
  self.assertEqual({(row['station'],row['variable']) for row in loaded},{
   ('MAUL1','stage'),('DENL1','discharge'),('NWCL1','residual'),('MDLL1','stage')})
  self.assertEqual(len(loaded),4)
 def test_merge_dependent_groups_overlapping_pathway_episodes(self):
  episodes=[
   {'episode_id':'river-1','pathway':'river','onset_utc':'2020-09-20T00:00:00Z','end_utc':'2020-09-20T12:00:00Z'},
   {'episode_id':'river-2','pathway':'river','onset_utc':'2020-09-20T16:00:00Z','end_utc':'2020-09-21T00:00:00Z'},
   {'episode_id':'coastal-1','pathway':'coastal','onset_utc':'2020-09-20T04:00:00Z','end_utc':'2020-09-20T08:00:00Z'},
  ]
  groups=discover.merge_dependent(episodes,gap_hours=6)
  self.assertEqual(len(groups),2)
  self.assertEqual(groups[0]['episode_ids'],['river-1','river-2'])
  self.assertEqual(groups[0]['pathway'],'river')
  self.assertEqual(groups[1]['episode_ids'],['coastal-1'])

 def test_classification_keeps_compound_and_nonresponse_descriptive(self):
  targets=[{'episode_id':'target-1','onset_utc':'2024-02-03T12:00:00Z','status':'detected'}]
  predictors=[
   {'episode_id':'river-1','station':'DENL1','pathway':'river','onset_utc':'2024-02-03T08:00:00Z','status':'detected'},
   {'episode_id':'coast-1','station':'NWCL1','pathway':'coastal','onset_utc':'2024-02-03T10:00:00Z','status':'detected'},
   {'episode_id':'river-2','station':'DENL1','pathway':'river','onset_utc':'2024-02-10T08:00:00Z','status':'detected'},
  ]
  result=discover.classify_matches(targets,predictors)
  self.assertEqual(result['target_categories'][0]['category'],'compound_candidate')
  self.assertEqual(result['unmatched_predictors'][0]['category'],'river_nonresponse')
  self.assertNotIn('cause',result['target_categories'][0])
  self.assertIn('not verified',result['target_categories'][0]['note'].lower())

 def test_quiet_controls_require_available_hours_and_no_detected_signals(self):
  rows=[]
  start=dt.datetime(2024,1,1,tzinfo=dt.timezone.utc)
  for offset in range(48):
   stamp=(start+dt.timedelta(hours=offset)).strftime('%Y-%m-%dT%H:%M:%SZ')
   rows.append({'time':stamp,'station':'MAUL1','variable':'stage','value':1.0,'coverage':1,'missing':False})
  controls=discover.build_controls(rows,[])
  self.assertEqual(controls[0]['category'],'quiet_control')
  self.assertEqual(controls[0]['valid_hours'],48)

 def test_context_references_are_explicitly_not_queried(self):
  context=discover.context_for_interval('2024-02-01T00:00:00Z','2024-02-03T00:00:00Z')
  self.assertEqual(context['status'],'not_queried')
  self.assertTrue(context['references'])
  self.assertNotIn('classification',context)


if __name__=='__main__': unittest.main()
