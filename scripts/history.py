"""Contracts and helpers for the Phase 3A monthly historical archive."""
import argparse
import datetime as dt
import gzip
import json
import pathlib
import re
import math
from collections import defaultdict

SCHEMA_VERSION='3A.1'
MONTH_PATTERN=re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')

def _month_start(month):
 if not MONTH_PATTERN.fullmatch(month): raise ValueError(f'Invalid UTC month: {month}')
 year,number=(int(part) for part in month.split('-'))
 return dt.datetime(year,number,1,tzinfo=dt.timezone.utc)

def _month_end(month):
 start=_month_start(month)
 return (start.replace(year=start.year+1,month=1) if start.month==12 else start.replace(month=start.month+1))

def month_range(start_month,end_month):
 start=_month_start(start_month); end=_month_start(end_month)
 if end < start: raise ValueError('end_month precedes start_month')
 months=[]; cursor=start
 while cursor <= end:
  months.append(cursor.strftime('%Y-%m'))
  cursor=_month_end(cursor.strftime('%Y-%m'))
 return months

def partition_path(root,station,month):
 _month_start(month)
 if not station or '/' in station or '\\' in station: raise ValueError('Invalid station identifier')
 return pathlib.Path(root)/'raw'/station/f'{month}.json.gz'

def canonical_month(start_month,end_month):
 months=month_range(start_month,end_month)
 return {'schema_version':SCHEMA_VERSION,'months':months,
  'month_start':f'{months[0]}-01T00:00:00Z',
  'month_end_exclusive':_month_end(months[-1]).strftime('%Y-%m-%dT%H:%M:%SZ')}

def _validate_payload(payload):
 required={'schema_version','station','month_start','month_end_exclusive','rows'}
 missing=required-set(payload)
 if missing: raise ValueError(f'Partition missing fields: {sorted(missing)}')
 if payload['schema_version'] != SCHEMA_VERSION: raise ValueError('Unsupported partition schema')
 start=dt.datetime.fromisoformat(payload['month_start'].replace('Z','+00:00')).astimezone(dt.timezone.utc)
 end=dt.datetime.fromisoformat(payload['month_end_exclusive'].replace('Z','+00:00')).astimezone(dt.timezone.utc)
 if end <= start or start.day != 1 or start.hour != 0 or start.minute != 0: raise ValueError('Invalid half-open month bounds')
 seen=set()
 for row in payload['rows']:
  if not isinstance(row,dict) or 'time' not in row or 'variable' not in row: raise ValueError('Invalid observation row')
  stamp=dt.datetime.fromisoformat(row['time'].replace('Z','+00:00')).astimezone(dt.timezone.utc)
  if not start <= stamp < end: raise ValueError(f'Observation outside partition: {row["time"]}')
  key=(row.get('station',payload['station']),row['variable'],row['time'])
  if key in seen: raise ValueError(f'Duplicate observation key: {key}')
  seen.add(key)

def _encoded(payload):
 _validate_payload(payload)
 return gzip.compress(json.dumps(payload,sort_keys=True,separators=(',',':')).encode(),mtime=0)

def write_partition(path,payload,overwrite=False):
 path=pathlib.Path(path); encoded=_encoded(payload)
 if path.exists() and not overwrite: return False
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_bytes(encoded)
 return True

def load_partition(path):
 with gzip.open(path,'rt',encoding='utf-8') as stream: payload=json.load(stream)
 _validate_payload(payload)
 return payload

def manifest_path(root):
 return pathlib.Path(root)/'manifest.json'

def _read_manifest(root):
 path=manifest_path(root)
 if not path.exists(): return {'schema_version':SCHEMA_VERSION,'months':{}}
 return json.loads(path.read_text())

def _write_manifest(root,manifest):
 path=manifest_path(root); path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')

def acquire_month(month,stations,root=None,refresh=False,fetchers=None):
 """Fetch one month per station, writing only successful non-empty partitions."""
 import history_sources
 root=pathlib.Path(root or pathlib.Path(__file__).resolve().parents[1]/'site/data/history')
 fetchers=fetchers or history_sources.DEFAULT_FETCHERS
 manifest=_read_manifest(root); month_record=manifest.setdefault('months',{}).setdefault(month,{})
 results={}
 for station in stations:
  path=partition_path(root,station,month)
  existing_record=month_record.get(station,{})
  if path.exists() and not refresh and existing_record.get('status')!='partially_retrieved':
   payload=load_partition(path)
   result={'status':'skipped','row_count':len(payload['rows']),'path':str(path.relative_to(root))}
   month_record[station]=result; results[station]=result; continue
  fetcher=fetchers[station]
  result=fetcher(month)
  rows=result.get('rows') or []
  status=result.get('status')
  if status=='retrieved' and not rows: status='queried_unavailable'
  record={'status':status,'row_count':len(rows),'request':result.get('request'),
   'source':result.get('source'),'error':result.get('error'),'observed_start':result.get('observed_start'),'observed_end':result.get('observed_end')}
  if result.get('components'): record['components']=result['components']
  if rows and status in {'retrieved','partially_retrieved'}:
   payload={'schema_version':SCHEMA_VERSION,'station':station,'month_start':f'{month}-01T00:00:00Z',
    'month_end_exclusive':_month_end(month).strftime('%Y-%m-%dT%H:%M:%SZ'),'rows':result['rows'],'retrieval':record}
   write_partition(path,payload,overwrite=True)
   record['path']=str(path.relative_to(root))
  month_record[station]=record; results[station]=record
 _write_manifest(root,manifest)
 return {'month':month,'sources':results}

