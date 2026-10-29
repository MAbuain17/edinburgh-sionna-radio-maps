"""Convert Dryad D3 MAT arrays to CSV; the measurements are already calibrated."""

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy.io import loadmat


def convert(path, output, channel):
    data = loadmat(path, simplify_cells=True)
    towers = np.asarray(data["LWs"], dtype=object).reshape(-1)
    rows = []
    for index, tower in enumerate(towers, 1):
        arrays = [np.asarray(tower[key], dtype=float).reshape(-1) for key in
                  ["time_reference", "RSS_arr_plot", f"RSS{channel}_offset"]]
        if len({len(array) for array in arrays}) != 1:
            raise ValueError(f"LW{index}: array lengths differ; inspect alignment before importing")
        if not all(np.isfinite(array).all() for array in arrays):
            raise ValueError(f"LW{index}: non-finite data; inspect before importing")
        rows.extend((f"LW{index}_ch{channel}", *sample) for sample in zip(*arrays))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["link", "time_s", "predicted_dbm", "measured_dbm"])
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mat_file", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--channel", type=int, choices=[1, 2], default=1)
    args = parser.parse_args()
    convert(args.mat_file, args.output, args.channel)
