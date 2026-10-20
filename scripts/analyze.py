"""Exploratory first-difference lag diagnostics; positive lag means input leads MAUL1."""
import json
import gzip
import math
from bisect import bisect_left,bisect_right
import pathlib
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from build import EVENTS
ROOT=pathlib.Path(__file__).resolve().parents[1]

def _dt(value):
 return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)

def _median(values):
 values=sorted(values)
 if not values:return None
 middle=len(values)//2
 return values[middle] if len(values)%2 else (values[middle-1]+values[middle])/2

def aggregate_hourly(rows,station,variable,start,end):
 """Aggregate actual observations into UTC hours; empty hours stay missing."""
 start_dt=_dt(start); end_dt=_dt(end)
 buckets=defaultdict(list)
 for row in rows:
  if row.get('station') != station or row.get('variable') != variable: continue
  stamp=_dt(row['time'])
  if start_dt <= stamp < end_dt: buckets[stamp.replace(minute=0,second=0,microsecond=0)].append(row)
 result=[]; cursor=start_dt.replace(minute=0,second=0,microsecond=0)
 while cursor < end_dt:
  records=buckets.get(cursor,[]); values=[float(r['value']) for r in records]
  # Median is robust for levels; discharge and wind components use means.
  value=(sum(values)/len(values) if variable in {'discharge','wind_u','wind_v'} and values else _median(values))
  item={'time':cursor.strftime('%Y-%m-%dT%H:%M:%SZ'),'value':round(value,6) if value is not None else None,
   'coverage':len(values),'missing':not bool(values),'station':station,'variable':variable}
  if records:
   item.update(unit=records[0].get('unit'),datum=records[0].get('datum'),source='derived hourly aggregation')
  result.append(item); cursor += timedelta(hours=1)
 return result

def trailing_change(rows,hours):
 lookup={_dt(r['time']):r for r in rows if r.get('value') is not None and r.get('coverage',1)}
 result=[]
 for stamp,row in sorted(lookup.items()):
  old=lookup.get(stamp-timedelta(hours=hours))
  if old and row.get('datum') == old.get('datum'):
   result.append(dict(row,time=stamp.strftime('%Y-%m-%dT%H:%M:%SZ'),value=round(row['value']-old['value'],6),window_hours=hours))
 return result

def robust_sigma(values):
 center=_median(values); deviations=[abs(v-center) for v in values]
 return 1.4826*(_median(deviations) or 0.0)

def _usable(row,min_coverage):
 return row.get('value') is not None and row.get('coverage',1) >= min_coverage

def coverage_summary(series,min_coverage=1):
 ordered=sorted(series,key=lambda r:r['time']); valid=[r for r in ordered if _usable(r,min_coverage)]
 expected=len(ordered); missing=expected-len(valid)
 return {'hours':expected,'valid_hours':len(valid),'missing_hours':missing,
  'missing_fraction':round(missing/expected,3) if expected else 1.0,
  'minimum_hourly_coverage':min_coverage}

def _datum_status(station,variable,datum):
 if station == 'MAUL1' and variable == 'stage' and datum == 'gage height':
  return 'native_gage_height',False
 if station == 'MAUL1' and variable == 'elevation' and datum == 'NAVD88':
  return 'direct_navd88',True
 if station == 'MAUL1':
  return 'native_unverified',False
 return 'source_native',False

def _episode_context(rows,min_coverage):
 datum=next((row.get('datum') for row in rows if row.get('datum') is not None),None)
 valid=[row for row in rows if _usable(row,min_coverage)]
 valid_by_time={_dt(row['time']):row for row in valid}
 return {'datum':datum,'valid':valid,'valid_by_time':valid_by_time,
  'valid_times':sorted(valid_by_time),'coverage':coverage_summary(rows,min_coverage)}