def hourly_path(root,month):
 _month_start(month)
 return pathlib.Path(root)/'hourly'/f'{month}.json.gz'

def _median(values):
 values=sorted(values)
 if not values:return None
 middle=len(values)//2
 return values[middle] if len(values)%2 else (values[middle-1]+values[middle])/2

def _hourly_value(variable,values):
 return sum(values)/len(values) if variable in {'discharge','wind','wind_u','wind_v','gust'} else _median(values)

def hourly_buckets(rows):
 buckets=defaultdict(list)
 for row in rows:
  if row.get('station') and row.get('variable') and row.get('time'):
   buckets[(row['station'],row['variable'],_month_stamp(row['time']).strftime('%Y-%m-%dT%H:00:00Z'))].append(row)
 return buckets

def _aggregate_hour(rows,station,variable,hour,buckets=None,templates=None):
 key=(station,variable,hour.strftime('%Y-%m-%dT%H:00:00Z'))
 observations=(buckets.get(key,[]) if buckets is not None else [row for row in rows if row.get('station')==station and row.get('variable')==variable and _month_stamp(row['time'])==hour])
 values=[float(row['value']) for row in observations if row.get('value') is not None]
 template=observations[0] if observations else (templates.get((station,variable),{}) if templates is not None else next((row for row in rows if row.get('station')==station and row.get('variable')==variable),{}))
 result={'time':hour.strftime('%Y-%m-%dT%H:00:00Z'),'station':station,'variable':variable,'value':round(_hourly_value(variable,values),6) if values else None,
  'coverage':len(values),'missing':not bool(values),'unit':template.get('unit'),'datum':template.get('datum'),'source':'derived monthly hourly aggregation'}
 return result

def _month_stamp(value):
 return dt.datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(dt.timezone.utc).replace(minute=0,second=0,microsecond=0)

