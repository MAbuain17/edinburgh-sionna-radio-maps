"""Export our geometry into NVIDIA LRM's SW-origin and absolute-altitude convention.

This writes one native-layout tile. Run the upstream project in a SEPARATE
environment pinned to its own requirements. No native LRM run is claimed here.
"""
from pathlib import Path
import json,shutil,numpy as np
from build_scene import ply
R=Path(__file__).resolve().parent
def read_ply(p):
    with p.open('rb') as s:
        nv=nf=0
        while True:
            line=s.readline().decode().strip()
            if line.startswith('element vertex'):nv=int(line.split()[-1])
            if line.startswith('element face'):nf=int(line.split()[-1])
            if line=='end_header':break
        v=np.frombuffer(s.read(nv*12),dtype='<f4').reshape(-1,3).copy()
        f=np.frombuffer(s.read(),dtype=[('n','u1'),('i','<i4',(3,))])['i'].copy();assert len(f)==nf
        return v,f
def main():
    m=json.loads((R/'data/metadata.json').read_text());out=R/'lrm_export/kings_buildings';tile=out/'0';(tile/'meshes').mkdir(parents=True,exist_ok=True)
    for name in ['buildings','ground']:
        v,f=read_ply(R/f'scene/meshes/{name}.ply');v[:,0]-=m['bounds_xy_m'][0];v[:,1]-=m['bounds_xy_m'][1];v[:,2]+=m['z_reference_m'];ply(tile/f'meshes/{name}.ply',v,f)
    shutil.copy2(R/'scene/scene.xml',tile/'scene.xml');shutil.copy2(R/'data/lrm_bbox.npz',out/'bboxes.npz');shutil.copy2(R/'data/transmitters_lrm.csv',R/'lrm_export/transmitters.csv')
    print(out)
if __name__=='__main__':main()
