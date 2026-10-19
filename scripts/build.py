"""Reproducible event archive. Run python scripts/build.py [event-id]."""
import csv
import gzip
import datetime as dt
import io
import json
import math
import pathlib
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'site' / 'data'
EVENTS = {
 'flood-2016': ('August 2016 Louisiana flood', '2016-08-09', '2016-08-22'),
 'laura-2020': ('Hurricane Laura', '2020-08-24', '2020-09-02'),
 'sally-2020': ('Hurricane Sally', '2020-09-12', '2020-09-21'),
 'beta-2020': ('Tropical Storm Beta', '2020-09-18', '2020-09-28'),
 'delta-2020': ('Hurricane Delta', '2020-10-05', '2020-10-15'),
 'zeta-2020': ('Hurricane Zeta', '2020-10-25', '2020-11-04'),
 'claudette-2021': ('Tropical Storm Claudette', '2021-06-15', '2021-06-25'),
 'front-2024-11': ('November 2024 coastal-advisory window', '2024-11-14', '2024-11-24'),
 'front-2025-04': ('April 2025 southeast-wind window', '2025-04-01', '2025-04-11'),
 'front-2024-10': ('October 2024 north-wind control window', '2024-10-11', '2024-10-21'),
 'recent-2026': ('October 2026 direct-NAVD88 observation window', '2026-10-07', '2026-10-17'),
}
USGS = {'DENL1': ('07378500', ['00060', '00065']), 'MAUL1': ('07380215', ['00065', '63160']), 'MDLL1': ('301200090072400', ['00065'])}
PARAMS = {'00060': ('discharge', 'cfs', 'native'), '00065': ('stage', 'ft', 'gage height'), '63160': ('elevation', 'ft', 'NAVD88')}
RETRIEVAL_STATUSES = ('retrieved', 'queried_unavailable', 'not_queried', 'retrieval_error')
MCHL1_SOURCES = [
 {'id':'hads-mchl1','name':'NWS HADS MCHL1 / CE678A12','interface':'https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py','station':'MCHL1','datum':'HADS native gage height (unverified)'},
 {'id':'usace-85420','name':'USACE Pass Manchac near Pontchatoula','interface':'https://rivergages.mvr.usace.army.mil/WaterControl/stationinfo2.cfm?sid=85420','station':'USACE-85420','datum':'USACE station datum (unresolved)'},
 {'id':'usace-85420la','name':'USACE Pass Manchac','interface':'https://rivergages.mvr.usace.army.mil/WaterControl/stationinfo2.cfm?sid=85420LA','station':'USACE-85420LA','datum':'USACE station datum (unresolved)'},
]

def get_json(base, params):
 url = base + '?' + urllib.parse.urlencode(params)
 for attempt in range(4):
  try:
   with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'MAUL1-research/1.0 (public research)'}), timeout=40) as response:
    return json.load(response), url
  except (OSError, ValueError):
   if attempt == 3: raise
   time.sleep(2 ** attempt)

def iso(s):
 return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def parse_usgs(payload, station):
 result = []
 for series in payload['value']['timeSeries']:
  if series['sourceInfo']['siteCode'][0]['value'] != USGS[station][0]: raise ValueError('Unexpected USGS site')
  code = series['variable']['variableCode'][0]['value']
  if code not in USGS[station][1]: raise ValueError('Unexpected USGS parameter')
  variable, unit, datum = PARAMS[code]
  for block in series.get('values', []):
   for v in block.get('value', []):
    try: value = float(v['value'])
    except (ValueError, TypeError): continue
    if value <= -9999: continue
    result.append(dict(time=iso(v['dateTime']), value=value, station=station, variable=variable, unit=unit, datum=datum, quality=v.get('qualifiers', []), source='USGS NWIS IV'))
 return result

def parse_coops(payload, variable, datum):
 if 'error' in payload: raise ValueError(payload['error'])
 result = []
 for row in payload.get('data', payload.get('predictions', [])):
  try: value=float(row['v'])
  except (KeyError, ValueError, TypeError): continue
  result.append(dict(time=iso(row['t']+'+00:00'), value=value, station='NWCL1', variable=variable, unit='ft', datum=datum, quality=row.get('f', ''), source='NOAA CO-OPS 8761927'))
 return result

