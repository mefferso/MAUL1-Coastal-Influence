import copy
import datetime as dt
import gzip
import json
import pathlib
import sys
import tempfile
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import phase4
import evidence
from test_evidence import observations,T


class Phase4Tests(unittest.TestCase):
    def test_calibration_cannot_see_holdout_discharge(self):
        idx=observations()
        before=phase4.calibrate(idx)
        idx[('DENL1','discharge')][dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)] = dict(next(iter(idx[('DENL1','discharge')].values())),value=1e8)
        self.assertEqual(phase4.calibrate(idx),before)

    def test_sequential_paths_are_not_compound(self):
        rows=[evidence.assess(observations(True,False,False),T),evidence.assess(observations(False),T+dt.timedelta(hours=1))]
        self.assertEqual(phase4.summarize(rows)['category'],'Indeterminate')
        self.assertTrue(phase4.summarize(rows)['sequential_signals'])

    def test_replay_differs_from_later_retrospective_evidence(self):
        idx=observations()
        early=evidence.assess(idx,T-dt.timedelta(hours=24))
        later=evidence.assess(idx,T)
        self.assertEqual(early['category'],'Indeterminate')
        self.assertEqual(phase4.summarize([early,later])['category'],'Compound-supported')
        self.assertNotEqual(early['category'],later['category'])

    def test_seam_uses_complete_feature_history_and_event_recovery(self):
        start=dt.datetime(2023,1,5,tzinfo=dt.timezone.utc)
        self.assertEqual(phase4.subset(start,start+dt.timedelta(hours=6)),'excluded_split_seam')
        self.assertEqual(phase4.subset(start+dt.timedelta(days=10),start+dt.timedelta(days=11)),'holdout_2023_onward')

    def test_mixed_residual_datum_and_quality_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'hourly').mkdir()
            base={'station':'NWCL1','time':'2020-01-01T00:00:00Z','coverage':10,'unit':'ft','missing':False,'value':1}
            rows=[dict(base,variable='water',datum='MLLW'),dict(base,variable='prediction',datum='NAVD88')]
            with gzip.open(root/'hourly/2020-01.json.gz','wt') as f: json.dump({'records':rows},f)
            (root/'quality.json').write_text(json.dumps({'findings':[]}))
            idx=phase4.load_inputs(root)
            residual=next(iter(idx[('NWCL1','residual')].values()))
            self.assertIsNone(residual['value'])

    def test_quality_flags_propagate_to_derived_residual_and_vectors(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'hourly').mkdir()
            base={'station':'NWCL1','time':'2020-01-01T00:00:00Z','coverage':10,'missing':False,'value':1,'datum':'MLLW','unit':'ft'}
            rows=[dict(base,variable=v) for v in ('water','prediction','wind_u','wind_v')]
            with gzip.open(root/'hourly/2020-01.json.gz','wt') as f: json.dump({'records':rows},f)
            findings=[{'group':['NWCL1',v],'from_time':'2020-01-01T00:06:00Z','to_time':'2020-01-01T00:12:00Z','kind':'suspicious_jump'} for v in ('water','wind')]
            (root/'quality.json').write_text(json.dumps({'findings':findings}))
            idx=phase4.load_inputs(root)
            for v in ('residual','wind_u','wind_v'):
                self.assertTrue(next(iter(idx[('NWCL1',v)].values()))['phase4_quality_excluded'])

    def test_replay_ignores_future_dependent_archive_QC(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'hourly').mkdir()
            rows=[]
            for key,series in observations(False).items():
                if key==('NWCL1','residual'):
                    for row in series.values():
                        rows.extend([dict(row,variable='water'),dict(row,variable='prediction',value=0)])
                elif key not in [('NWCL1','water'),('NWCL1','prediction')]:rows.extend(series.values())
            with gzip.open(root/'hourly/2020-09.json.gz','wt') as f:json.dump({'records':rows},f)
            (root/'quality.json').write_text(json.dumps({'findings':[]}))
            before=evidence.assess(phase4.load_inputs(root,quality_mode='causal'),T)
            future=[{'group':['NWCL1','water'],'from_time':evidence.iso(T-dt.timedelta(hours=1)),
                     'to_time':evidence.iso(T+dt.timedelta(hours=1)),'kind':'suspicious_jump'}]
            (root/'quality.json').write_text(json.dumps({'findings':future}))
            future_time=T+dt.timedelta(hours=1)
            rows.extend(dict(row,time=evidence.iso(future_time),value=1e8) for row in list(rows) if row['time']==evidence.iso(T))
            with gzip.open(root/'hourly/2020-09.json.gz','wt') as f:json.dump({'records':rows},f)
            after=evidence.assess(phase4.load_inputs(root,quality_mode='causal'),T)
            self.assertEqual(before,after)
            self.assertEqual(before['category'],'Coastal-supported')

    def test_issue_calibration_excludes_future_values(self):
        idx=observations()
        before=phase4.replay_thresholds(idx,[T])[T]
        future=T+dt.timedelta(hours=1)
        idx[('DENL1','discharge')][future]=dict(next(iter(idx[('DENL1','discharge')].values())),value=1e9)
        self.assertEqual(phase4.replay_thresholds(idx,[T])[T],before)
        self.assertLessEqual(before['training_end_exclusive_utc'],evidence.iso(T))

    def test_control_forcing_presence_counts_sequential_indeterminate(self):
        rows=[evidence.assess(observations(True,False,False),T),evidence.assess(observations(False),T+dt.timedelta(hours=1))]
        record=phase4.summarize(rows)
        self.assertEqual(record['category'],'Indeterminate')
        self.assertTrue(phase4.has_forcing(record))

    def test_early_coastal_exclusion_has_consistent_explanation(self):
        row=evidence.assess(observations(False),T)
        self.assertEqual(row['category'],'Coastal-supported')
        masked=phase4.exclude_early_coastal(row)
        self.assertEqual(masked['category'],'Indeterminate')
        self.assertTrue(masked['explanation'].startswith('Indeterminate:'))
        self.assertFalse(masked['coastal_association_eligible'])
        self.assertEqual(row['category'],'Coastal-supported')

    def test_deterministic_encoding(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'test.json.gz'
            phase4.write_json(p,{'b':2,'a':1});first=p.read_bytes()
            phase4.write_json(p,{'a':1,'b':2});self.assertEqual(p.read_bytes(),first)

    def test_named_event_labels_do_not_enter_assessment(self):
        self.assertNotIn('event',evidence.assess(observations(),T))


if __name__=='__main__':unittest.main()
