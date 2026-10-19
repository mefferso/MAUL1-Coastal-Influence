"""Exploratory first-difference lag diagnostics; positive lag means input leads MAUL1."""
import json
import gzip
import math
import pathlib
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict
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
  # Median is robust for levels; discharge uses a within-hour mean.
  value=(sum(values)/len(values) if variable == 'discharge' and values else _median(values))
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

def detect_onset(series,threshold=2.0,baseline_points=6,persistence=2):
 """Detect a persistent trailing deviation using data available at each row."""
 valid=[r for r in series if r.get('coverage',1) and r.get('value') is not None]
 for i in range(baseline_points + persistence - 1,len(valid)):
  window=valid[i-baseline_points:i]
  baseline=[r['value'] for r in window]
  scale=robust_sigma(baseline)
  if scale == 0: scale=1e-9
  center=_median(baseline)
  signal=all(abs(r['value']-center) >= threshold*scale for r in valid[i-persistence+1:i+1])
  if signal:
   return {'onset_time':valid[i]['time'],'threshold_sigma':threshold,'baseline_points':baseline_points,
    'persistence':persistence,'baseline_median':center,'robust_sigma':scale,'status':'reliable'}
 return {'onset_time':None,'threshold_sigma':threshold,'baseline_points':baseline_points,'persistence':persistence,'status':'unavailable'}

def vector_hourly(rows,start,end):
 u=aggregate_hourly(rows,'NWCL1','wind_u',start,end); v=aggregate_hourly(rows,'NWCL1','wind_v',start,end)
 result=[]
 for a,b in zip(u,v):
  coverage=min(a['coverage'],b['coverage'])
  item={'time':a['time'],'coverage':coverage,'missing':coverage==0,'station':'NWCL1','variable':'wind_vector'}
  if coverage:
   speed=math.hypot(a['value'],b['value']); item.update(vector_u=a['value'],vector_v=b['value'],vector_speed=round(speed,6),vector_direction=round((math.degrees(math.atan2(-a['value'],-b['value']))+360)%360,3))
  result.append(item)
 base={r['time']:r for r in result if r.get('coverage')}
 for window in (3,6,12,24):
  for item in list(result):
   if not item.get('coverage'): continue
   old=base.get((_dt(item['time'])-timedelta(hours=window)).strftime('%Y-%m-%dT%H:%M:%SZ'))
   if old:
    result.append(dict(item,variable='wind_vector_trailing',window_hours=window,
     vector_u_change=round(item['vector_u']-old['vector_u'],6),vector_v_change=round(item['vector_v']-old['vector_v'],6),
     vector_speed_change=round(item['vector_speed']-old['vector_speed'],6)))
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
 target_hourly=[r for r in hourly if r['station']=='MAUL1' and r['variable']=='stage' and r.get('value') is not None]
 onsets={}
 for station,variable in [('DENL1','discharge'),('NWCL1','residual'),('MDLL1','stage')]:
  predictor=[r for r in hourly if r['station']==station and r['variable']==variable]
  onsets[station]=[]
  for threshold in (1.5,2.0,2.5):
   found=detect_onset(predictor,threshold=threshold)
   target_onset=detect_onset(target_hourly,threshold=threshold)
   lead=(_dt(target_onset['onset_time'])-_dt(found['onset_time'])).total_seconds()/3600 if found['onset_time'] and target_onset['onset_time'] else None
   onsets[station].append(dict(predictor_onset_utc=found['onset_time'],maul1_onset_utc=target_onset['onset_time'],lead_hours=lead,threshold_sigma=threshold,predictor_coverage=sum(r.get('coverage',0) for r in predictor),status='reliable' if lead is not None else 'unavailable'))
 return dict(event=data['id'],metrics={'den_discharge_peak':peak(rows,'DENL1','discharge'),'lake_residual_peak':peak(rows,'NWCL1','residual'),'maul_stage_peak':peak(rows,'MAUL1','stage'),'maul_direct_navd88_peak':peak(rows,'MAUL1','elevation'),'maul_24h_rise_peak':peak(rows,'MAUL1','stage_change_24h')},target='MAUL1 first difference of native gage height',hourly_file=hourly_path.name,hourly_records=len(hourly),onsets=onsets,legacy_lag_diagnostic={'description':'Pearson r of hourly first differences, exploratory only; positive lag means source change precedes MAUL1 change','results':{station:lag_correlation(hourly_change(rows,station,var),legacy_target,lags) for station,var,lags in inputs}})

def main():
 output=[]
 for file in sorted((ROOT/'site/data').glob('*.json.gz')):
  output.append(analyze(file))
 (ROOT/'site/data/analysis.json').write_text(json.dumps(output,indent=2))
 print(json.dumps(output,indent=2))
if __name__=='__main__':main()
