"""Monthly source adapters for the Phase 3A historical archive."""
import datetime as dt
import gzip
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request

import build
import history

USER_AGENT='MAUL1-research/3A (public historical archive)'
_NDBC_RAW_BY_YEAR={}

def _bounds(month):
 start=history._month_start(month); end=history._month_end(month)
 return start,end

def _iso(value):
 return value.strftime('%Y-%m-%dT%H:%M:%SZ')

def _filter_rows(rows,month):
 start,end=_bounds(month)
 result=[]
 for row in rows:
  stamp=dt.datetime.fromisoformat(row['time'].replace('Z','+00:00')).astimezone(dt.timezone.utc)
  if start <= stamp < end: result.append(row)
 return sorted(result,key=lambda row:(row['time'],row.get('station',''),row.get('variable','')))

def _result(rows,source,request,month,status='retrieved',error=None):
 rows=_filter_rows(rows,month)
 return {'rows':rows,'source':source,'request':request,'status':status,'error':error,
  'observed_start':rows[0]['time'] if rows else None,'observed_end':rows[-1]['time'] if rows else None}

def failure_result(station,month,request,error,status='retrieval_error'):
 return {'rows':[],'source':station,'request':request,'status':status,'error':error,'observed_start':None,'observed_end':None}

def _request(url,timeout=60):
 for attempt in range(3):
  try:
   request=urllib.request.Request(url,headers={'User-Agent':USER_AGENT})
   with urllib.request.urlopen(request,timeout=timeout) as response: return response.read(),url
  except urllib.error.HTTPError as error:
   if error.code in {403,404}: raise
   if attempt==2: raise
   time.sleep(2**attempt)
  except OSError:
   if attempt==2: raise
   time.sleep(2**attempt)

def _json(url):
 data,_=_request(url)
 return json.loads(data.decode('utf-8')),url

def parse_usgs_payload(payload,station,month):
 try: rows=build.parse_usgs(payload,station)
 except (KeyError,TypeError,ValueError) as error: return failure_result(station,month,'USGS NWIS IV',str(error))
 return _result(rows,'USGS NWIS IV','https://waterservices.usgs.gov/nwis/iv/',month)

def parse_coops_payload(payload,variable,datum,month):
 try: rows=build.parse_wind(payload) if variable=='wind' else build.parse_coops(payload,variable,datum)
 except (KeyError,TypeError,ValueError) as error: return failure_result('NWCL1',month,'NOAA CO-OPS Data API',str(error))
 return _result(rows,'NOAA CO-OPS 8761927','https://api.tidesandcurrents.noaa.gov/api/prod/datagetter',month)

def parse_hads_payload(payload,month):
 try: rows=build.parse_hads(payload)
 except (KeyError,TypeError,ValueError) as error: return failure_result('MCHL1',month,'Iowa Environmental Mesonet HADS',str(error))
 return _result(rows,'Iowa Environmental Mesonet archive of NWS HADS SHEF','https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py',month)

def parse_usace_payload(payload,source_id,month):
 row=build.parse_usace_row(payload,source_id)
 return _result(row,f'USACE RiverGages {source_id}',f'https://rivergages.mvr.army.mil/{source_id}',month)

def parse_ndbc_payload(payload,month,request='NDBC historical stdmet'):
 if isinstance(payload,bytes): payload=gzip.decompress(payload).decode('utf-8') if payload[:2]==b'\x1f\x8b' else payload.decode('utf-8')
 lines=payload.splitlines(); header=next((line[1:].split() for line in lines if line.startswith('#YY')),None)
 if not header: return failure_result('NWCL1-NDBC',month,request,'NDBC standard-met header unavailable','queried_unavailable')
 index={name:i for i,name in enumerate(header)}; rows=[]
 for line in lines:
  if not line.strip() or line.startswith('#'): continue
  fields=line.split()
  try:
   year=int(fields[index['#YY']]) if '#YY' in index else int(fields[index['YY']]); year=year+2000 if year<100 else year
   stamp=dt.datetime(year,int(fields[index['MM']]),int(fields[index['DD']]),int(fields[index['hh']]),int(fields[index['mm']]),tzinfo=dt.timezone.utc)
   direction=float(fields[index['WDIR']]); speed=float(fields[index['WSPD']])*1.943844492; gust=float(fields[index['GST']])*1.943844492
   if speed < 0 or not 0 <= direction <= 360: continue
  except (KeyError,ValueError,IndexError): continue
  angle=math.radians(direction)
  for variable,value,unit in [('wind',speed,'knots'),('wind_u',-speed*math.sin(angle),'knots'),('wind_v',-speed*math.cos(angle),'knots'),('wind_direction',direction,'degrees from'),('gust',gust,'knots')]:
   rows.append({'time':_iso(stamp),'value':round(value,6),'station':'NWCL1-NDBC','variable':variable,'unit':unit,'datum':'none','quality':'NDBC standard met','source':'NDBC historical standard meteorological archive'})
 return _result(rows,'NDBC historical standard meteorological archive',request,month)

