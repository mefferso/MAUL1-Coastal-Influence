"""Exploratory first-difference lag diagnostics; positive lag means input leads MAUL1."""
import json
import gzip
import math
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
 output=[]
 for file in canonical_event_paths():
  output.append(analyze(file))
 (ROOT/'site/data/analysis.json').write_text(json.dumps(output,indent=2))
 print(json.dumps(output,indent=2))
if __name__=='__main__':main()