def _episode_record(status,station,variable,rows,onset=None,end=None,peak=None,
                    baseline=None,baseline_status='available',signal_threshold=None,
                    min_coverage=1,_prepared=None,**extra):
 prepared=_episode_context(rows,min_coverage) if _prepared is None else _prepared
 datum=prepared['datum']
 datum_status,navd88_eligible=_datum_status(station,variable,datum)
 valid=prepared['valid']; by_time=prepared['valid_by_time']
 record={'onset_utc':onset.strftime('%Y-%m-%dT%H:%M:%SZ') if onset else None,
  'onset_known':onset is not None,'peak_utc':peak.strftime('%Y-%m-%dT%H:%M:%SZ') if peak else None,
  'duration_hours':None,'rise':None,'max_hourly_rise':None,'status':status,
  'station':station,'variable':variable,'datum':datum,'datum_status':datum_status,
  'navd88_threshold_eligible':navd88_eligible,'coverage':prepared['coverage'],
  'baseline_status':baseline_status,'baseline_hours':72,'minimum_baseline_points':48,
  'sigma_threshold':signal_threshold,'signal_type':'positive_consecutive_hourly_rise'}
 if onset and end:
  record['duration_hours']=int((end-onset).total_seconds()/3600)+1
 if onset and peak and valid:
  before_index=bisect_left(prepared['valid_times'],onset)
  start_value=valid[before_index-1]['value'] if before_index else None
  peak_row=by_time.get(peak)
  if start_value is not None and peak_row is not None:
   record['rise']=round(peak_row['value']-start_value,6)
  changes=[]
  cursor=onset
  while cursor <= end:
   current=by_time.get(cursor); previous=by_time.get(cursor-timedelta(hours=1))
   if current and previous: changes.append(current['value']-previous['value'])
   cursor += timedelta(hours=1)
  if changes: record['max_hourly_rise']=round(max(changes),6)
 if baseline:
  record.update(baseline_median=round(baseline[0],6),robust_sigma=round(baseline[1],6))
 if signal_threshold is not None: record['positive_change_cutoff']=round(signal_threshold,6)
 record.update(extra)
 return record

def detect_episodes(series,station,variable,min_rise=0.0,min_duration_hours=3,
                    baseline_hours=72,min_baseline_points=48,sigma_threshold=2.0,
                    min_coverage=1,reset_hours=6,sigma_floor=1e-6):
 """Identify independent positive-rise episodes from one hourly series.

 The antecedent baseline is fixed at the candidate onset and uses only exact,
 consecutive hourly changes in the preceding ``baseline_hours``. Missing or
 below-coverage hours break both baseline support and episode persistence.
 """
 ordered=sorted(series,key=lambda row:row['time'])
 prepared=_episode_context(ordered,min_coverage)
 if not ordered:
  return [_episode_record('unavailable_baseline',station,variable,ordered,
   baseline_status='unavailable',signal_threshold=sigma_threshold,min_coverage=min_coverage,_prepared=prepared)]
 by_time={_dt(row['time']):row for row in ordered}
 ordered_times=sorted(by_time)
 changes={}
 for stamp,row in by_time.items():
  previous=by_time.get(stamp-timedelta(hours=1))
  if previous and _usable(row,min_coverage) and _usable(previous,min_coverage):
   changes[stamp]=row['value']-previous['value']
 change_times=sorted(changes)
 positive=[stamp for stamp in change_times if changes[stamp] > 0]
 if not positive:
  return [_episode_record('unavailable_baseline',station,variable,ordered,
   baseline_status='unavailable' if len(changes) < min_baseline_points else 'available',
   signal_threshold=sigma_threshold,min_coverage=min_coverage,_prepared=prepared)]

 episodes=[]; blocked_until=None; baseline_seen=False; uncertain_seen=False
 for candidate in positive:
  if blocked_until and candidate <= blocked_until: continue
  baseline_start=candidate-timedelta(hours=baseline_hours)
  candidate_index=bisect_left(change_times,candidate)
  baseline_start_index=bisect_left(change_times,baseline_start,0,candidate_index)
  baseline=[changes[stamp] for stamp in change_times[baseline_start_index:candidate_index]]
  if len(baseline) < min_baseline_points:
   # A rise already present at the archive boundary is useful evidence, but
   # its onset cannot be dated without the missing antecedent record.
   if candidate == positive[0]:
    end=candidate
    while end+timedelta(hours=1) in changes and changes[end+timedelta(hours=1)] > 0:
     end += timedelta(hours=1)
    run_length=int((end-candidate).total_seconds()/3600)+1
    if run_length >= min_duration_hours:
     peak=end
     episodes.append(_episode_record('already_underway',station,variable,ordered,
      end=end,peak=peak,baseline_status='unavailable',signal_threshold=sigma_threshold,
      min_coverage=min_coverage,_prepared=prepared,reason='archive begins during a sustained positive rise'))
     blocked_until=end+timedelta(hours=reset_hours)
    else:
     # Short positive noise before the first usable baseline is not enough
     # evidence that the archive began during an event; keep looking.
     pass
    continue
   continue
  baseline_seen=True
  center=_median(baseline); scale=robust_sigma(baseline)
  if scale <= sigma_floor:
   uncertain_seen=True
   continue
  cutoff=max(0.0,center+sigma_threshold*scale)
  if changes[candidate] <= cutoff: continue
  end=candidate
  while end+timedelta(hours=1) in changes and changes[end+timedelta(hours=1)] > 0:
   end += timedelta(hours=1)
  duration=int((end-candidate).total_seconds()/3600)+1
  gap_after_run=(end+timedelta(hours=1) in by_time and end+timedelta(hours=1) not in changes)
  peak_start=bisect_left(ordered_times,candidate)
  peak_end=bisect_right(ordered_times,end)
  peak=max(ordered_times[peak_start:peak_end],key=lambda stamp:by_time[stamp]['value'])
  record=_episode_record('gap' if gap_after_run else ('detected' if duration >= min_duration_hours else 'uncertain'),
   station,variable,ordered,onset=candidate,end=end,peak=peak,
   baseline=(center,scale),baseline_status='available',signal_threshold=cutoff,
   min_coverage=min_coverage,_prepared=prepared,minimum_rise=min_rise)
  if gap_after_run:
   record['reason']='missing or below-coverage hour broke positive persistence'
  elif record['rise'] is None or record['rise'] < min_rise or (record['max_hourly_rise'] or 0) <= 0:
   record['status']='uncertain' if duration >= min_duration_hours else 'no_signal'
   record['reason']='did not meet fixed magnitude/duration/rate safeguards'
  episodes.append(record)
  blocked_until=end+timedelta(hours=reset_hours)
 if episodes:return episodes
 if uncertain_seen:
  return [_episode_record('uncertain',station,variable,ordered,baseline_status='available',
   signal_threshold=sigma_threshold,min_coverage=min_coverage,
   _prepared=prepared,reason='robust baseline scale was zero or near zero')]
 if baseline_seen:
  return [_episode_record('no_signal',station,variable,ordered,baseline_status='available',
   signal_threshold=sigma_threshold,min_coverage=min_coverage,_prepared=prepared)]
 return [_episode_record('unavailable_baseline',station,variable,ordered,
  baseline_status='unavailable',signal_threshold=sigma_threshold,min_coverage=min_coverage,_prepared=prepared)]

