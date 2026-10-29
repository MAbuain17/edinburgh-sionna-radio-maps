"""Structural, coordinate, numerical-stability and result checks."""
from pathlib import Path
import json,numpy as np
from geodesy import forward,inverse
R=Path(__file__).resolve().parent
def db(a):return 10*np.log10(np.maximum(a,1e-30))
def main():
    d=np.load(R/'data/measurement.npz');v=d['vertices'];f=d['faces'];m=d['mask'];w=d['areas']
    assert np.all(np.isfinite(v)) and f.min()>=0 and f.max()<len(v)
    assert np.all(d['areas']>0) and np.all(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])[:,2]>0)
    lon=np.array([-3.187,-3.175,-3.163]);lat=np.array([55.916,55.922,55.929]);x,y=forward(lon,lat);ll,pp=inverse(x,y)
    error=float(max(np.max(abs(ll-lon)),np.max(abs(pp-lat))));assert error<1e-7
    def pct(a):return float(np.average(a[m],weights=w[m])*100)
    for freq in [2.4,3.5,5.8]:
        g=np.load(R/f'results/rt_{freq:g}GHz.npz')['path_gain'];assert g.shape==(3,len(f));assert np.all(np.isfinite(g)) and np.all(g>=0) and np.any(g>0)
    a=np.load(R/'results/rt_3.5GHz.npz')['path_gain'].max(0);b=np.load(R/'results/rt_3.5GHz_convergence.npz')['path_gain'].max(0);los=np.load(R/'results/rt_3.5GHz_los.npz')['path_gain'].max(0)
    both=m&(a>0)&(b>0);delta=np.abs(db(a[both])-db(b[both]));q=np.percentile(delta,[50,95,100])
    qa={'checks_passed':['finite terrain vertices','positive terrain triangle areas','upward terrain normals','UTM forward/inverse round trip','nonnegative finite radio gains','result shape agrees with measurement mesh'],'coordinate_roundtrip_max_deg':error,'sample_convergence':{'base_samples_per_tx_per_seed':20000000,'comparison_samples_per_tx_per_seed':40000000,'median_abs_delta_db_both_positive':q[0],'p95_abs_delta_db_both_positive':q[1],'max_abs_delta_db_both_positive':q[2],'base_rss_ge_minus85_pct':pct(30+db(a)>=-85),'comparison_rss_ge_minus85_pct':pct(30+db(b)>=-85),'zero_state_disagreement_pct':pct((a==0)!=(b==0))},'los_ablation':{'los_only_rss_ge_minus85_pct':pct(30+db(los)>=-85),'depth3_rss_ge_minus85_pct':pct(30+db(a)>=-85)},'scope':'Modeled outdoor campus surface triangles; classification at triangle centroids; not field validation'}
    (R/'results/validation.json').write_text(json.dumps(qa,indent=2));print(json.dumps(qa,indent=2))
if __name__=='__main__':main()
