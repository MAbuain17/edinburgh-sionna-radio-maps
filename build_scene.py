"""Rebuild the campus scene from cached OSM and Mapzen terrain tiles."""
from pathlib import Path
import json, math, urllib.request, hashlib, struct, csv
from datetime import datetime, timezone
import numpy as np
from PIL import Image
from geodesy import forward, inverse
from shapely.geometry import Polygon, LineString, Point, mapping
from shapely.ops import polygonize, unary_union, transform
from shapely import make_valid
from shapely.geometry.polygon import orient
import mapbox_earcut as earcut
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
ORIGIN=np.array(forward(-3.175,55.922))

def local(lon,lat,z=None):
    x,y=forward(lon,lat)
    return np.asarray(x)-ORIGIN[0],np.asarray(y)-ORIGIN[1]
def geo(x,y,z=None): return inverse(np.asarray(x)+ORIGIN[0],np.asarray(y)+ORIGIN[1])
def dump(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')

def polygons(g):
    if g.geom_type=='Polygon': return [g]
    return [p for p in getattr(g,'geoms',[]) if p.geom_type=='Polygon']

def ply(path,vertices,faces):
    v=np.asarray(vertices,dtype='<f4'); f=np.asarray(faces,dtype='<i4')
    with path.open('wb') as out:
        out.write((f'ply\nformat binary_little_endian 1.0\nelement vertex {len(v)}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(f)}\nproperty list uchar int vertex_indices\nend_header\n').encode())
        out.write(v.tobytes())
        ff=np.empty(len(f),dtype=[('n','u1'),('i','<i4',(3,))]);ff['n']=3;ff['i']=f;out.write(ff.tobytes())

class Terrain:
    def __init__(self): self.tiles={};self.z=14
    def __call__(self,x,y):
        lon,lat=geo(x,y);n=2**self.z
        fx=(np.asarray(lon)+180)/360*n
        fy=(1-np.arcsinh(np.tan(np.deg2rad(lat)))/np.pi)/2*n
        shape=np.shape(fx); fx=np.atleast_1d(fx).ravel();fy=np.atleast_1d(fy).ravel();out=[]
        for a,b in zip(fx,fy):
            tx,ty=int(a),int(b);key=(tx,ty)
            if key not in self.tiles:
                path=DATA/f'terrain_{self.z}_{tx}_{ty}.png'
                if not path.exists():
                    url=f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{self.z}/{tx}/{ty}.png'
                    urllib.request.urlretrieve(url,path)
                rgb=np.asarray(Image.open(path).convert('RGB'),dtype=float)
                self.tiles[key]=rgb[:,:,0]*256+rgb[:,:,1]+rgb[:,:,2]/256-32768
            tile=self.tiles[key];u=(a-tx)*255;v=(b-ty)*255;i,j=int(u),int(v);du,dv=u-i,v-j
            i=min(i,254);j=min(j,254)
            out.append((1-du)*(1-dv)*tile[j,i]+du*(1-dv)*tile[j,i+1]+(1-du)*dv*tile[j+1,i]+du*dv*tile[j+1,i+1])
        return np.array(out).reshape(shape)

def main():
    raw=json.loads((DATA/'osm.json').read_text(encoding='utf8'))
    els=raw['elements'];nodes={e['id']:(e['lon'],e['lat']) for e in els if e['type']=='node'}
    ways={e['id']:e for e in els if e['type']=='way'}
    def outline(w): return [local(*nodes[i]) for i in w['nodes']]
    campus=make_valid(Polygon(outline(ways[9514792])))
    # Metric rectangle with at least 150 m of surrounding geometry on every side.
    bounds=campus.buffer(150).bounds
    xmin,ymin=np.floor(np.array(bounds[:2])/10)*10;xmax,ymax=np.ceil(np.array(bounds[2:])/10)*10
    records=[];members=set();errors=[]
    for rel in [e for e in els if e['type']=='relation' and 'building' in e.get('tags',{})]:
        try:
            rings={}
            for role in ['outer','inner']:
                lines=[LineString(outline(ways[m['ref']])) for m in rel['members'] if m['type']=='way' and m.get('role','outer')==role and m['ref'] in ways]
                rings[role]=unary_union(list(polygonize(lines)))
            g=rings['outer'].difference(rings['inner'])
            records.append((f"relation/{rel['id']}",g,rel['tags']))
            members.update(m['ref'] for m in rel['members'] if m['type']=='way')
        except Exception as ex: errors.append({'id':rel['id'],'error':str(ex)})
    for ident,w in ways.items():
        tags=w.get('tags',{})
        if 'building' not in tags or tags['building']=='no' or ident in members: continue
        if w['nodes'][0]!=w['nodes'][-1]:errors.append({'id':ident,'error':'open footprint'});continue
        records.append((f'way/{ident}',make_valid(Polygon(outline(w))),tags))
    from shapely.geometry import box
    boxpoly=box(xmin,ymin,xmax,ymax); terrain=Terrain()
    zref=float(terrain(0,0));features=[];verts=[];faces=[]
    for ident,g,tags in records:
        if not g.intersects(boxpoly):continue
        def number(k):
            try: return float(tags[k].replace(' m',''))
            except (KeyError,ValueError):return None
        h=number('height');levels=number('building:levels')
        source='OSM height' if h else 'OSM levels x 3.5 m' if levels and levels>0 else 'assumed 10.5 m'
        h=h or (levels*3.5 if levels and levels>0 else 10.5)
        for part,p in enumerate(polygons(make_valid(g))):
            if p.area<1:continue
            p=orient(p,sign=1)
            rings=[np.asarray(p.exterior.coords)[:-1]]+[np.asarray(r.coords)[:-1] for r in p.interiors]
            xy=np.vstack(rings);ends=np.cumsum([len(r) for r in rings],dtype=np.uint32)
            tri=earcut.triangulate_float64(xy,ends).reshape(-1,3)
            area=sum(abs((xy[b,0]-xy[a,0])*(xy[c,1]-xy[a,1])-(xy[b,1]-xy[a,1])*(xy[c,0]-xy[a,0]))/2 for a,b,c in tri)
            if not np.isclose(area,p.area,rtol=1e-6): raise ValueError(f'Roof triangulation failed for {ident}')
            grounds=terrain(xy[:,0],xy[:,1])-zref;base=float(grounds.min())-0.5;roof=float(grounds.max())+h
            n=len(xy);start=len(verts);verts.extend(np.c_[xy,np.full(n,base)]);verts.extend(np.c_[xy,np.full(n,roof)])
            faces.extend((tri[:,::-1]+start).tolist());faces.extend((tri+n+start).tolist())
            begin=0
            for end in ends:
                for i in range(begin,int(end)):
                    j=i+1 if i+1<end else begin
                    faces.extend([[start+i,start+j,start+j+n],[start+i,start+j+n,start+i+n]])
                begin=int(end)
            features.append({'type':'Feature','geometry':mapping(p),'properties':{'osm_id':ident,'part':part,'name':tags.get('name',ident),'height_m':h,'height_source':source,'base_z':base,'roof_z':roof,'inside_campus':campus.covers(p.representative_point()),'tags':tags}})
    scene=ROOT/'scene';scene.mkdir(exist_ok=True);(scene/'meshes').mkdir(exist_ok=True)
    ply(scene/'meshes/buildings.ply',verts,faces)
    # Shared vertices and two triangles per 10 m terrain cell, south-to-north ordering.
    xs=np.arange(xmin,xmax+1,10);ys=np.arange(ymin,ymax+1,10);xx,yy=np.meshgrid(xs,ys)
    zz=terrain(xx,yy)-zref;ground=np.c_[xx.ravel(),yy.ravel(),zz.ravel()];gf=[]
    for j in range(len(ys)-1):
        for i in range(len(xs)-1):
            a=j*len(xs)+i;b=a+1;c=a+len(xs);d=c+1;gf.extend([[a,b,d],[a,d,c]])
    gf=np.array(gf);ply(scene/'meshes/ground.ply',ground,gf)
    centers=ground[gf].mean(axis=1)
    from shapely import points,contains
    buildings=unary_union([__import__('shapely').geometry.shape(f['geometry']) for f in features])
    mask=contains(campus,points(centers[:,:2])) & ~contains(buildings,points(centers[:,:2]))
    areas=np.linalg.norm(np.cross(ground[gf[:,1]]-ground[gf[:,0]],ground[gf[:,2]]-ground[gf[:,0]]),axis=1)/2
    np.savez(DATA/'measurement.npz',vertices=ground,faces=gf,centers=centers,mask=mask,areas=areas,x=xs,y=ys)
    xml='''<?xml version="1.0"?><scene version="3.0.0">
<bsdf type="diffuse" id="mat-itu_concrete"><rgb name="reflectance" value="0.65 0.68 0.72"/></bsdf>
<bsdf type="diffuse" id="mat-itu_wet_ground"><rgb name="reflectance" value="0.32 0.40 0.34"/></bsdf>
<shape type="ply" id="mesh-buildings"><string name="filename" value="meshes/buildings.ply"/><ref id="mat-itu_concrete" name="bsdf"/><boolean name="face_normals" value="true"/></shape>
<shape type="ply" id="mesh-ground"><string name="filename" value="meshes/ground.ply"/><ref id="mat-itu_wet_ground" name="bsdf"/><boolean name="face_normals" value="true"/></shape>
</scene>'''
    (scene/'scene.xml').write_text(xml,encoding='utf8')
    # Portable geometry interchange for Blender, CAD, and other viewers.
    with (scene/'campus.obj').open('w') as out:
        out.write('# OSM footprint extrusions and sampled terrain; local UTM metres\no buildings\n')
        for v in verts:out.write('v '+' '.join(f'{c:.4f}' for c in v)+'\n')
        for f in faces:out.write('f '+' '.join(str(int(i)+1) for i in f)+'\n')
        out.write('o terrain\n')
        for v in ground:out.write('v '+' '.join(f'{c:.4f}' for c in v)+'\n')
        for f in gf:out.write('f '+' '.join(str(int(i)+1+len(verts)) for i in f)+'\n')
    dump(DATA/'buildings_local.geojson',{'type':'FeatureCollection','features':features,'coordinate_note':'Local EPSG:32630 metres minus origin; not WGS84 GeoJSON'})
    geo_features=[dict(f,geometry=mapping(transform(geo,__import__('shapely').geometry.shape(f['geometry'])))) for f in features]
    dump(DATA/'buildings.geojson',{'type':'FeatureCollection','features':geo_features})
    dump(DATA/'campus_boundary.geojson',{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'source':'OSM way/9514792; mapped extent, not legal cadastral boundary'},'geometry':mapping(transform(geo,campus))}]})
    tx=[]
    for code,name in [('A','Noreen and Kenneth Murray Library'),('B','James Clerk Maxwell Building'),('C','Joseph Black Building')]:
        f=next(f for f in features if f['properties']['name']==name);p=__import__('shapely').geometry.shape(f['geometry']).representative_point();lon,lat=geo(p.x,p.y)
        tx.append({'id':code,'name':name,'x':p.x,'y':p.y,'z':f['properties']['roof_z']+3,'lat':float(lat),'lon':float(lon),'power_dbm':30,'height_above_modeled_roof_m':3,'status':'hypothetical study site, not an existing installation'})
    dump(DATA/'transmitters.json',tx)
    with (DATA/'transmitters_lrm.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=['lat','lon','elevation','building']);writer.writeheader()
        for t in tx:writer.writerow({'lat':t['lat'],'lon':t['lon'],'elevation':t['z']+zref-2,'building':1})
    # LRM adds 2 m to building elevation: export desired antenna elevation minus 2 m.
    sw=geo(xmin,ymin);ne=geo(xmax,ymax)
    np.savez(DATA/'lrm_bbox.npz',corners=np.array([[[sw[1],sw[0]],[ne[1],ne[0]]]]))
    metadata={'name':"King's Buildings campus",'campus_osm':'https://www.openstreetmap.org/way/9514792','campus_area_m2':campus.area,'origin_lonlat':[-3.175,55.922],'origin_utm_m':ORIGIN.tolist(),'crs':'EPSG:32630','z_reference_m':zref,'bounds_xy_m':[xmin,ymin,xmax,ymax],'bbox_swne_latlon':[[sw[1],sw[0]],[ne[1],ne[0]]],'terrain_z_range_m':[float(zz.min()),float(zz.max())],'buildings_total':len(features),'campus_buildings':sum(f['properties']['inside_campus'] for f in features),'height_sources':{s:sum(f['properties']['height_source']==s for f in features) for s in ['OSM height','OSM levels x 3.5 m','assumed 10.5 m']},'mesh_building_triangles':len(faces),'measurement_triangles':len(gf),'outdoor_campus_triangles':int(mask.sum()),'errors':errors,'osm_timestamp':raw.get('osm3s',{}),'built_utc':datetime.now(timezone.utc).isoformat()}
    dump(DATA/'metadata.json',metadata)
    dump(DATA/'provenance.json',{'sources':['https://github.com/NVlabs/sionna-large-radio-maps','https://science-engineering.ed.ac.uk/about/location-map','https://www.openstreetmap.org/copyright','https://registry.opendata.aws/terrain-tiles/','https://github.com/tilezen/joerd/blob/master/docs/attribution.md'],'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob('*') if p.name=='osm.json' or p.suffix=='.png'}})
    print(json.dumps(metadata,indent=2))
if __name__=='__main__':main()
