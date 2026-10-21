"""Reproduce Phase 4 from frozen archive products, with no network requests."""
import argparse
import bisect
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
import statistics
from collections import Counter, defaultdict

import evidence
from evidence import HOUR, UTC, iso

SCHEMA = '4.1'
BOUNDARY = dt.datetime(2023,1,1,tzinfo=UTC)
BASE_COMMIT = '1217a498247a85f60c37c4b3a1e882338f53e12e'


def stamp(value): return dt.datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(UTC)


def write_json(path, data):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    content=(json.dumps(data,sort_keys=True,indent=None if path.suffix=='.gz' else 2,allow_nan=False)+'\n').encode()
    path.write_bytes(gzip.compress(content,mtime=0) if path.suffix=='.gz' else content)


def load_inputs(root, quality_mode='retrospective'):
    if quality_mode not in ('retrospective','causal'):raise ValueError('Unknown quality mode')
    root=pathlib.Path(root)
    needed={(s,v) for s,v,_,_ in evidence.SERIES}|{('NWCL1','water'),('NWCL1','prediction')}
    index=defaultdict(dict)
    for path in sorted((root/'hourly').glob('*.json.gz')):
        with gzip.open(path,'rt') as f: payload=json.load(f)
        for row in payload['records']:
            key=row['station'],row['variable']
            if key in needed: index[key][stamp(row['time'])]=row
    quality_path=root/'quality.json'
    quality=json.loads(quality_path.read_text()) if quality_path.exists() else {'findings':[]}
    for finding in quality['findings'] if quality_mode=='retrospective' else []:
        group=finding.get('group',[])
        if len(group)!=2: continue
        keys=[tuple(group)]
        if group==['NWCL1','wind'] or group==['NWCL1','wind_direction']:
            keys += [('NWCL1','wind_u'),('NWCL1','wind_v')]
        for field in ('from_time','to_time','time'):
            if not finding.get(field): continue
            time=stamp(finding[field]).replace(minute=0,second=0,microsecond=0)
            for key in keys:
                if time in index.get(key,{}): index[key][time]['phase4_quality_excluded']=True
    if quality_mode=='causal':
        # Fixed hourly magnitude screens, declared without the future month.
        # Flag only the newly observed endpoint; never rewrite a prior bin.
        limits={'stage':5.,'water':5.,'prediction':5.,'discharge':10000.,'wind_u':50.,'wind_v':50.}
        for (station,variable),series in index.items():
            if variable not in limits:continue
            previous=None;previous_time=None
            for time,row in sorted(series.items()):
                if previous is not None and time-previous_time==HOUR and row.get('datum')==previous.get('datum') and row.get('unit')==previous.get('unit'):
                    values=(previous.get('value'),row.get('value'))
                    if all(isinstance(v,(int,float)) and math.isfinite(v) for v in values) and abs(values[1]-values[0])>limits[variable]:
                        row['phase4_quality_excluded']=True
                previous,previous_time=row,time
    # Never reuse an unverified derived residual. Same UTC bin, unit and datum
    # pairing is mandatory; this is an hourly aggregate residual, not a raw exact-time pair.
    index[('NWCL1','residual')]={}
    for time, water in index.get(('NWCL1','water'),{}).items():
        prediction=index.get(('NWCL1','prediction'),{}).get(time)
        same=bool(prediction and water.get('datum') and water['datum']==prediction.get('datum') and water.get('unit')==prediction.get('unit')=='ft')
        good=same and evidence.valid(water,'ft') and evidence.valid(prediction,'ft')
        excluded=bool(water.get('phase4_quality_excluded') or (prediction or {}).get('phase4_quality_excluded'))
        index[('NWCL1','residual')][time]=dict(time=iso(time),station='NWCL1',variable='residual',
             value=round(water['value']-prediction['value'],6) if good else None,
             unit='ft',datum=water.get('datum') if same else None,
             coverage=min(water.get('coverage',0),(prediction or {}).get('coverage',0)),
             missing=not good,phase4_quality_excluded=excluded,
             source='same-hour same-datum observed hourly aggregate minus predicted hourly aggregate')
    return index


def quantile(values, fraction):
    values=sorted(values)
    if not values: return None
    pos=(len(values)-1)*fraction;lo=math.floor(pos);hi=math.ceil(pos)
    return values[lo]+(values[hi]-values[lo])*(pos-lo)