def _result(status,threshold,baseline_hours,min_baseline_points,persistence,**extra):
 result=dict(onset_time=None,threshold_sigma=threshold,baseline_hours=baseline_hours,
  min_baseline_points=min_baseline_points,persistence=persistence,status=status)
 result.update(extra); return result

def detect_onset(series,threshold=2.0,baseline_hours=72,min_baseline_points=48,persistence=3,min_coverage=1,sigma_floor=1e-6):
 """Detect a sustained positive hourly rise using only the trailing record.

 The baseline is the preceding 72 hours of exact one-hour changes. At least
 48 usable baseline changes are required. Missing hours break persistence;
 near-zero MAD is uncertain rather than silently treated as zero noise.
 """
 ordered=sorted(series,key=lambda r:r['time']); by_time={_dt(r['time']):r for r in ordered}
 if not ordered:return _result('unavailable_baseline',threshold,baseline_hours,min_baseline_points,persistence)
 changes={}; saw_gap=False; saw_uncertain=False; baseline_available=False
 for stamp,row in by_time.items():
  previous=by_time.get(stamp-timedelta(hours=1))
  if previous and _usable(row,min_coverage) and _usable(previous,min_coverage):
   changes[stamp]=row['value']-previous['value']
 for candidate in sorted(changes):
  baseline_start=candidate-timedelta(hours=baseline_hours)
  baseline=[value for stamp,value in changes.items() if baseline_start <= stamp < candidate]
  if len(baseline) < min_baseline_points: continue
  baseline_available=True
  persistence_stamps=[candidate-timedelta(hours=offset) for offset in range(persistence-1,-1,-1)]
  if any(stamp not in changes for stamp in persistence_stamps):
   saw_gap=True; continue
  center=_median(baseline); scale=robust_sigma(baseline)
  if scale <= sigma_floor:
   saw_uncertain=True; continue
  cutoff=max(0.0,center+threshold*scale)
  if all(changes[stamp] > cutoff and changes[stamp] > 0 for stamp in persistence_stamps):
   return _result('detected',threshold,baseline_hours,min_baseline_points,persistence,
    onset_time=candidate.strftime('%Y-%m-%dT%H:%M:%SZ'),baseline_median=center,robust_sigma=scale,
    positive_change_cutoff=cutoff,signal_type='positive_consecutive_hourly_change')
 if not baseline_available:
  first=min(changes) if changes else None
  if first and all(first+timedelta(hours=i) in changes and changes[first+timedelta(hours=i)] > 0 for i in range(persistence)):
   return _result('already_underway',threshold,baseline_hours,min_baseline_points,persistence,
    evidence_start=first.strftime('%Y-%m-%dT%H:%M:%SZ'))
  return _result('unavailable_baseline',threshold,baseline_hours,min_baseline_points,persistence)
 if saw_gap:return _result('gap',threshold,baseline_hours,min_baseline_points,persistence)
 if saw_uncertain:return _result('uncertain',threshold,baseline_hours,min_baseline_points,persistence)
 return _result('no_signal',threshold,baseline_hours,min_baseline_points,persistence)

