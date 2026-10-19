import gzip
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0,'scripts')
import history


class TestPartitionContracts(unittest.TestCase):
 def test_month_range_is_inclusive_and_utc_month_ordered(self):
  self.assertEqual(history.month_range('2016-11','2017-02'),['2016-11','2016-12','2017-01','2017-02'])

 def test_partition_path_is_station_and_month_specific(self):
  root=pathlib.Path('/tmp/history-contracts')
  self.assertEqual(history.partition_path(root,'MAUL1','2024-02'),root/'raw'/'MAUL1'/'2024-02.json.gz')

 def test_canonical_month_describes_half_open_bounds(self):
  result=history.canonical_month('2024-02','2024-02')
  self.assertEqual(result['months'],['2024-02'])
  self.assertEqual(result['schema_version'],'3A.1')

 def test_write_partition_is_deterministic_and_skips_existing_without_refresh(self):
  payload={'schema_version':'3A.1','station':'MAUL1','month_start':'2024-02-01T00:00:00Z','month_end_exclusive':'2024-03-01T00:00:00Z','rows':[{'time':'2024-02-01T00:00:00Z','variable':'stage','value':1.2}]}
  with tempfile.TemporaryDirectory() as temporary:
   path=pathlib.Path(temporary)/'raw'/'MAUL1'/'2024-02.json.gz'
   self.assertTrue(history.write_partition(path,payload))
   first=path.read_bytes()
   self.assertFalse(history.write_partition(path,payload))
   self.assertEqual(first,path.read_bytes())
   self.assertTrue(history.write_partition(path,payload,overwrite=True))
   self.assertEqual(first,path.read_bytes())
   self.assertEqual(json.loads(gzip.decompress(first)),payload)

 def test_duplicate_station_variable_timestamp_is_rejected(self):
  payload={'schema_version':'3A.1','station':'MAUL1','month_start':'2024-02-01T00:00:00Z','month_end_exclusive':'2024-03-01T00:00:00Z','rows':[{'time':'2024-02-01T00:00:00Z','variable':'stage','value':1.2},{'time':'2024-02-01T00:00:00Z','variable':'stage','value':1.3}]}
  with tempfile.TemporaryDirectory() as temporary:
   with self.assertRaises(ValueError): history.write_partition(pathlib.Path(temporary)/'partition.json.gz',payload)


if __name__=='__main__': unittest.main()