def calibrate(index):
    values=[r['value'] for t,r in index.get(('DENL1','discharge'),{}).items()
            if dt.datetime(2016,1,1,tzinfo=UTC)<=t<BOUNDARY-dt.timedelta(hours=72)
            and evidence.valid(r,'cfs')]
    # Freeze an upper-decile definition without consulting response labels.
    return dict(period_end_exclusive_utc=iso(BOUNDARY-dt.timedelta(hours=72)),
                sample_hours=len(values), discharge_quantiles_cfs={str(p):quantile(values,p) for p in (.25,.5,.75,.9,.95)},
                discharge_high_cfs=quantile(values,.9) or evidence.DEFAULTS['discharge_high_cfs'])


def replay_thresholds(index, issues):
    """Expanding calibration history strictly before issue, frozen at split seam."""
    cutoff=BOUNDARY-dt.timedelta(hours=72)
    samples=sorted((time,r['value']) for time,r in index.get(('DENL1','discharge'),{}).items()
                   if dt.datetime(2016,1,1,tzinfo=UTC)<=time<cutoff and evidence.valid(r,'cfs'))
    values=[];cursor=0;result={}
    for issue in sorted(set(issues)):
        end=min(issue,cutoff)
        while cursor<len(samples) and samples[cursor][0]+HOUR<=end:
            bisect.insort(values,samples[cursor][1]);cursor+=1
        if len(values)>=1000:
            pos=(len(values)-1)*.9;lo=math.floor(pos);hi=math.ceil(pos)
            high=values[lo]+(values[hi]-values[lo])*(pos-lo)
        else:high=evidence.DEFAULTS['discharge_high_cfs']
        result[issue]=dict(discharge_high_cfs=high,training_end_exclusive_utc=iso(end),
                           sample_hours=len(values),method='prior calibration-era upper decile; fixed 20000-cfs fallback before 1000 prior hours')
    return result


def has_forcing(record):
    return any(record['pathway_timing'][name]['present_hours']>0 for name in ('river','coastal'))


def exclude_early_coastal(row):
    result=dict(row,flags=dict(row['flags'],coastal='unknown'),coastal_association_eligible=False,
                physical_coastal_flag=row['flags']['coastal'])
    result['category']=evidence.category(result['flags']['river'],'unknown')
    result['explanation']=f"{result['category']}: river={result['flags']['river']}; coastal association excluded before the event's coastal antecedent window (physical coastal screen={row['flags']['coastal']}). This exclusion is not missing observations."
    result['supporting']=[x+' (physical observation outside eligible coastal association window)' if x.split(':')[0] in ('residual','lake','wind') else x for x in row['supporting']]
    return result


def subset(start,end,lookback_hours=78):
    left=start-dt.timedelta(hours=lookback_hours)
    if end<=BOUNDARY-dt.timedelta(hours=72):return 'calibration_2016_2022'
    if left>=BOUNDARY+dt.timedelta(hours=72):return 'holdout_2023_onward'
    return 'excluded_split_seam'


def counts(rows):
    result=Counter(r['category'] for r in rows)
    return {k:result[k] for k in evidence.CATEGORIES}


