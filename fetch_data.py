"""Refresh OSM snapshot only when explicitly requested; rebuild to fetch terrain."""
from pathlib import Path
import argparse,urllib.request,json
R=Path(__file__).resolve().parent
QUERY='[out:json][timeout:60];(way[building](55.916,-3.187,55.929,-3.163);relation[building](55.916,-3.187,55.929,-3.163);way[amenity=university](55.916,-3.187,55.929,-3.163);relation[amenity=university](55.916,-3.187,55.929,-3.163););out body;>;out skel qt;'
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--refresh',action='store_true',required=True);p.parse_args()
    req=urllib.request.Request('https://overpass-api.de/api/interpreter',data=QUERY.encode(),headers={'User-Agent':'Edinburgh-campus-radio-study/1.0'})
    with urllib.request.urlopen(req,timeout=120) as response:payload=response.read()
    data=json.loads(payload);assert data.get('elements')
    (R/'data/osm.json').write_bytes(payload)
    print('Snapshot refreshed. Rebuild all geometry, simulations, figures, validation, and report.')
