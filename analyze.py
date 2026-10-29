"""Generate inspectable metrics, PNG/SVG figures and a self-contained explorer."""
from pathlib import Path
import json,csv,html
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from shapely.geometry import shape
from shapely.ops import transform
from build_scene import local

R=Path(__file__).resolve().parent
def load(p):return json.loads((R/p).read_text(encoding='utf8'))
def db(a):return 10*np.log10(np.maximum(a,1e-30))
def main():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})
    out=R/'figures';out.mkdir(exist_ok=True)
    meta=load('data/metadata.json');b=load('data/buildings_local.geojson')['features'];sites=load('data/transmitters.json')
    campus=transform(local,shape(load('data/campus_boundary.geojson')['features'][0]['geometry']))
    d=np.load(R/'data/measurement.npz');v=d['vertices'];f=d['faces'];c=d['centers'];mask=d['mask'];w=d['areas'];tri=v[f];bounds=meta['bounds_xy_m']
    records=[];maps={};noise=10**((-174+10*np.log10(20e6)+7)/10)
    def pct(a):return float(np.sum(w[mask]*a[mask])/np.sum(w[mask])*100)
    def base(ax,labels=True):
        for feat in b:
            p=shape(feat['geometry']);x,y=p.exterior.xy
            ax.fill(x,y,color='#dde2e7',edgecolor='#7c8996',linewidth=.22,zorder=2)
            for hole in p.interiors:ax.fill(*hole.xy,color='white',zorder=3)
        ax.plot(*campus.exterior.xy,color='#e36b31',lw=1.6,zorder=4,label='OSM campus boundary')
        for t in sites:
            ax.scatter(t['x'],t['y'],s=65,marker='^',c='#ed334e',edgecolors='white',zorder=5)
            if labels:ax.annotate(t['id'],(t['x'],t['y']),xytext=(7,5),textcoords='offset points',weight='bold',zorder=6)
        ax.set(xlim=(bounds[0],bounds[2]),ylim=(bounds[1],bounds[3]),aspect='equal',xlabel='Local easting (m)',ylabel='Local northing (m)')
    fig,ax=plt.subplots(figsize=(11,8));pc=PolyCollection(tri[:,:,:2],array=c[:,2]+meta['z_reference_m'],cmap='terrain',edgecolors='none');ax.add_collection(pc);base(ax)
    fig.colorbar(pc,ax=ax,shrink=.75,label='Terrain elevation in source datum (m)')
    ax.set_title("King's Buildings | mapped campus and surrounding geometry",loc='left',weight='bold',pad=16)
    fig.text(.1,.025,'A Murray Library   B James Clerk Maxwell Building   C Joseph Black Building\nProposed rooftop sites; orange boundary is the study mask. OSM contributors / Mapzen terrain.',fontsize=9)
    fig.subplots_adjust(bottom=.15);fig.savefig(out/'campus_overview.png',dpi=180);fig.savefig(out/'campus_overview.svg');plt.close(fig)
    for ghz in [2.4,3.5,5.8]:
        data=np.load(R/f'results/rt_{ghz:g}GHz.npz');g=data['path_gain'];p=1000*g # 30 dBm = 1000 mW
        best=p.max(axis=0);sinr=best/(p.sum(axis=0)-best+noise)
        seeds=data['seed_gains'];positive=(seeds[0].max(0)>0)&(seeds[1].max(0)>0)&mask
        delta=np.abs(db(seeds[0].max(0))-db(seeds[1].max(0)))
        for layout,selected in [('single_A',p[0]),('best_of_ABC',best)]:
            sg=selected/noise if layout=='single_A' else sinr
            records.append({'frequency_ghz':ghz,'layout':layout,'rss_ge_minus85_dbm_pct':pct(db(selected)>=-85),'sinr_ge_5_db_pct':pct(db(sg)>=5),'joint_rss_sinr_pct':pct((db(selected)>=-85)&(db(sg)>=5)),'zero_gain_pct':pct(selected==0),'median_seed_delta_db_on_both_positive':float(np.median(delta[positive])),'p95_seed_delta_db_on_both_positive':float(np.percentile(delta[positive],95)),'seed_delta_cells_count':int(positive.sum())})
        maps[str(ghz)]={'gains':np.round(db(g),2).tolist()}
        with (R/f'results/cells_{ghz:g}GHz.csv').open('w',newline='') as fp:
            writer=csv.writer(fp);writer.writerow(['triangle','x_m','y_m','terrain_local_z_m','outdoor_campus','area_m2','path_gain_A','path_gain_B','path_gain_C','best_rss_dbm','reuse1_sinr_db'])
            for i in range(len(c)):writer.writerow([i,*c[i],int(mask[i]),w[i],*g[:,i],db(best[i]) if best[i]>0 else '',db(sinr[i]) if best[i]>0 else ''])
        if ghz==3.5:
            fig,axes=plt.subplots(1,3,figsize=(17,5.7),layout='constrained')
            for ax,title,values,limits,cmap in zip(axes,['One site A | received power','Three sites | strongest received power','Three sites | full-load cochannel SINR'],[db(p[0]),db(best),db(sinr)],[(-110,-50),(-110,-50),(-10,30)],['viridis','viridis','coolwarm']):
                vals=values.copy();vals[~mask]=np.nan
                pc=PolyCollection(tri[:,:,:2],array=np.ma.masked_invalid(vals),cmap=cmap,clim=limits,edgecolors='none');ax.add_collection(pc);base(ax);ax.set_title(title,fontsize=11)
                ax.set_xlim(campus.bounds[0]-30,campus.bounds[2]+30);ax.set_ylim(campus.bounds[1]-30,campus.bounds[3]+30)
                fig.colorbar(pc,ax=ax,orientation='horizontal',shrink=.9,pad=.12,label='dBm' if cmap=='viridis' else 'dB')
            fig.suptitle('3.5 GHz campus experiment | actual Sionna RT predictions',fontsize=16,weight='bold')
            fig.savefig(out/'radio_comparison.png',dpi=180);fig.savefig(out/'radio_comparison.svg');plt.close(fig)
            fig,ax=plt.subplots(figsize=(8,5))
            for selected,label,color in [(p[0],'One site A','#324b78'),(best,'Best of A+B+C','#e36b31')]:
                a=db(selected[mask]);order=np.argsort(a);weights=w[mask][order];ax.plot(a[order],np.cumsum(weights)/weights.sum()*100,label=label,color=color,lw=2)
            ax.axvline(-85,c='gray',ls='--',lw=1);ax.set(xlim=(-130,-40),ylim=(0,100),xlabel='Received power (dBm; zero-gain cells fall below axis)',ylabel='Outdoor campus surface area at or below value (%)',title='Received-power distribution at 3.5 GHz');ax.legend();ax.grid(alpha=.2)
            fig.tight_layout();fig.savefig(out/'rss_distribution.png',dpi=180);plt.close(fig)
    with (R/'results/summary.csv').open('w',newline='') as fp:
        writer=csv.DictWriter(fp,fieldnames=records[0].keys());writer.writeheader();writer.writerows(records)
    (R/'results/summary.json').write_text(json.dumps(records,indent=2))
    payload={'meta':meta,'sites':sites,'buildings':[{'p':[[round(x,2),round(y,2)] for x,y in shape(q['geometry']).exterior.coords],'holes':[[[round(x,2),round(y,2)] for x,y in h.coords] for h in shape(q['geometry']).interiors],**q['properties']} for q in b], 'boundary':list(campus.exterior.coords),'vertices':np.round(v,2).tolist(),'faces':f.tolist(),'mask':mask.tolist(),'maps':maps,'summary':records}
    template=(R/'explorer_template.html').read_text(encoding='utf8')
    (R/'explorer.html').write_text(template.replace('/*PAYLOAD*/',json.dumps(payload,ensure_ascii=True).replace('<','\\u003c')),encoding='utf8')
    print(json.dumps(records,indent=2))
if __name__=='__main__':main()