def summarize(rows):
    river=[r for r in rows if r['flags']['river']=='present']
    coast=[r for r in rows if r['flags']['coastal']=='present']
    compound=[r for r in rows if r['flags']['river']=='present' and r['flags']['coastal']=='present']
    sequential=bool(river and coast and not compound)
    selected=('Indeterminate' if sequential else 'Compound-supported' if compound else
              'River-supported' if river else 'Coastal-supported' if coast else 'Indeterminate')
    core=('river','residual','lake','wind')
    known=sum(all(r['flags'][k]!='unknown' for k in core) for r in rows)
    fraction=known/len(rows) if rows else 0
    witnesses={}
    for name, candidates in [('river',river),('coastal',coast),('compound',compound),('indeterminate',[r for r in rows if r['category']=='Indeterminate'])]:
        if candidates:witnesses[name]=candidates[0]
    intervals={}
    for name in core+('coastal','pass_context'):
        items=[r for r in rows if r['flags'][name]=='present']
        intervals[name]=dict(present_hours=len(items),first_utc=items[0]['issue_time_utc'] if items else None,
                             last_utc=items[-1]['issue_time_utc'] if items else None,
                             absent_hours=sum(r['flags'][name]=='absent' for r in rows),
                             unknown_hours=sum(r['flags'][name]=='unknown' for r in rows))
    return dict(category=selected, assessment_hours=len(rows),coverage_qualified_90pct=fraction>=.9,
                evidence_sufficient_fraction=round(fraction,4),sequential_signals=sequential,
                coexistence_hours=len(compound),
                compound_context={'coastal_during_elevated_discharge_hours':sum(r['metrics']['discharge']['elevated_discharge'] for r in compound),
                                  'coastal_during_rising_discharge_hours':sum(r['metrics']['discharge']['rising_discharge'] for r in compound),
                                  'meaningful_response_not_required':'Overlap of forcing observations; no interaction or target-response prediction is established.'},
                hourly_class_counts=counts(rows),pathway_timing=intervals,witnesses=witnesses,
                supporting=sorted({x for r in rows for x in r['supporting']}),
                contradictory=sorted({x for r in rows for x in r['contradictory']}),
                missing=sorted({x for r in rows for x in r['missing']}),
                explanation=('River and coastal signals occur in separate intervals; compound support is not established.' if sequential else
                             f'{selected}: requires a persistent pathway in its event-specific timing window; compound requires simultaneous support.'),
                uncertainty=['Retrospective supporting evidence is not a causal label, forecast or demonstrated interaction.',
                             'Event selection and assessment windows use the full historical response catalogue.',
                             'DENL1 absence cannot exclude tributary/local runoff downstream.',
                             'Hourly means preserve native datums; same-hour residual pairing may differ from raw coincident residuals.'])


def event_bounds(event):
    return stamp(event['onset_utc'])-dt.timedelta(hours=72),stamp(event['peak_utc'])+HOUR


def assess_event(event, evaluate, coastal_antecedent=18):
    onset=stamp(event['onset_utc']);start,end=event_bounds(event)
    rows=[];cursor=start
    while cursor<=end:
        row=evaluate(cursor)
        if cursor<onset-dt.timedelta(hours=coastal_antecedent):
            # Preserve original metrics in witnesses but do not count an older
            # coastal signal as associated with this response.
            row=exclude_early_coastal(row)
        rows.append(row);cursor+=HOUR
    result=summarize(rows)
    result.update(record_id=event['event_id'],sample_type='response_event',mode='retrospective',
                  source_event=event,analysis_start_utc=iso(start),analysis_end_utc=iso(end),
                  temporal_subset=subset(start,max(end,stamp(event['recovery_end_utc']) if event.get('recovery_end_utc') else end)),
                  original_temporal_subset=subset(onset,stamp(event['peak_utc']),0))
    for name,item in result['pathway_timing'].items():
        item['first_relative_to_onset_hours']=(stamp(item['first_utc'])-onset).total_seconds()/3600 if item['first_utc'] and event['onset_known'] else None
    if not event['onset_known']:result['uncertainty'].append('MAUL1 onset is censored; timing relative to true onset is unknown.')
    if event['rise_duration_hours']>168:result['uncertainty'].append('Long response excursion: later forcing episodes may be unrelated to its original onset.')
    return result


def assess_control(control,evaluate):
    start,end=stamp(control['start_utc']),stamp(control['end_utc'])
    rows=[];cursor=start+HOUR
    while cursor<=end:rows.append(evaluate(cursor));cursor+=HOUR
    result=summarize(rows)
    result.update(record_id=control['control_candidate_id'],sample_type='eligible_negative_control',
                  mode='retrospective',analysis_start_utc=iso(start),analysis_end_utc=iso(end),
                  source_control=control,temporal_subset=subset(start,end),original_temporal_subset=control['temporal_subset'])
    result['uncertainty'].append('No >=1-ft MAUL1 event under frozen Phase 3B selection; smaller responses may occur. Forcing here is not a false forecast alarm.')
    return result


def fingerprints(root):
    paths=sorted((root/'hourly').glob('*.json.gz'))+[root/'quality.json',root/'manifest.json',root/'phase3b/validation.json',root/'phase3b/cases.json']
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()}


