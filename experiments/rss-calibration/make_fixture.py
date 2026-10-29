"""Generate artificial RSS traces for checking the pipeline, not scientific claims."""

import argparse
import csv
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rng = np.random.default_rng(17)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["link", "time_s", "predicted_dbm", "measured_dbm"])
        for link in ["stable_offset", "changing_offset"]:
            for time in range(241):
                predicted = -70 - 9 * np.sin(time / 21) - 0.025 * time
                offset = 6 if link == "stable_offset" or time <= 120 else -6
                measured = predicted + offset + rng.normal(0, 1)
                writer.writerow([link, time, predicted, measured])


if __name__ == "__main__":
    main()