def compare_onsets(predictor,target,threshold=2.0,**kwargs):
 found=detect_onset(predictor,threshold=threshold,**kwargs); maul=detect_onset(target,threshold=threshold,**kwargs)
 lead=None
 if found['onset_time'] and maul['onset_time']:
  lead=(_dt(maul['onset_time'])-_dt(found['onset_time'])).total_seconds()/3600
  status='detected_not_validated'
 elif found['status'] in {'uncertain','gap'} or maul['status'] in {'uncertain','gap'}:
  status='uncertain'
 else: status='unavailable'
 return dict(threshold_sigma=threshold,predictor_onset_utc=found['onset_time'],maul1_onset_utc=maul['onset_time'],lead_hours=lead,
  predictor_status=found['status'],maul1_status=maul['status'],status=status,
  note='First-signal timing only; no validated precursor or causal attribution.',
  predictor_coverage=coverage_summary(predictor,kwargs.get('min_coverage',1)),
  maul1_coverage=coverage_summary(target,kwargs.get('min_coverage',1)))

def vector_hourly(rows,start,end):
 u=aggregate_hourly(rows,'NWCL1','wind_u',start,end); v=aggregate_hourly(rows,'NWCL1','wind_v',start,end)
 result=[]
 for a,b in zip(u,v):
  coverage=min(a['coverage'],b['coverage'])
  item={'time':a['time'],'coverage':coverage,'missing':coverage==0,'station':'NWCL1','variable':'wind_vector_hourly'}
  if coverage:
   speed=math.hypot(a['value'],b['value']); item.update(vector_u=a['value'],vector_v=b['value'],vector_speed=round(speed,6),vector_direction=round((math.degrees(math.atan2(-a['value'],-b['value']))+360)%360,3))
  result.append(item)
 base={r['time']:r for r in result if r.get('coverage')}
 for window in (3,6,12,24):
  for item in list(result):
   if not item.get('coverage'): continue
   window_items=[]
   for offset in range(window):
    stamp=(_dt(item['time'])-timedelta(hours=offset)).strftime('%Y-%m-%dT%H:%M:%SZ')
    if stamp not in base: window_items=[]; break
    window_items.append(base[stamp])
   if len(window_items) != window: continue
   mean_u=sum(x['vector_u'] for x in window_items)/window
   mean_v=sum(x['vector_v'] for x in window_items)/window
   speeds=[math.hypot(x['vector_u'],x['vector_v']) for x in window_items]
   unit_u=[x['vector_u']/speed for x,speed in zip(window_items,speeds) if speed > 1e-9]
   unit_v=[x['vector_v']/speed for x,speed in zip(window_items,speeds) if speed > 1e-9]
   resultant=math.hypot(sum(unit_u)/len(unit_u),sum(unit_v)/len(unit_v)) if unit_u else None
   result.append(dict(time=item['time'],station='NWCL1',variable='wind_vector_trailing',window_hours=window,
    coverage=sum(x['coverage'] for x in window_items),window_coverage_hours=window,
    vector_u_mean=round(mean_u,6),vector_v_mean=round(mean_v,6),vector_speed=round(math.hypot(mean_u,mean_v),6),
    vector_direction=round((math.degrees(math.atan2(-mean_u,-mean_v))+360)%360,3) if mean_u or mean_v else None,
    directional_persistence=round(resultant,6) if resultant is not None else None,
    missing=False,source='derived trailing vector mean; direction from vector components'))
 return result