def parse_wind(payload):
 if 'error' in payload: raise ValueError(payload['error'])
 result=[]
 for row in payload.get('data', []):
  try:
   speed=float(row['s']); degrees=float(row['d'])
   if speed<0 or not (0<=degrees<=360): continue
  except (KeyError, ValueError, TypeError): continue
  stamp=iso(row['t']+'+00:00'); angle=math.radians(degrees)
  # Meteorological FROM direction; positive u points east, positive v north.
  values={'wind':speed,'wind_u':-speed*math.sin(angle),'wind_v':-speed*math.cos(angle),'wind_direction':degrees}
  try: values['gust']=float(row['g'])
  except (KeyError, ValueError, TypeError): pass
  for variable,value in values.items():
   result.append(dict(time=stamp,value=value,station='NWCL1',variable=variable,unit='degrees from' if variable=='wind_direction' else 'knots',datum='none',quality=row.get('f',''),source='NOAA CO-OPS 8761927'))
 return result

def residuals(rows):
 predictions={r['time']:r['value'] for r in rows if r['station']=='NWCL1' and r['variable']=='prediction' and r['datum']=='MLLW'}
 return [dict(r,variable='residual',value=round(r['value']-predictions[r['time']],4),datum='difference (MLLW)') for r in rows if r['station']=='NWCL1' and r['variable']=='water' and r['datum']=='MLLW' and r['time'] in predictions]

def parse_hads(payload):
 if not payload.startswith('station,utc_valid,'): raise ValueError('HADS CSV missing or empty')
 parsed=list(csv.DictReader(io.StringIO(payload)))
 if not parsed or 'HGIRGZZ' not in parsed[0]: raise ValueError('HADS stage missing')
 rows=[]
 for item in parsed:
  if item['station']!='MCHL1': raise ValueError('Unexpected HADS station')
  try: value=float(item['HGIRGZZ'])
  except (ValueError, TypeError): continue
  rows.append(dict(time=iso(item['utc_valid']+'+00:00'),value=value,station='MCHL1',variable='stage',unit='ft',datum='HADS native gage height (unverified)',quality='unverified',source='Iowa Environmental Mesonet archive of NWS HADS SHEF'))
 return rows

def parse_usace_row(item, source_id):
 """Parse an explicitly named USACE record without treating it as MCHL1."""
 try: value=float(item['value'])
 except (KeyError, ValueError, TypeError): return []
 return [dict(time=iso(item['time']), value=value, station='USACE-'+source_id,
  variable='stage', unit='ft', datum='USACE station datum (unresolved)',
  original_datum='USACE station datum (unresolved)', quality='unverified',
  source=f'USACE RiverGages {source_id}')]

def navd88_threshold_eligible(row):
 return row.get('station') == 'MAUL1' and row.get('variable') == 'elevation' and row.get('datum') == 'NAVD88'

def get_hads(start,end):
 url='https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py?'+urllib.parse.urlencode(dict(stations='MCHL1',sts=start+'T00:00Z',ets=end+'T23:59Z',what='txt'))
 for attempt in range(3):
  try:
   with urllib.request.urlopen(url,timeout=50) as response:return response.read().decode('utf-8'),url
  except OSError:
   if attempt==2: raise
   time.sleep(2**attempt)

def mchl1_provenance(start, end, hads_status, hads_error=None):
 """Return per-source status; USACE sources remain separate and unspliced."""
 statuses=[]
 statuses.append(dict(source='hads-mchl1', period_start=start, period_end=end, status=hads_status,
  error=hads_error, interface=MCHL1_SOURCES[0]['interface']))
 for source in MCHL1_SOURCES[1:]:
  statuses.append(dict(source=source['id'], period_start=start, period_end=end,
   status='not_queried', error='Station metadata identified; historical observations require datum/instrument review before ingestion.',
   interface=source['interface']))
 return statuses

def dedupe(rows):
 selected = {}
 for row in rows: selected[(row['station'], row['variable'], row['time'])] = row
 return sorted(selected.values(), key=lambda x:(x['time'],x['station'],x['variable']))