def fetch_usgs_month(station,month):
 sites={'DENL1':('07378500',['00060','00065']),'MDLL1':('301200090072400',['00065']),'MAUL1':('07380215',['00065','63160'])}
 site,codes=sites[station]; start,end=_bounds(month)
 params={'format':'json','sites':site,'parameterCd':','.join(codes),'startDT':_iso(start),'endDT':_iso(end-dt.timedelta(seconds=1)),'siteStatus':'all'}
 url='https://waterservices.usgs.gov/nwis/iv/?'+urllib.parse.urlencode(params)
 try:
  payload,request=_json(url); result=parse_usgs_payload(payload,station,month); result['request']=request; return result
 except Exception as error: return failure_result(station,month,url,str(error))

def fetch_coops_month(product,month):
 start,end=_bounds(month); params={'product':product,'station':'8761927','begin_date':start.strftime('%Y%m%d'),'end_date':(end-dt.timedelta(days=1)).strftime('%Y%m%d'),'units':'english','time_zone':'gmt','format':'json'}
 if product!='wind': params['datum']='MLLW'
 if product=='predictions': params['interval']='6'
 url='https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'+urllib.parse.urlencode(params)
 try:
  payload,request=_json(url); variable='wind' if product=='wind' else ('prediction' if product=='predictions' else 'water')
  result=parse_coops_payload(payload,variable,'none' if variable=='wind' else 'MLLW',month); result['request']=request; return result
 except Exception as error: return failure_result('NWCL1',month,url,str(error))

def _effective_status(result):
 status=result.get('status')
 if status=='retrieved' and not result.get('rows'): return 'queried_unavailable'
 return status

def fetch_nwcl1_month(month):
 names=('water_level','predictions','wind')
 products=[fetch_coops_month(product,month) for product in names]
 rows=[row for result in products for row in result['rows']]
 failures=[result['error'] for result in products if result.get('error')]
 statuses=[_effective_status(result) for result in products]
 if rows and any(status!='retrieved' for status in statuses): status='partially_retrieved'
 elif rows: status='retrieved'
 elif failures: status='retrieval_error'
 else: status='queried_unavailable'
 result=_result(rows,'NOAA CO-OPS 8761927','NOAA CO-OPS monthly products',month,status,'; '.join(failures) if failures else None)
 result['components']={name:{'status':_effective_status(component),'row_count':len(component.get('rows',[])),
  'request':component.get('request'),'error':component.get('error')} for name,component in zip(names,products)}
 return result

def fetch_hads_month(month):
 start,end=_bounds(month); params={'stations':'MCHL1','sts':start.strftime('%Y-%m-%dT%H:%MZ'),'ets':(end-dt.timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%MZ'),'what':'txt'}
 url='https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py?'+urllib.parse.urlencode(params)
 try:
  raw,request=_request(url); result=parse_hads_payload(raw.decode('utf-8'),month); result['request']=request; return result
 except Exception as error: return failure_result('MCHL1',month,url,str(error))

def fetch_ndbc_month(month):
 start,end=_bounds(month); year=start.year; url=f'https://www.ndbc.noaa.gov/data/historical/stdmet/nwcl1h{year}.txt.gz'
 try:
  if year not in _NDBC_RAW_BY_YEAR: _NDBC_RAW_BY_YEAR[year]=_request(url)[0]
  return parse_ndbc_payload(_NDBC_RAW_BY_YEAR[year],month,url)
 except Exception as error: return failure_result('NWCL1-NDBC',month,url,str(error))

def fetch_usace_month(source_id,month):
 request=f'https://rivergages.mvr.army.mil/WaterControl/stationinfo2.cfm?sid={source_id}'
 return failure_result(f'USACE-{source_id}',month,request,'Historical observation endpoint requires station-specific provenance review','not_queried')

def fetch_usace_85420_month(month): return fetch_usace_month('85420',month)
def fetch_usace_85420la_month(month): return fetch_usace_month('85420LA',month)

DEFAULT_FETCHERS={'DENL1':lambda month:fetch_usgs_month('DENL1',month),'MDLL1':lambda month:fetch_usgs_month('MDLL1',month),
 'MAUL1':lambda month:fetch_usgs_month('MAUL1',month),'NWCL1':fetch_nwcl1_month,'MCHL1':fetch_hads_month,
 'NWCL1-NDBC':fetch_ndbc_month,'USACE-85420':fetch_usace_85420_month,'USACE-85420LA':fetch_usace_85420la_month}
