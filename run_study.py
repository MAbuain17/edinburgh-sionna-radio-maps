"""Actual Sionna RT experiment; saves per-transmitter linear gains before aggregation.

Example: python run_study.py --samples 1000000 --seeds 17 29
Optional Windows CPU: set DRJIT_LIBLLVM_PATH to the official LLVM-C.dll path.
"""
from pathlib import Path
import argparse, json, time, platform, importlib.metadata, sys, os
import numpy as np

ROOT=Path(__file__).resolve().parent
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--samples',type=int,default=1000000)
    ap.add_argument('--seeds',type=int,nargs='+',default=[17,29]);ap.add_argument('--frequencies',type=float,nargs='+',default=[2.4,3.5,5.8])
    ap.add_argument('--depth',type=int,default=3);ap.add_argument('--suffix',default='');args=ap.parse_args()
    import sionna.rt as rt
    import mitsuba as mi
    import drjit as dr
    scene=rt.load_scene(str(ROOT/'scene/scene.xml'),merge_shapes=False)
    scene.tx_array=rt.PlanarArray(num_rows=1,num_cols=1,pattern='iso',polarization='V')
    scene.rx_array=scene.tx_array
    sites=json.loads((ROOT/'data/transmitters.json').read_text())
    for t in sites:scene.add(rt.Transmitter(name=t['id'],position=[t['x'],t['y'],t['z']],power_dbm=t['power_dbm']))
    surface=scene.objects['ground'].clone(as_mesh=True)
    rt.transform_mesh(surface,translation=[0,0,1.5])
    solver=rt.RadioMapSolver();out=ROOT/'results';out.mkdir(exist_ok=True)
    for ghz in args.frequencies:
        scene.frequency=ghz*1e9;arrays=[];times=[]
        for seed in args.seeds:
            start=time.perf_counter()
            rm=solver(scene,measurement_surface=surface,samples_per_tx=args.samples,max_depth=args.depth,seed=seed,
                      los=True,specular_reflection=True,diffuse_reflection=False,refraction=False,diffraction=False)
            gain=rm.path_gain.numpy().copy();arrays.append(gain);times.append(time.perf_counter()-start)
            print(f'{ghz} GHz seed {seed}: {gain.shape}, {times[-1]:.1f} s',flush=True)
            del rm;dr.flush_malloc_cache()
        name=f'rt_{ghz:g}GHz{args.suffix}'
        np.savez_compressed(out/f'{name}.npz',path_gain=np.mean(arrays,axis=0),seed_gains=np.array(arrays),seeds=args.seeds,samples_per_tx=args.samples,frequency_hz=ghz*1e9)
        meta={'engine':'Sionna RT','sionna_rt':rt.__version__,'mitsuba':mi.__version__,'backend':mi.variant(),'platform':platform.platform(),'frequency_ghz':ghz,'samples_per_tx_per_seed':args.samples,'seeds':args.seeds,'elapsed_seconds':times,'max_depth':args.depth,'los':True,'specular_reflection':True,'diffuse_reflection':False,'diffraction':False,'refraction':False,'tx_pattern':'iso, V polarization','measurement':'terrain mesh shifted vertically 1.5 m; two triangles per 10 m cell','power_dbm_per_site':30,'bandwidth_hz':20e6,'noise_figure_db':7,'noise_dbm':-174+10*np.log10(20e6)+7}
        (out/f'{name}.json').write_text(json.dumps(meta,indent=2))
if __name__=='__main__':
    main()
    # Some Windows LLVM builds hang during native-library interpreter teardown.
    # All result files are synchronously closed by main before this CLI-only exit.
    # Imported use of main() keeps ordinary Python lifecycle semantics.
    if sys.platform=='win32':
        sys.stdout.flush();sys.stderr.flush();os._exit(0)