def hourly_month(raw_partitions,month):
 """Derive a complete UTC month, using up to 24h of preceding context."""
 start=_month_start(month); end=_month_end(month); context_start=start-dt.timedelta(hours=24)
 rows=[row for partition in raw_partitions for row in partition.get('rows',[])]
 rows=[row for row in rows if context_start <= dt.datetime.fromisoformat(row['time'].replace('Z','+00:00')).astimezone(dt.timezone.utc) < end and not '_change_' in row.get('variable','')]
 buckets=hourly_buckets(rows); templates={(row.get('station'),row.get('variable')):row for row in rows}
 groups=sorted({(row.get('station'),row.get('variable')) for row in rows if row.get('station') and row.get('variable')})
 hours=[]; cursor=start
 while cursor < end: hours.append(cursor); cursor += dt.timedelta(hours=1)
 records=[]
 for station,variable in groups:
  if variable=='wind_direction': continue
  hourly=[_aggregate_hour(rows,station,variable,hour,buckets,templates) for hour in hours]
  records.extend(hourly)
  windows=(6,12,24) if variable=='discharge' else ((1,3,6,12,24) if variable in {'stage','elevation','water','residual'} else ())
  lookup={_month_stamp(row['time']):row for row in [_aggregate_hour(rows,station,variable,hour,buckets,templates) for hour in [cursor for cursor in [start-dt.timedelta(hours=offset) for offset in range(24,0,-1)] if cursor < start]+hours]}
  for window in windows:
   for row in hourly:
    stamp=_month_stamp(row['time']); old=lookup.get(stamp-dt.timedelta(hours=window))
    if row['value'] is None or not old or old['value'] is None or row.get('datum') != old.get('datum'): continue
    records.append(dict(row,variable=f'{variable}_change_{window}h',value=round(row['value']-old['value'],6),source='derived exact trailing UTC difference'))
 wind_u=[row for row in records if row['station']=='NWCL1' and row['variable']=='wind_u']
 wind_v=[row for row in records if row['station']=='NWCL1' and row['variable']=='wind_v']
 u_lookup={_month_stamp(row['time']):row for row in wind_u}; v_lookup={_month_stamp(row['time']):row for row in wind_v}
 for hour in hours:
  u=u_lookup.get(hour); v=v_lookup.get(hour)
  if not u or not v or u['value'] is None or v['value'] is None: continue
  records.append({'time':hour.strftime('%Y-%m-%dT%H:00:00Z'),'station':'NWCL1','variable':'wind_direction',
   'value':round((math.degrees(math.atan2(-u['value'],-v['value']))+360)%360,3),'coverage':min(u['coverage'],v['coverage']),
   'missing':False,'unit':'degrees from','datum':'none','source':'derived direction from hourly wind components'})
 for window in (3,6,12,24):
  for hour in hours:
   samples=[]
   for offset in range(window):
    u=u_lookup.get(hour-dt.timedelta(hours=offset)); v=v_lookup.get(hour-dt.timedelta(hours=offset))
    if not u or not v or u['value'] is None or v['value'] is None: samples=[]; break
    samples.append((u,v))
   if len(samples)!=window: continue
   mean_u=sum(pair[0]['value'] for pair in samples)/window; mean_v=sum(pair[1]['value'] for pair in samples)/window
   unit=[(pair[0]['value']/math.hypot(pair[0]['value'],pair[1]['value']),pair[1]['value']/math.hypot(pair[0]['value'],pair[1]['value'])) for pair in samples if math.hypot(pair[0]['value'],pair[1]['value'])>1e-9]
   persistence=math.hypot(sum(pair[0] for pair in unit)/len(unit),sum(pair[1] for pair in unit)/len(unit)) if unit else None
   records.append({'time':hour.strftime('%Y-%m-%dT%H:00:00Z'),'station':'NWCL1','variable':'wind_vector_trailing','window_hours':window,
    'value':round(math.hypot(mean_u,mean_v),6),'vector_u_mean':round(mean_u,6),'vector_v_mean':round(mean_v,6),
    'vector_direction':round((math.degrees(math.atan2(-mean_u,-mean_v))+360)%360,3),'directional_persistence':round(persistence,6) if persistence is not None else None,
    'coverage':window,'missing':False,'unit':'knots','datum':'none','source':'derived trailing vector mean'})
 records.sort(key=lambda row:(row['time'],row.get('station',''),row.get('variable',''),row.get('window_hours',0)))
 return {'schema_version':SCHEMA_VERSION,'month_start':f'{month}-01T00:00:00Z','month_end_exclusive':_month_end(month).strftime('%Y-%m-%dT%H:%M:%SZ'),'records':records}