def feature_dependence(records):
    pairs=[]
    for i,a in enumerate(records):
        for b in records[i+1:]:
            sa,ea=stamp(a['analysis_start_utc'])-dt.timedelta(hours=78),stamp(a['analysis_end_utc'])
            sb,eb=stamp(b['analysis_start_utc'])-dt.timedelta(hours=78),stamp(b['analysis_end_utc'])
            if sa<eb and sb<ea:pairs.append([a['record_id'],b['record_id']])
    return dict(overlapping_feature_window_pairs=pairs,count=len(pairs),
                interpretation='Frozen response recovery and control buffers are preserved; overlapping feature windows are dependent, so no independent sample-size or precision claim is made.')


def write_csv(path,rows):
    fields=['record_id','sample_type','category','temporal_subset','coverage_qualified_90pct','evidence_sufficient_fraction','coexistence_hours','sequential_signals','analysis_start_utc','analysis_end_utc']
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        writer.writerows({k:r[k] for k in fields} for r in rows)


def run(root='site/data/history',output=None):
    root=pathlib.Path(root);out=pathlib.Path(output) if output else root/'phase4'
    out.mkdir(parents=True,exist_ok=True)
    frozen=json.loads((root/'phase3b/validation.json').read_text())['maul1_first_analysis']
    original_cases=json.loads((root/'phase3b/cases.json').read_text())['cases']
    source_hashes=fingerprints(root)
    print('Loading archived hourly observations',flush=True)
    index=load_inputs(root);calibration=calibrate(index)
    thresholds=evidence.DEFAULTS|{'discharge_high_cfs':calibration['discharge_high_cfs']}
    # Freeze these variants before inspecting class counts; never select a winner.
    variants={'primary':{},'lower_magnitudes':{k:thresholds[k]*.75 for k in ('discharge_rise_cfs','residual_ft','residual_rise_ft','lake_rise_ft','wind_projection_knots')},
              'higher_magnitudes':{k:thresholds[k]*1.25 for k in ('discharge_rise_cfs','residual_ft','residual_rise_ft','lake_rise_ft','wind_projection_knots')},
              'wind_toward_240':{'wind_axis_degrees':240.},'wind_toward_300':{'wind_axis_degrees':300.},
              'coastal_antecedent_6h':{},'coastal_antecedent_36h':{}}
    # Cache only issues actually needed, metrics once, threshold decisions per variant.
    issues=set()
    events=frozen['events']
    controls=[c for c in frozen['negative_controls']['windows'] if c['status']=='eligible_control_candidate']
    for e in events:
        start,end=event_bounds(e);cursor=start
        while cursor<=end:issues.add(cursor);cursor+=HOUR
        onset=stamp(e['onset_utc'])
        for offset in (-24,0,12,24):issues.add(onset+dt.timedelta(hours=offset))
    for c in controls:
        cursor=stamp(c['start_utc'])+HOUR;end=stamp(c['end_utc'])
        while cursor<=end:issues.add(cursor);cursor+=HOUR
    for c in original_cases:
        cursor=stamp(c['start_utc']);end=stamp(c['end_utc_exclusive'])
        while cursor<=end:issues.add(cursor);cursor+=dt.timedelta(hours=6)
    print(f'Assessing {len(issues)} completed-hour issues with frozen variants',flush=True)
    # Store decisions needed for primary and lightweight per-variant rows.
    primary={}; alternatives={name:{} for name in variants if name!='primary'}
    for number,time in enumerate(sorted(issues)):
        m=evidence.metrics(index,time)
        row=evidence.decide(m,time,thresholds);primary[time]=row
        for name,overrides in variants.items():
            if name=='primary':continue
            alternate=evidence.decide(m,time,thresholds|overrides) if overrides else row
            alternatives[name][time]=alternate
        if number and number%10000==0:print(f'  {number} issues',flush=True)
    result_events=[assess_event(e,primary.__getitem__) for e in events]
    result_controls=[assess_control(c,primary.__getitem__) for c in controls]
    sensitivity={}
    for name,mapping in [('primary',primary)]+list(alternatives.items()):
        lag=6 if name=='coastal_antecedent_6h' else 36 if name=='coastal_antecedent_36h' else 18
        classified=[assess_event(e,mapping.__getitem__,lag) for e in events]
        control_rows=[assess_control(c,mapping.__getitem__) for c in controls]
        sensitivity[name]=dict(overrides=variants[name],coastal_antecedent_hours=lag,event_counts=counts(classified),control_counts=counts(control_rows),
                               event_changes_from_primary=[dict(record_id=a['record_id'],primary=a['category'],variant=b['category']) for a,b in zip(result_events,classified) if a['category']!=b['category']],
                               counts_by_subset={s:counts([r for r in classified if r['temporal_subset']==s]) for s in ('calibration_2016_2022','holdout_2023_onward','excluded_split_seam')})
    print('Building independent causal-QC replay',flush=True)
    replay_index=load_inputs(root,quality_mode='causal')
    replay_parameters=replay_thresholds(replay_index,issues)
    replay_cache={}
    def replay_at(time):
        if time not in replay_cache:
            parameters=replay_parameters[time]
            assessment=evidence.assess(replay_index,time,thresholds|{'discharge_high_cfs':parameters['discharge_high_cfs']})
            assessment['calibration_as_of_issue']=parameters
            assessment['quality_mode']='fixed causal hourly jumps; future-dependent archived QC excluded'
            replay_cache[time]=assessment
        return replay_cache[time]
    replay=[]
    for e,result in zip(events,result_events):
        for offset in (-24,0,12,24):
            time=stamp(e['onset_utc'])+dt.timedelta(hours=offset)
            replay.append(dict(record_id=e['event_id'],sample_type='catalog_conditioned_event_snapshot',offset_from_retrospective_onset_hours=offset,
                               assessment=replay_at(time),retrospective_category=result['category'],differs_from_retrospective=replay_at(time)['category']!=result['category']))
    for c in controls:
        time=stamp(c['end_utc']);replay.append(dict(record_id=c['control_candidate_id'],sample_type='control_endpoint',assessment=replay_at(time)))
    case_results=[]
    by_id={r['record_id']:r for r in result_events}
    for case in original_cases:
        start,end=stamp(case['start_utc']),stamp(case['end_utc_exclusive'])
        snapshots=[];cursor=start
        while cursor<=end:
            snapshots.append(replay_at(cursor));replay.append(dict(record_id=case['event_id'],sample_type='fixed_six_hour_case_clock',assessment=replay_at(cursor)));cursor+=dt.timedelta(hours=6)
        selected=[by_id[eid] for eid in case['revised_response_event_ids']]
        within=summarize(snapshots)
        case_results.append(dict(case_id=case['event_id'],name=case['name'],start_utc=iso(start),end_utc_exclusive=iso(end),
                                 retrospective_events=selected,within_case_six_hour_summary=within,issue_time_snapshots=snapshots,
                                 external_context=case['external_storm_context'],prior_timing_context=case['revised_method_interpretation'],
                                 caveat='Case context is independent documentary information, not reference labels. Full-event interpretations may extend outside this named case; within-case snapshots are shown separately.'))
    all_records=result_events+result_controls
    summary=dict(schema_version=SCHEMA,mode='retrospective evidence research',event_count=len(events),control_count=len(controls),event_counts=counts(result_events),control_counts=counts(result_controls),
                 coverage_qualified_events=sum(r['coverage_qualified_90pct'] for r in result_events),
                 coverage_qualified_controls=sum(r['coverage_qualified_90pct'] for r in result_controls),
                 indeterminate_event_fraction=round(sum(r['category']=='Indeterminate' for r in result_events)/len(events),4),
                 coverage_qualified_event_counts=counts([r for r in result_events if r['coverage_qualified_90pct']]),
                 events_without_supported_path=sum(r['pathway_timing']['river']['present_hours']==0 and r['pathway_timing']['coastal']['present_hours']==0 for r in result_events),
                 events_with_both_paths=sum(r['pathway_timing']['river']['present_hours']>0 and r['pathway_timing']['coastal']['present_hours']>0 for r in result_events),
                 sequential_signal_events=sum(r['sequential_signals'] for r in result_events),
                 controls_with_forcing_evidence=sum(has_forcing(r) for r in result_controls),
                 controls_with_determinate_class=sum(r['category']!='Indeterminate' for r in result_controls),
                 replay=dict(snapshot_count=len(replay),event_snapshot_count=len(events)*4,event_snapshot_differences=sum(r.get('differs_from_retrospective',False) for r in replay),
                             availability='Completed hourly-bin valid-time-only replay; receipt timestamps unavailable. Event snapshot selection uses retrospective onsets; assessments do not.'),
                 counts_by_subset={s:dict(events=counts([r for r in result_events if r['temporal_subset']==s]),controls=counts([r for r in result_controls if r['temporal_subset']==s])) for s in ('calibration_2016_2022','holdout_2023_onward','excluded_split_seam')},
                 controls_by_original_category={c:counts([r for r in result_controls if c in r['source_control']['categories']]) for c in sorted({c for r in result_controls for c in r['source_control']['categories']})},
                 sensitivity={k:dict(event_counts=v['event_counts'],changed_events=len(v['event_changes_from_primary'])) for k,v in sensitivity.items()},
                 phase5_readiness='Not yet stable enough to justify operational forecasts. Supports continued experimental feature research only; no independent reference labels or out-of-sample forecast evaluation.',
                 conclusion='Observation-based evidence screens distinguish some consistent forcing patterns. Unknowns, contradictory signals, long event windows, rule sensitivity and local runoff limit attribution and predictive interpretation.')
    provenance=dict(schema_version=SCHEMA,base_repository_commit=BASE_COMMIT,input_sha256=source_hashes,
                    thresholds=thresholds,calibration=calibration,
                    analysis_source_sha256={name:hashlib.sha256((pathlib.Path(__file__).resolve().parent/name).read_bytes()).hexdigest() for name in ('evidence.py','phase4.py','phase4_report.py')},
                    rules_frozen_before_evaluation=True,accuracy='unavailable: no independent reference class labels',
                    datum_policy='No absolute cross-station comparison or historical NAVD88 conversion; hourly residual requires matching datum and unit.',
                    quality_policy='Retrospective: exclude archived quality-finding endpoint hours. Replay: ignore full-month adaptive flags; apply fixed causal hourly jumps only to newly completed endpoints, never backward. Native hourly quality limitations persist.',
                    replay_policy=summary['replay']['availability'])
    independence=feature_dependence(all_records)
    independence.update(boundary_utc=iso(BOUNDARY),embargo_hours=72,feature_lookback_hours=78,
                        rule='Keep frozen recovery-defined MAUL1 events and eligible control windows; extend split checks over antecedent assessment and feature history plus observed recovery.',
                        changes_from_original_split=[dict(record_id=r['record_id'],original=r['original_temporal_subset'],phase4=r['temporal_subset']) for r in all_records if r['original_temporal_subset']!=r['temporal_subset']],
                        limitation='Threshold hypotheses and historical cases were informed by prior exploratory work; the temporal holdout is descriptive frozen-rule evaluation, not pristine blind validation.')
    write_json(out/'historical.json',dict(provenance=provenance,events=result_events,controls=result_controls))
    write_json(out/'replay.json.gz',dict(schema_version=SCHEMA,mode='valid_time_only_issue_assessment',provenance=provenance,rows=replay))
    write_json(out/'cases.json',dict(schema_version=SCHEMA,cases=case_results))
    write_json(out/'sensitivity.json',dict(schema_version=SCHEMA,variants=sensitivity,note='Prespecified screens; no variant chosen based on holdout agreement or outcome.'))
    write_json(out/'independence.json',independence)
    write_json(out/'summary.json',summary)
    write_json(out/'coverage.json',dict(schema_version=SCHEMA,
        criterion='All four core evidence flags known for >=90% of assessed hours; this is evidence sufficiency, not source certification or a confidence score.',
        records=[dict(record_id=r['record_id'],sample_type=r['sample_type'],coverage_qualified_90pct=r['coverage_qualified_90pct'],
                      evidence_sufficient_fraction=r['evidence_sufficient_fraction'],pathway_timing=r['pathway_timing']) for r in all_records],
        quality_excluded_hourly_bins={f'{s}:{v}':sum(bool(r.get('phase4_quality_excluded')) for r in series.values()) for (s,v),series in index.items()}))
    write_json(out/'provenance.json',provenance)
    write_csv(out/'classifications.csv',all_records)
    from phase4_report import render_report,render_cases
    (out/'report.md').write_text(render_report(summary,provenance,independence,case_results)+'\n')
    (out/'case-studies.md').write_text(render_cases(case_results)+'\n')
    (out/'methodology.md').write_text((pathlib.Path(__file__).resolve().parents[1]/'docs/phase4-methodology.md').read_text())
    print(json.dumps(summary,sort_keys=True),flush=True)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='site/data/history');parser.add_argument('--output')
    args=parser.parse_args();run(args.root,args.output)
