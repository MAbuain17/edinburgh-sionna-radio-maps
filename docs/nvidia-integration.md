# NVIDIA large-radio-maps integration

This project adapts the geographic scene and terrain-following measurement approach in [NVIDIA's sionna-large-radio-maps](https://github.com/NVlabs/sionna-large-radio-maps). The included campus results were computed by `run_study.py` with Sionna RT 2.2.0. The export targets the inspected upstream implementation, which pins Sionna RT 1.2.1; execution through that upstream pipeline remains a separate verification step.

## Export layout

```text
lrm_export/
  transmitters.csv
  kings_buildings/
    0/
      bboxes.npz
      scene.xml
      meshes/
```

Regenerate the export with:

```bash
python export_lrm.py
```

The exporter translates the scene from the study's local frame to the upstream tile's southwest origin and restores the source terrain elevation reference. The transmitter CSV supplies `lat`, `lon`, `elevation` and `building`, matching `BaseStationDB.from_file`. Upstream adds 2 m to rooftop elevations; the exported values account for this offset to recover the intended antenna altitude.

## Run with upstream dependencies

Clone the upstream repository and install its dependencies in a separate environment. From that checkout:

```bash
python scripts/compute_radio_maps.py \
  -s /absolute/path/edinburgh-sionna-radio-maps/lrm_export/kings_buildings \
  -t /absolute/path/edinburgh-sionna-radio-maps/lrm_export/transmitters.csv \
  -o /absolute/path/lrm_results \
  --samples 500000000
```

The upstream defaults use a 2-by-16 TR38901 antenna array, maximum reflection depth 5, seeded site azimuths and maximum path gain over sites. Its memory-aware scheduling and SLURM examples support larger GPU workloads. Verify the frequency, antenna, elevation offsets, sample allocation and solver settings when comparing that configuration with this campus study.

The campus runner retains individual site gains so that RSS, SINR and site association can be recomputed. Upstream's maximum-over-sites output supports coverage analysis; interference calculations require retaining the individual gains.