def coverage_report(manifest,hourly):
 monthly=defaultdict(lambda:defaultdict(lambda:defaultdict(lambda:{'valid_hours':0,'reported_hours':0})))
 totals=defaultdict(lambda:{'valid_hours':0,'reported_hours':0,'expected_hours':0,'missing_hours':0,'not_yet_observed_hours':0})
 for row in hourly.get('records',[]):
  if not row.get('time') or not row.get('station') or not row.get('variable'): continue
  month=_month_stamp(row['time']).strftime('%Y-%m')
  station=row['station']; variable=row['variable']
  bucket=monthly[month][station][variable]
  bucket['reported_hours']+=1
  totals[f'{station}:{variable}']['reported_hours']+=1
  if row.get('value') is not None:
   bucket['valid_hours']+=1
   totals[f'{station}:{variable}']['valid_hours']+=1
 months=[]
 stations=defaultdict(lambda:{'valid_months':0,'retrieval_errors':0,'queried_unavailable':0,'not_queried':0,'partial_months':0,'rows':0})
 current_month=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m')
 now=dt.datetime.now(dt.timezone.utc)
 for month,source_map in sorted(manifest.get('months',{}).items()):
  expected_hours=int((_month_end(month)-_month_start(month)).total_seconds()//3600)
  hourly_coverage={}
  for station,variables in sorted(monthly.get(month,{}).items()):
   hourly_coverage[station]={}
   for variable,counts in sorted(variables.items()):
    valid=counts['valid_hours']
    reporting_hours=expected_hours
    if month==current_month and variable!='prediction':
     reporting_hours=max(0,min(expected_hours,int((now-_month_start(month)).total_seconds()//3600)))
    missing=max(0,reporting_hours-valid)
    not_yet=max(0,expected_hours-reporting_hours)
    entry={'valid_hours':valid,'expected_hours':expected_hours,'reporting_hours':reporting_hours,
     'missing_hours':missing,'not_yet_observed_hours':not_yet,'reported_hours':counts['reported_hours']}
    hourly_coverage[station][variable]=entry
    total=totals[f'{station}:{variable}']
    total['expected_hours']+=expected_hours
    total['missing_hours']+=missing
    total['not_yet_observed_hours']+=not_yet
  months.append({'month':month,'expected_hours':expected_hours,'sources':source_map,'hourly_coverage':hourly_coverage})
  for station,record in source_map.items():
   status=record.get('status')
   if status in {'retrieved','skipped','partially_retrieved'}: stations[station]['valid_months']+=1
   if status=='partially_retrieved': stations[station]['partial_months']+=1
   if status=='retrieval_error': stations[station]['retrieval_errors']+=1
   if status=='queried_unavailable': stations[station]['queried_unavailable']+=1
   if status=='not_queried': stations[station]['not_queried']+=1
   stations[station]['rows']+=record.get('row_count',0) or 0
 return {'schema_version':SCHEMA_VERSION,
  'coverage_basis':'Full UTC calendar months; for the current month, missing_hours stops at the current UTC hour and later hours are reported as not_yet_observed_hours. The prediction variable retains its full forecast horizon.',
  'months':months,'stations':dict(sorted(stations.items())),
  'hourly_valid_records':dict(sorted((key,value['valid_hours']) for key,value in totals.items())),
  'hourly_variable_coverage':dict(sorted(totals.items()))}

def _write_json(path,payload):
 path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')

def _iter_hourly_records(root,months):
 for month in months:
  path=hourly_path(root,month)
  if not path.exists(): continue
  with gzip.open(path,'rt',encoding='utf-8') as stream:
   yield from json.load(stream).get('records',[])

def rebuild_hourly_reports(root=None):
 root=pathlib.Path(root or pathlib.Path(__file__).resolve().parents[1]/'site/data/history')
 manifest=_read_manifest(root); months=sorted(manifest.get('months',{}))
 primary=[]; independent=[]; hourly_record_count=0
 for month in months:
  partitions=[]; seen_paths=set()
  context_month=(_month_start(month)-dt.timedelta(days=1)).strftime('%Y-%m')
  for source_month in (context_month,month):
   for station,record in manifest.get('months',{}).get(source_month,{}).items():
    relative=record.get('path')
    if relative and relative not in seen_paths and (root/relative).exists():
     partitions.append(load_partition(root/relative)); seen_paths.add(relative)
  hourly=hourly_month(partitions,month)
  path=hourly_path(root,month); path.parent.mkdir(parents=True,exist_ok=True)
  path.write_bytes(gzip.compress(json.dumps(hourly,sort_keys=True,separators=(',',':')).encode(),mtime=0))
  hourly_record_count+=len(hourly['records'])
  primary.extend(row for row in hourly['records'] if row.get('station')=='NWCL1' and row.get('variable') in {'wind','wind_direction'} and row.get('value') is not None)
  independent.extend(row for row in hourly['records'] if row.get('station')=='NWCL1-NDBC' and row.get('variable') in {'wind','wind_direction'} and row.get('value') is not None)
 coverage=coverage_report(manifest,{'records':_iter_hourly_records(root,months)})
 _write_json(root/'coverage.json',coverage)
 try:
  import history_validate
  wind=history_validate.compare_wind(primary,independent)
 except ImportError:
  wind={'status':'not_available','overlap_records':0,'averaged_sources':False}
 _write_json(root/'wind-comparison.json',wind)
 try:
  quality=history_validate.validate_history(root)
 except ImportError:
  quality={'schema_version':SCHEMA_VERSION,'finding_count':0,'findings':[],'status':'not_available'}
 _write_json(root/'quality.json',quality)
 return {'months':len(months),'hourly_records':hourly_record_count,'coverage':coverage,'wind_comparison':wind,'quality':quality}

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--start-month',required=True); parser.add_argument('--end-month',required=True)
 parser.add_argument('--refresh',action='store_true'); parser.add_argument('--station'); parser.add_argument('--root',default=None)
 parser.add_argument('--rebuild',action='store_true',help='rebuild hourly and quality reports after acquisition')
 args=parser.parse_args(argv)
 stations=[args.station] if args.station else list(DEFAULT_STATIONS)
 output=[]
 for month in month_range(args.start_month,args.end_month):
  result=acquire_month(month,stations,root=args.root,refresh=args.refresh)
  output.append(result); print(json.dumps(result,sort_keys=True))
 if args.rebuild:
  print(json.dumps(rebuild_hourly_reports(args.root),sort_keys=True))
 return output

DEFAULT_STATIONS=('DENL1','NWCL1','NWCL1-NDBC','MDLL1','MCHL1','USACE-85420','USACE-85420LA','MAUL1')

if __name__=='__main__': main()
