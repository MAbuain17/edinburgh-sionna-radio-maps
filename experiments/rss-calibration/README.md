# Does RSS calibration transfer along a flight?

This draft tests a small question: if a ray tracer has a power bias on the first part of a flight, does correcting that bias help on a later part?

It compares unchanged RSS predictions with a constant offset and an affine correction. Each link is fitted separately on an early time block, followed by a gap and a held-out block. The experiment runs on a CPU and consumes exported RSS values. It does not run Sionna itself.

## Status

The Python pipeline and artificial-data tests run. The intended measurement source is the [AERPAW/Sionna dataset by Lee, Ozdemir and Guvenc](https://doi.org/10.5061/dryad.ttdz08m8r). The archive download returned HTTP 403 during development, so the MAT importer has only been checked against a fixture matching its documented schema. No measured-data results are claimed here.

The dataset's D3 measurements are **already calibrated**. An experiment on D3 is a residual-correction study. Splitting D3 locally does not establish that the upstream calibration was independent of the held-out samples. Inspect `C2_RSS_postprocessing.m` before making that claim.

## Run the draft

From the repository root, using Python 3.12:

```bash
cd experiments/rss-calibration
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest -v
python make_fixture.py data/synthetic.csv
python calibrate.py data/synthetic.csv --out output/synthetic \
  --data-kind synthetic --source "make_fixture.py; seed 17" \
  --train-fraction 0.5 --gap-s 10
```

On Windows, activate with `.venv\Scripts\activate` and put the calibration command on one line.

The fixture contains two artificial links. One has a stable +6 dB measurement offset. The other switches from +6 dB to -6 dB after the fit block. The second case checks that an apparently good training fit can make later predictions worse. These are software checks, not a model of UAV propagation.

The checked run produced these held-out RMSE values, in dB:

| Artificial link | Uncorrected | Offset | Affine |
|---|---:|---:|---:|
| Stable offset | 6.020 | 0.966 | 1.017 |
| Changing offset | 6.005 | 11.842 | 11.842 |

The full synthetic run is recorded in [`examples/synthetic_metrics.json`](examples/synthetic_metrics.json). Recreate the figure with the command above.

Outputs:

- `metrics.json`: per-link fit coefficients, train/test errors, sample counts, split settings, source label, input SHA-256 and NumPy version.
- `held_out.csv`: predictions and measurements for the test block only.
- `rss.png`: traces with the fit block and gap marked.

## Bring in the measurement data

Download and extract `Sionna_Ray_Tracing_Real_World_Measurements.zip` from the DOI above. Keep it under the ignored `data/` directory, then run:

```bash
python import_dryad.py data/D3_RT_Measurement_RSS_postprocessed_data.mat data/dryad_ch1.csv --channel 1
python calibrate.py data/dryad_ch1.csv --out output/dryad_ch1 \
  --data-kind precalibrated --source https://doi.org/10.5061/dryad.ttdz08m8r \
  --train-fraction 0.5 --gap-s 10
```

Adjust the MAT path to the extracted directory. The importer uses the documented `LWs` cells and fields `time_reference`, `RSS_arr_plot`, and `RSS1_offset` or `RSS2_offset`. It refuses unequal array lengths or non-finite values rather than silently aligning or dropping samples. Inspect any failure against the MATLAB processing scripts.

Other sources can use this CSV format:

```csv
link,time_s,predicted_dbm,measured_dbm
LW1_ch1,0,-80.0,-74.0
LW1_ch1,1,-81.0,-75.0
```

Use one link identifier per tower/channel/flight. Times must increase strictly within each link; at least three fit samples and two test samples must remain. Predictions and measurements must already refer to the same times, receiver channel, bandwidth and power convention. The two rows above illustrate the schema only.

## Method

For each link, the cutoff is `first_time + train_fraction * elapsed_duration`. Fit samples have `time <= cutoff`; test samples have `time > cutoff + gap_s`. The intervening samples are unused. The default 10-second gap is a starting setting, not an established decorrelation time.

The offset is the training mean of `measured - predicted`, in dB. The affine model fits `measured = slope * predicted + intercept` by ordinary least squares in dBm. A constant prediction trace cannot identify the slope, so that model is omitted with a recorded warning.

Errors are prediction minus measurement. Bias is their mean, MAE is their mean absolute value, and RMSE is their root mean square. All are reported in dB. Models use the same held-out samples. The code reports all models; it does not select the best one using test errors.

An offset can absorb a power-reference mismatch. An affine fit is an empirical baseline; it does not estimate permittivity, foliage loss, or a physically valid channel. RSS alone also leaves phase, delay spread, Doppler and MIMO structure untested. This is a propagation-validation exercise relevant to channel modelling, not a material classifier.

## Next two days

1. Inspect the original MATLAB preprocessing and verify the imported samples against its plots. Record which quantities were calibrated upstream, where offsets came from, and whether they used the entire flight.
2. Run both receiver channels separately. Compare all three models at a predeclared cutoff. Repeat at a few cutoffs and gaps as a sensitivity analysis, without choosing a winning configuration from test scores.
3. Inspect residuals over time and location. Report where correction fails. A temporal gap alone does not prevent spatial overlap if the UAV returns to a previously visited location.
4. Write one page with the result table, one residual figure and the limitations. Keep synthetic outputs labelled. For a stronger generalization claim, hold out a separate flight or route and fit all preprocessing on training data only.

Tests cover coefficient recovery, metric signs, time-based splitting, held-out-label isolation, distribution shift, degenerate fits, invalid inputs and the documented MAT cell structure. They do not validate the original dataset or Sionna's propagation model.

## Sources

- Lee, D., Ozdemir, O., and Guvenc, I. (2025). *Sionna ray tracing vs. real-world measurements: Signal strength comparison in rural scenarios with foliage*. [Dataset and processing scripts](https://doi.org/10.5061/dryad.ttdz08m8r).
- [Analysis and Prediction of Coverage and Channel Rank for UAV Networks in Rural Scenarios with Foliage](https://arxiv.org/abs/2502.10324).
- [Sionna RT](https://github.com/NVlabs/sionna-rt).

The code follows the repository's MIT license. External data retain their own terms; no dataset files are bundled.
