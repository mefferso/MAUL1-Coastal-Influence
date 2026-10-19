"""Exploratory first-difference lag diagnostics; positive lag means input leads MAUL1."""
import json
import gzip
import math
import pathlib
import sys
from collections import defaultdict
ROOT=pathlib.Path(__file__).resolve().parents[1]

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
 data=json.loads(gzip.decompress(path.read_bytes()));rows=data['rows'];target=hourly_change(rows,'MAUL1','stage')
 inputs=[('DENL1','discharge',range(0,73)),('NWCL1','residual',range(-24,25)),('MDLL1','stage',range(-24,25)),('MCHL1','stage',range(-24,25))]
 return dict(event=data['id'],metrics={'den_discharge_peak':peak(rows,'DENL1','discharge'),'lake_residual_peak':peak(rows,'NWCL1','residual'),'maul_stage_peak':peak(rows,'MAUL1','stage'),'maul_direct_navd88_peak':peak(rows,'MAUL1','elevation'),'maul_24h_rise_peak':peak(rows,'MAUL1','stage_change_24h')},target='MAUL1 first difference of native gage height',diagnostic='Pearson r of hourly first differences, exploratory only; positive lag means source change precedes MAUL1 change',results={station:lag_correlation(hourly_change(rows,station,var),target,lags) for station,var,lags in inputs})

def main():
 output=[]
 for file in sorted((ROOT/'site/data').glob('*.json.gz')):
  output.append(analyze(file))
 (ROOT/'site/data/analysis.json').write_text(json.dumps(output,indent=2))
 print(json.dumps(output,indent=2))
if __name__=='__main__':main()
