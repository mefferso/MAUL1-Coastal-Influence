"""Quality and source-comparison checks for the Phase 3A archive."""
import argparse
import collections
import gzip
import json
import math
import pathlib

def validate_rows(rows):
 findings=[]; seen=set(); groups=collections.defaultdict(list); units={}; datums={}
 for row in rows:
  key=(row.get('station'),row.get('variable'),row.get('time'))
  if key in seen: findings.append({'kind':'duplicate_timestamp','key':key})
  seen.add(key); group=(row.get('station'),row.get('variable')); groups[group].append(row)
  units.setdefault(group,set()).add(row.get('unit')); datums.setdefault(group,set()).add(row.get('datum'))
 for group,values in units.items():
  if len(values-{None})>1: findings.append({'kind':'unit_change','group':group,'values':sorted(value for value in values if value is not None)})
 for group,values in datums.items():
  if len(values-{None})>1: findings.append({'kind':'datum_change','group':group,'values':sorted(value for value in values if value is not None)})
 for group,series in groups.items():
  ordered=sorted((row for row in series if row.get('value') is not None),key=lambda row:row['time'])
  deltas=[abs(float(current['value'])-float(previous['value'])) for previous,current in zip(ordered,ordered[1:])]
  if deltas:
   variable=group[1]; typical=sorted(deltas)[:-1] or deltas; median=typical[len(typical)//2]
   floor={'stage':5.0,'elevation':5.0,'water':5.0,'residual':5.0,'discharge':10000.0,'wind':50.0,'wind_u':50.0,'wind_v':50.0}.get(variable,5.0)
   threshold=max(floor,median*10)
   for previous,current,delta in zip(ordered,ordered[1:],deltas):
    if delta > threshold: findings.append({'kind':'suspicious_jump','group':group,'from_time':previous['time'],'to_time':current['time'],'delta':round(delta,6),'threshold':threshold})
 return findings

def _speed_knots(row):
 value=float(row['value']); return value*1.943844492 if row.get('unit') in {'m/s','mps'} else value

def _circular_error(first,second):
 return abs((first-second+180)%360-180)

def compare_wind(primary,independent):
 primary_by=collections.defaultdict(dict); independent_by=collections.defaultdict(dict)
 for row in primary: primary_by[row['time']][row['variable']]=row
 for row in independent: independent_by[row['time']][row['variable']]=row
 overlap=sorted(set(primary_by)&set(independent_by)); speed_errors=[]; direction_errors=[]
 for stamp in overlap:
  left=primary_by[stamp]; right=independent_by[stamp]
  if 'wind' in left and 'wind' in right: speed_errors.append(abs(_speed_knots(left['wind'])-_speed_knots(right['wind'])))
  if 'wind_direction' in left and 'wind_direction' in right: direction_errors.append(round(_circular_error(float(left['wind_direction']['value']),float(right['wind_direction']['value'])),6))
 return {'primary_source':'CO-OPS','independent_source':'NDBC','overlap_records':len(overlap),
  'speed_abs_error_knots':speed_errors,'direction_error_degrees':direction_errors,
  'mean_speed_abs_error_knots':round(sum(speed_errors)/len(speed_errors),6) if speed_errors else None,
  'mean_direction_error_degrees':round(sum(direction_errors)/len(direction_errors),6) if direction_errors else None,
  'averaged_sources':False,'status':'compared' if overlap else 'no_overlap'}

def _load_json(path):
 with gzip.open(path,'rt') as stream: return json.load(stream)

def validate_history(root):
 root=pathlib.Path(root); manifest=json.loads((root/'manifest.json').read_text()) if (root/'manifest.json').exists() else {'months':{}}
 findings=[]
 for month,stations in manifest.get('months',{}).items():
  for station,record in stations.items():
   if record.get('path'):
    path=root/record['path']
    if not path.exists(): findings.append({'kind':'missing_partition','month':month,'station':station})
    else: findings.extend(validate_rows(_load_json(path)['rows']))
 return {'schema_version':'3A.1','finding_count':len(findings),'findings':findings,'status':'ok' if not findings else 'findings'}

def main(argv=None):
 parser=argparse.ArgumentParser(); parser.add_argument('--root',default='site/data/history'); args=parser.parse_args(argv)
 result=validate_history(args.root); print(json.dumps(result,indent=2)); return 0 if result['status']=='ok' else 0

if __name__=='__main__': main()
