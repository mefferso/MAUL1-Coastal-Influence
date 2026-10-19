"""Regenerate derived metadata and manifest for downloaded event JSON without re-fetching."""
import json
import gzip
from pathlib import Path
from build import EVENTS, OUT, coverage, changes, dedupe, residuals

def main():
 summary=[];available=[]
 for event_id,(name,_,_) in EVENTS.items():
  path=OUT/f'{event_id}.json.gz'
  if not path.exists():continue
  data=json.loads(gzip.decompress(path.read_bytes()))
  raw=[r for r in data['rows'] if not (r['variable']=='residual' or '_change_' in r['variable'])]
  rows=dedupe(raw+residuals(raw)+changes(raw))
  data['rows']=rows;data['coverage']=coverage(rows)
  path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
  available.append(dict(id=event_id,name=name))
  summary.append(dict(id=event_id,rows=len(rows),counts={station:sum(r['station']==station for r in rows) for station in ['DENL1','NWCL1','MDLL1','MCHL1','MAUL1']},issues=data['issues']))
 (OUT/'manifest.json').write_text(json.dumps(dict(events=available,summary=summary),indent=2))
if __name__=='__main__':main()