def hourly_products(rows,start,end):
 configs=[('DENL1','discharge',(6,12,24)),('NWCL1','water',(3,6)),('NWCL1','residual',(3,6)),('MDLL1','stage',(3,6)),('MCHL1','stage',(3,6)),('MAUL1','stage',(3,6)),('MAUL1','elevation',(3,6))]
 products=[]
 for station,variable,windows in configs:
  hourly=aggregate_hourly(rows,station,variable,start,end)
  products.extend(hourly)
  for window in windows:
   products.extend(dict(r,variable=f'{variable}_change_{window}h') for r in trailing_change(hourly,window))
 products.extend(vector_hourly(rows,start,end))
 return products

def hourly_change(rows, station, variable):
 values={r['time']:r['value'] for r in rows if r['station']==station and r['variable']==variable and r['time'][14:19]=='00:00'}
 result={}
 from datetime import datetime,timedelta,timezone
 for t,v in values.items():
  old=(datetime.fromisoformat(t.replace('Z','+00:00'))-timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
  if old in values:result[t]=v-values[old]
 return result

def lag_correlation(source,target,lags,min_pairs=24):
 from datetime import datetime,timedelta
 result=[]
 for lag in lags:
  pairs=[]
  for t,v in source.items():
   target_time=(datetime.fromisoformat(t.replace('Z','+00:00'))+timedelta(hours=lag)).strftime('%Y-%m-%dT%H:%M:%SZ')
   if target_time in target:pairs.append((v,target[target_time]))
  if len(pairs)<min_pairs:continue
  x=[p[0] for p in pairs];y=[p[1] for p in pairs]
  mx=sum(x)/len(x);my=sum(y)/len(y)
  numerator=sum((a-mx)*(b-my) for a,b in pairs)
  denom=math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
  if denom:result.append(dict(lag_hours=lag,correlation=round(numerator/denom,3),pairs=len(pairs)))
 return max(result,key=lambda r:r['correlation']) if result else None

def peak(rows,station,variable):
 series=[r for r in rows if r['station']==station and r['variable']==variable]
 if not series:return None
 best=max(series,key=lambda r:r['value'])
 return dict(value=best['value'],time=best['time'],unit=best['unit'],datum=best['datum'])

def event_independence_group(event_id):
 if event_id in {'sally-2020','beta-2020'}: return 'sally-beta-2020'
 return None

def match_episodes(targets,predictors,max_lead_hours,max_lag_hours=0):
 """Match each predictor episode to at most one target episode.

 ``lead_hours`` is target onset minus predictor onset. Only non-negative
 leads inside the predeclared window are matches; post-target predictors are
 retained as explicit non-leads.
 """
 ordered_targets=sorted(targets,key=lambda item:item.get('onset_utc') or '9999')
 ordered_predictors=sorted(predictors,key=lambda item:item.get('onset_utc') or '9999')
 used=set(); matches=[]; unmatched_targets=[]
 for target in ordered_targets:
  target_time=target.get('onset_utc')
  target_id=target.get('episode_id')
  if not target_time:
   unmatched_targets.append({'target_episode_id':target_id,'status':'target_onset_unknown'})
   continue
  target_dt=_dt(target_time)
  candidates=[]
  for index,predictor in enumerate(ordered_predictors):
   if index in used or not predictor.get('onset_utc'): continue
   predictor_dt=_dt(predictor['onset_utc'])
   lead=(target_dt-predictor_dt).total_seconds()/3600
   if -max_lag_hours <= lead <= max_lead_hours:
    candidates.append((abs(lead),index,lead,predictor))
  if not candidates:
   unmatched_targets.append({'target_episode_id':target_id,'status':'no_precursor_in_window'})
   continue
  _,index,lead,predictor=min(candidates,key=lambda item:(item[0],item[1]))
  used.add(index)
  matches.append({'target_episode_id':target_id,'predictor_episode_id':predictor.get('episode_id'),
   'predictor_station':predictor.get('station'),'lead_hours':round(lead,3),
   'status':'detected_not_validated','window_hours':max_lead_hours,
   'note':'Detected timing association only; not verified precursor skill or causal attribution.'})
 unmatched_predictors=[]
 target_times=[_dt(item['onset_utc']) for item in targets if item.get('onset_utc')]
 for index,predictor in enumerate(ordered_predictors):
  if index in used: continue
  status='unavailable_onset'
  if predictor.get('onset_utc') and target_times:
   predictor_dt=_dt(predictor['onset_utc'])
   if any(predictor_dt > target_dt for target_dt in target_times): status='post_target'
   else: status='no_target_in_window'
  unmatched_predictors.append({'predictor_episode_id':predictor.get('episode_id'),'station':predictor.get('station'),
   'status':status})
 return {'matches':matches,'unmatched_targets':unmatched_targets,'unmatched_predictors':unmatched_predictors,
  'window_hours':max_lead_hours,'post_target_is_not_a_lead':True}

PREDICTOR_CONFIG={
 ('DENL1','discharge'):{'pathway':'river','max_lead_hours':72,'min_rise':50.0},
 ('NWCL1','residual'):{'pathway':'coastal','max_lead_hours':18,'min_rise':0.05},
 ('MDLL1','stage'):{'pathway':'coastal','max_lead_hours':18,'min_rise':0.05},
}

def _with_episode_ids(episodes,event_id,prefix):
 result=[]
 for number,episode in enumerate(episodes,1):
  item=dict(episode); item['episode_id']=f'{event_id}-{prefix}-{number:02d}'
  result.append(item)
 return result

def _wind_context(hourly,target_episodes):
 records=[]
 for target in target_episodes:
  if not target.get('onset_utc'): continue
  onset=_dt(target['onset_utc'])
  candidates=[row for row in hourly if row.get('station')=='NWCL1' and row.get('variable')=='wind_vector_trailing'
   and row.get('window_hours') in {3,6,12,24} and abs((_dt(row['time'])-onset).total_seconds()) <= 3600]
  if candidates:
   records.append({'target_episode_id':target['episode_id'],'samples':sorted(candidates,key=lambda row:row['window_hours'])[:4]})
 return records

def _series_for(hourly,station,variable):
 return [row for row in hourly if row.get('station')==station and row.get('variable')==variable]

def event_verification(data,hourly):
 event_id=data['id']
 target_series=_series_for(hourly,'MAUL1','stage')
 sensitivity_checks={}
 for sigma in (1.5,2.0,2.5):
  sensitivity=detect_episodes(target_series,'MAUL1','stage',min_rise=0.25,sigma_threshold=sigma)
  sensitivity_checks[str(sigma)]={'target_episode_count':len(sensitivity),
   'detected_onsets':[episode['onset_utc'] for episode in sensitivity if episode['status']=='detected'],
   'statuses':[episode['status'] for episode in sensitivity]}
 target_episodes=_with_episode_ids(
  detect_episodes(target_series,'MAUL1','stage',min_rise=0.25,sigma_threshold=2.0),event_id,'maul1')
 predictor_episodes={}
 for (station,variable),config in PREDICTOR_CONFIG.items():
  series=_series_for(hourly,station,variable)
  episodes=detect_episodes(series,station,variable,min_rise=config['min_rise'],sigma_threshold=2.0)
  predictor_episodes[station]=_with_episode_ids(episodes,event_id,station.lower())
 matches=[]; unmatched_targets=[]; unmatched_predictors=[]
 match_by_pathway={}
 for station,episodes in predictor_episodes.items():
  variable=next(variable for (candidate,variable) in PREDICTOR_CONFIG if candidate==station)
  config=PREDICTOR_CONFIG[(station,variable)]
  match_targets=[target for target in target_episodes if target['status'] in {'detected','already_underway'}]
  match_predictors=[episode for episode in episodes if episode['status']=='detected']
  matching=match_episodes(match_targets,match_predictors,config['max_lead_hours'])
  for item in matching['matches']: item['pathway']=config['pathway']
  for item in matching['unmatched_targets']: item.update(pathway=config['pathway'])
  for item in matching['unmatched_predictors']: item.update(pathway=config['pathway'])
  matches.extend(matching['matches']); unmatched_targets.extend(matching['unmatched_targets']); unmatched_predictors.extend(matching['unmatched_predictors'])
  match_by_pathway[station]=matching
 coverage={}
 for (station,variable) in [('MAUL1','stage'),('DENL1','discharge'),('NWCL1','residual'),('MDLL1','stage'),('MCHL1','stage')]:
  series=_series_for(hourly,station,variable)
  coverage[f'{station}:{variable}']=coverage_summary(series)
 target_match_ids={item['target_episode_id'] for item in matches}
 river_ids={item['target_episode_id'] for item in matches if item['pathway']=='river'}
 coastal_ids={item['target_episode_id'] for item in matches if item['pathway']=='coastal'}
 group=event_independence_group(event_id)
 return {'event_id':event_id,'name':data['name'],'independence_group':group,
  'independence_note':('Potentially dependent with the overlapping Sally/Beta 2020 window; do not count these windows as independent samples.' if group else 'Event-window episode records are descriptive; no independence claim is made across hydrometeorological events.'),
  'target_station':'MAUL1','target_episodes':target_episodes,'sensitivity_checks':sensitivity_checks,
  'predictor_episodes':predictor_episodes,'matches':matches,
  'unmatched_targets':unmatched_targets,'unmatched_predictors':unmatched_predictors,
  'wind_context':_wind_context(hourly,target_episodes),'coverage':coverage,
  'datum_notes':['MAUL1 stage is native 00065 gage height and is not converted to NAVD88.',
   'MAUL1 63160 direct NAVD88 elevation remains separate and is not used to infer historical threshold exceedance.',
   'MCHL1 and USACE station 85420/85420LA sources remain independent and are not combined.'],
  'summary':{'target_signal_episode_count':len([x for x in target_episodes if x['status'] in {'detected','already_underway'}]),
   'target_episodes_with_river_precursor':len(river_ids),'target_episodes_with_coastal_precursor':len(coastal_ids),
   'target_episodes_with_any_precursor':len(target_match_ids),'target_episodes_without_matched_precursor':len([x for x in target_episodes if x['status'] in {'detected','already_underway'} and x['episode_id'] not in target_match_ids]),
   'matches':len(matches),'unmatched_predictors':len(unmatched_predictors)}}

def build_verification(events):
 event_records=[]
 for path in events:
  with gzip.open(path,'rt') as stream: data=json.load(stream)
  hourly_path=ROOT/'site'/'data'/f"{data['id']}-hourly.json.gz"
  if hourly_path.exists():
   with gzip.open(hourly_path,'rt') as stream: hourly=json.load(stream)['records']
  else:
   hourly=hourly_products(data['rows'],data['start']+'T00:00:00Z',data['end']+'T23:00:00Z')
  event_records.append(event_verification(data,hourly))
 all_targets=[target for event in event_records for target in event['target_episodes']]
 all_matches=[match for event in event_records for match in event['matches']]
 all_unmatched_predictors=[item for event in event_records for item in event['unmatched_predictors']]
 leads=sorted(item['lead_hours'] for item in all_matches if item['lead_hours'] >= 0)
 cases=[]
 case_ids=['flood-2016','beta-2020','front-2024-11','front-2025-04','laura-2020','front-2024-10']
 for case_id in case_ids:
  event=next((item for item in event_records if item['event_id']==case_id),None)
  if not event: continue
  target_coverage=event['coverage']['MAUL1:stage']
  cases.append({'event_id':case_id,'name':event['name'],'independence_group':event['independence_group'],
   'target_episode_count':len(event['target_episodes']),'target_signal_episode_count':event['summary']['target_signal_episode_count'],
   'match_count':len(event['matches']),
   'coverage_quality':'available' if target_coverage['valid_hours'] else 'unavailable',
   'note':('Overlapping Sally/Beta window; results are descriptive and potentially dependent.' if case_id=='beta-2020' else
    'Independent event-window review; timing associations are not verified prediction skill.')})
 return {'schema_version':'2B.1','method':'Independent event episodes from native hourly observations; target membership is selected from MAUL1 alone.',
  'baseline':{'hours':72,'minimum_valid_change_points':48,'sigma_sensitivities':[1.5,2.0,2.5],
   'selected_sigma':2.0,'positive_changes_only':True,'minimum_hourly_coverage':1},
  'matching_windows_hours':{'DENL1':{'pathway':'river','lead_min':0,'lead_max':72},'NWCL1':{'pathway':'coastal','lead_min':0,'lead_max':18},'MDLL1':{'pathway':'coastal','lead_min':0,'lead_max':18}},
  'events':event_records,'case_studies':cases,
  'summary':{'event_count':len(event_records),'target_episode_records':len(all_targets),
   'target_signal_episode_records':len([x for x in all_targets if x['status'] in {'detected','already_underway'}]),
   'matches_detected_not_validated':len(all_matches),'target_episodes_with_river_precursor':len({x['target_episode_id'] for x in all_matches if x['pathway']=='river'}),
   'target_episodes_with_coastal_precursor':len({x['target_episode_id'] for x in all_matches if x['pathway']=='coastal'}),
   'unmatched_predictor_records':len(all_unmatched_predictors),'positive_lead_hours':leads,
   'lead_hours_summary':({'count':len(leads),'minimum':min(leads),'maximum':max(leads),'median':_median(leads)} if leads else {'count':0}),
   'note':'Counts are descriptive event-window records. Sally and Beta 2020 are potentially dependent; hourly observations are not independent samples.'},
  'limitations':['Detected first signals are not proof of useful precursor skill.',
   'No classification, forecast probability, causal attribution, or universal lag is inferred.',
   'No pre-2026 NAVD88 threshold exceedance is inferred from MAUL1 00065 gage height.',
   'Gaps, unavailable baselines, uncertain onsets, and post-target predictors remain explicit in event records.']}

def analyze(path):
 data=json.loads(gzip.decompress(path.read_bytes()));rows=data['rows'];legacy_target=hourly_change(rows,'MAUL1','stage')
 inputs=[('DENL1','discharge',range(0,73)),('NWCL1','residual',range(-24,25)),('MDLL1','stage',range(-24,25)),('MCHL1','stage',range(-24,25))]
 hourly=hourly_products(rows,data['start']+'T00:00:00Z',data['end']+'T23:00:00Z')
 hourly_path=ROOT/'site'/'data'/f"{data['id']}-hourly.json.gz"
 hourly_path.write_bytes(gzip.compress(json.dumps({'event':data['id'],'records':hourly},separators=(',',':')).encode(),mtime=0))
 target_hourly=[r for r in hourly if r['station']=='MAUL1' and r['variable']=='stage']
 onsets={}
 for station,variable in [('DENL1','discharge'),('NWCL1','residual'),('MDLL1','stage')]:
  predictor=[r for r in hourly if r['station']==station and r['variable']==variable]
  onsets[station]=[]
  for threshold in (1.5,2.0,2.5):
   onsets[station].append(compare_onsets(predictor,target_hourly,threshold=threshold,baseline_hours=72,min_baseline_points=48,persistence=3,min_coverage=1))
 return dict(event=data['id'],metrics={'den_discharge_peak':peak(rows,'DENL1','discharge'),'lake_residual_peak':peak(rows,'NWCL1','residual'),'maul_stage_peak':peak(rows,'MAUL1','stage'),'maul_direct_navd88_peak':peak(rows,'MAUL1','elevation'),'maul_24h_rise_peak':peak(rows,'MAUL1','stage_change_24h')},target='MAUL1 first difference of native gage height',hourly_file=hourly_path.name,hourly_records=len(hourly),onsets=onsets,legacy_lag_diagnostic={'description':'Pearson r of hourly first differences, exploratory only; positive lag means source change precedes MAUL1 change','results':{station:lag_correlation(hourly_change(rows,station,var),legacy_target,lags) for station,var,lags in inputs}})

def canonical_event_paths():
 return sorted(path for path in (ROOT/'site/data').glob('*.json.gz') if path.name.removesuffix('.json.gz') in EVENTS)

def main():
 paths=canonical_event_paths(); output=[]
 for file in paths:
  output.append(analyze(file))
 (ROOT/'site/data/analysis.json').write_text(json.dumps(output,indent=2))
 verification=build_verification(paths)
 (ROOT/'site/data/verification.json').write_text(json.dumps(verification,indent=2))
 print(json.dumps(output,indent=2))
if __name__=='__main__':main()
