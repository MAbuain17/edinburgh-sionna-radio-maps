# Reproducing the study

The included results were computed with Sionna RT 2.2.0, Mitsuba 3.9.1 and the LLVM CPU backend on Windows x64. Tested dependency versions are recorded in `requirements.txt`.

## Environment

Use Python 3.12 and an isolated environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\Activate.ps1`.

Ray tracing requires a compatible NVIDIA GPU or an LLVM CPU backend. The Windows CPU configuration used LLVM 21.1.8. Install the official distribution and point Dr.Jit to its library:

```powershell
$env:DRJIT_LIBLLVM_PATH = 'C:\path\to\LLVM-C.dll'
```

See the [Dr.Jit installation documentation](https://drjit.readthedocs.io/en/stable/what.html) for backend setup. The command-line runners flush completed outputs and exit explicitly on Windows to handle native interpreter shutdown in the tested CPU configuration.

## Run the experiment

Run these commands from the repository root. Cached geographic inputs allow the scene to be rebuilt offline.

```bash
python build_scene.py
python run_study.py --samples 20000000 --seeds 17 29
python run_study.py --samples 20000000 --seeds 17 29 --frequencies 3.5 --depth 0 --suffix _los
python run_study.py --samples 40000000 --seeds 17 29 --frequencies 3.5 --suffix _convergence
python validate.py
python export_lrm.py
python analyze.py
python render_model.py
python make_report.py
```

The main run evaluates 2.4, 3.5 and 5.8 GHz. Additional runs provide a line-of-sight comparison and a sample-count convergence check at 3.5 GHz. `analyze.py` rebuilds figures, tables and the explorer from saved path gains. `make_report.py` writes the PDF and Markdown report.

For a shorter installation check, use a distinct suffix to preserve the published results:

```bash
python run_study.py --samples 100000 --seeds 17 --frequencies 3.5 --suffix _smoke
```

## Validate included outputs

```bash
python validate.py
```

The checks cover mesh coordinates, triangle areas and orientation, coordinate round trips, path-gain dimensions and values, sample convergence, and the line-of-sight comparison. Results are written to `results/validation.json`.

At 3.5 GHz, coverage changes from 77.41% to 77.88% when the samples per transmitter and seed increase from 20 million to 40 million. Among cells with positive gains in both runs, the median absolute received-power change is 0.057 dB and the 95th percentile is 1.34 dB.

## Refresh geographic inputs

```bash
python fetch_data.py --refresh
```

Refreshing the OSM snapshot starts a new experiment. Rebuild the scene and rerun the simulations, analysis and report together to keep inputs and results consistent. Hardware, compiler and package versions can produce numerical differences.
