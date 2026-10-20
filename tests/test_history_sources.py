import pathlib
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0,'scripts')
import history
import history_sources


class TestSourceAdapters(unittest.TestCase):
 def test_usgs_parser_preserves_native_datum_and_quality(self):
  payload={'value':{'timeSeries':[{'sourceInfo':{'siteCode':[{'value':'07380215'}]},'variable':{'variableCode':[{'value':'00065'}]},'values':[{'value':[{'value':'5.38','dateTime':'2024-02-01T00:00:00-06:00','qualifiers':['P']}]}]}]}}
  result=history_sources.parse_usgs_payload(payload,'MAUL1','2024-02')
  self.assertEqual(result['status'],'retrieved')
  self.assertEqual(result['rows'][0]['datum'],'gage height')
  self.assertEqual(result['rows'][0]['quality'],['P'])
  self.assertEqual(result['rows'][0]['time'],'2024-02-01T06:00:00Z')

 def test_coops_parser_keeps_source_and_native_datum(self):
  result=history_sources.parse_coops_payload({'data':[{'t':'2024-02-01 00:00','v':'1.25','f':'0,0'}]},'water','MLLW','2024-02')
  self.assertEqual(result['rows'][0]['station'],'NWCL1')
  self.assertEqual(result['rows'][0]['datum'],'MLLW')
  self.assertIn('NOAA CO-OPS',result['rows'][0]['source'])

 def test_hads_parser_preserves_unverified_mchl1_provenance(self):
  result=history_sources.parse_hads_payload('station,utc_valid,HGIRGZZ\nMCHL1,2024-02-01 00:00:00,1.25\n','2024-02')
  self.assertEqual(result['rows'][0]['station'],'MCHL1')
  self.assertEqual(result['rows'][0]['datum'],'HADS native gage height (unverified)')

 def test_ndbc_access_failure_is_not_fabricated_data(self):
  result=history_sources.failure_result('NDBC-NWCL1','2024-02','https://example.invalid','HTTP 403')
  self.assertEqual(result['status'],'retrieval_error')
  self.assertEqual(result['rows'],[])
  self.assertEqual(result['error'],'HTTP 403')

 def test_ndbc_archive_download_is_cached_once_per_year(self):
  history_sources._NDBC_RAW_BY_YEAR.clear()
  payload=b'#YY MM DD hh mm WDIR WSPD GST\n2024 02 01 00 00 180 5.0 7.0\n'
  with patch.object(history_sources,'_request',return_value=(payload,'fixture')) as request:
   first=history_sources.fetch_ndbc_month('2024-01')
   second=history_sources.fetch_ndbc_month('2024-02')
  self.assertEqual(request.call_count,1)
  self.assertEqual(first['status'],'retrieved')
  self.assertEqual(second['status'],'retrieved')
  self.assertEqual(second['rows'][0]['time'],'2024-02-01T00:00:00Z')

 def test_usace_sources_keep_actual_station_identity(self):
  result=history_sources.parse_usace_payload({'time':'2024-02-01T00:00:00Z','value':'2.5'},'85420LA','2024-02')
  self.assertEqual(result['rows'][0]['station'],'USACE-85420LA')
  self.assertEqual(result['rows'][0]['datum'],'USACE station datum (unresolved)')

class TestResumableAcquisition(unittest.TestCase):
 def test_existing_successful_partition_is_skipped_without_refresh(self):
  result={'rows':[{'time':'2024-02-01T00:00:00Z','station':'MAUL1','variable':'stage','value':1,'unit':'ft','datum':'gage height'}], 'source':'fixture','request':'fixture','status':'retrieved','error':None}
  calls=[]
  def fetcher(month): calls.append(month); return result
  with tempfile.TemporaryDirectory() as temporary:
   root=pathlib.Path(temporary)
   history.acquire_month('2024-02',['MAUL1'],root=root,fetchers={'MAUL1':fetcher})
   history.acquire_month('2024-02',['MAUL1'],root=root,fetchers={'MAUL1':fetcher})
   self.assertEqual(calls,['2024-02'])

 def test_failed_source_is_recorded_and_has_no_rows(self):
  result=history_sources.failure_result('MAUL1','2024-02','fixture','HTTP 403')
  with tempfile.TemporaryDirectory() as temporary:
   record=history.acquire_month('2024-02',['MAUL1'],root=pathlib.Path(temporary),fetchers={'MAUL1':lambda month:result})
   self.assertEqual(record['sources']['MAUL1']['status'],'retrieval_error')
   self.assertEqual(record['sources']['MAUL1']['row_count'],0)

 def test_successful_empty_response_is_unavailable_not_successful_coverage(self):
  result={'rows':[],'source':'fixture','request':'fixture','status':'retrieved','error':None}
  with tempfile.TemporaryDirectory() as temporary:
   root=pathlib.Path(temporary)
   record=history.acquire_month('2024-02',['MAUL1'],root=root,fetchers={'MAUL1':lambda month:result})
   self.assertEqual(record['sources']['MAUL1']['status'],'queried_unavailable')
   self.assertFalse(history.partition_path(root,'MAUL1','2024-02').exists())

if __name__=='__main__': unittest.main()