def changes(rows):
 groups=defaultdict(list)
 for r in rows:
  if (r['station'],r['variable']) in {('DENL1','discharge'),('MAUL1','stage'),('MAUL1','elevation')}:
   groups[(r['station'],r['variable'])].append(r)
 result=[]
 for (station,variable),series in groups.items():
  lookup={r['time']:r for r in series}
  hours=(3,6,12,24) if station=='DENL1' else (1,3,6,12,24)
  for r in series:
   stamp=dt.datetime.fromisoformat(r['time'].replace('Z','+00:00'))
   for h in hours:
    previous=lookup.get((stamp-dt.timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ'))
    if previous and r['datum']==previous['datum']:
     result.append(dict(r,variable=f'{variable}_change_{h}h',value=round(r['value']-previous['value'],4),source=r['source']+' (derived exact UTC difference)'))
 return result

def coverage(rows):
 groups=defaultdict(list)
 for r in rows:groups[(r['station'],r['variable'])].append(r)
 result=[]
 for (station,variable),records in sorted(groups.items()):
  stamps=sorted(dt.datetime.fromisoformat(r['time'].replace('Z','+00:00')) for r in records)
  gaps=[int((b-a).total_seconds()/60) for a,b in zip(stamps,stamps[1:])]
  cadence=sorted(gaps)[len(gaps)//2] if gaps else None
  expected=int((stamps[-1]-stamps[0]).total_seconds()/60/cadence)+1 if cadence and cadence>0 else len(stamps)
  result.append(dict(station=station,variable=variable,first=records[0]['time'],last=records[-1]['time'],count=len(records),typical_minutes=cadence,missing_fraction=round(max(0,1-len(stamps)/expected),3) if expected else None,major_gaps_minutes=sorted([g for g in gaps if g>=180],reverse=True)[:5],datum=records[0]['datum'],unit=records[0]['unit'],source=records[0]['source']))
 return result

def build(event_id):
 name, start, end = EVENTS[event_id]
 rows=[]; issues=[]; sources=[]; provenance=[]
 for station,(site, codes) in USGS.items():
  try:
   data,url=get_json('https://waterservices.usgs.gov/nwis/iv/', dict(format='json', sites=site, parameterCd=','.join(codes), startDT=start, endDT=end, siteStatus='all'))
   rows+=parse_usgs(data,station); sources.append(url)
  except (OSError, ValueError, KeyError) as e: issues.append(f'{station}: {e}')
 for product,variable,datum in [('water_level','water','MLLW'),('predictions','prediction','MLLW'),('wind','wind','none')]:
  params=dict(product=product, station='8761927', begin_date=start.replace('-',''), end_date=end.replace('-',''), units='english', time_zone='gmt', format='json')
  if product!='wind': params['datum']=datum
  if product=='predictions': params['interval']='6'
  try:
   data,url=get_json('https://api.tidesandcurrents.noaa.gov/api/prod/datagetter',params)
   rows+=parse_wind(data) if product=='wind' else parse_coops(data,variable,datum);sources.append(url)
  except (OSError, ValueError, KeyError) as e: issues.append(f'NWCL1 {product}: {e}')
 try:
  data,url=get_hads(start,end); hads_rows=parse_hads(data); rows+=hads_rows; sources.append(url)
  provenance=mchl1_provenance(start,end,'retrieved' if hads_rows else 'queried_unavailable')
 except (OSError, ValueError) as e:
  provenance=mchl1_provenance(start,end,'retrieval_error',str(e)); issues.append(f'MCHL1 HADS: {e}')
 sources.extend(source['interface'] for source in MCHL1_SOURCES[1:])
 rows=dedupe(rows); rows=dedupe(rows+residuals(rows)+changes(rows))
 result=dict(id=event_id,name=name,start=start,end=end,generated=dt.datetime.now(dt.timezone.utc).isoformat(),rows=rows,coverage=coverage(rows),issues=issues,sources=sources,mchl1_provenance=provenance,
  caveats=['MAUL1 historical 00065 gage height is not converted to NAVD88. Only direct 63160 elevations qualify for the 4.0 ft NAVD88 threshold.', 'NWCL1 observed and predicted levels use station MLLW; their difference is a non-tidal residual. Do not compare absolute lake height with other stations.', 'MDLL1 uses USGS 301200090072400 at Crossover 4 for this period; older Midlake USGS 073802330 is a separate instrument and is not spliced.', 'Event names describe meteorology, not measured dominant forcing.'])
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/f'{event_id}.json.gz').write_bytes(gzip.compress(json.dumps(result,separators=(',',':')).encode(),mtime=0))
 return dict(id=event_id, rows=len(rows), counts={k:sum(r['station']==k for r in rows) for k in ['DENL1','NWCL1','MDLL1','MCHL1','MAUL1']}, issues=issues)

def main():
 names=sys.argv[1:] or list(EVENTS)
 summary=[build(e) for e in names]
 existing=[]
 for e in EVENTS:
  path=OUT/f'{e}.json.gz'
  if path.exists():
   archive=json.loads(gzip.decompress(path.read_bytes()))
   existing.append(dict(id=e,rows=len(archive['rows']),counts={k:sum(r['station']==k for r in archive['rows']) for k in ['DENL1','NWCL1','MDLL1','MCHL1','MAUL1']},issues=archive['issues']))
 (OUT/'manifest.json').write_text(json.dumps(dict(events=[dict(id=e,name=EVENTS[e][0]) for e in EVENTS if (OUT/f'{e}.json.gz').exists()],summary=existing),indent=2))
 print(json.dumps(summary,indent=2))
 if all(not x['rows'] for x in summary): raise SystemExit('No event data downloaded')
if __name__=='__main__': main()
