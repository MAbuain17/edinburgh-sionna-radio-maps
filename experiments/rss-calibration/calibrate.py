"""Fit RSS corrections on an early time block; score a later block."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


FIELDS = ("link", "time_s", "predicted_dbm", "measured_dbm")


def read_csv(path):
    groups = {}
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must contain {FIELDS}")
        for line, row in enumerate(reader, 2):
            link = row["link"].strip()
            if not link:
                raise ValueError(f"Empty link on line {line}")
            values = [float(row[key]) for key in FIELDS[1:]]
            if not np.isfinite(values).all():
                raise ValueError(f"Non-finite value on line {line}")
            groups.setdefault(link, []).append(values)
    if not groups:
        raise ValueError("CSV contains no samples")
    arrays = {key: np.asarray(value) for key, value in groups.items()}
    for link, rows in arrays.items():
        if np.any(np.diff(rows[:, 0]) <= 0):
            raise ValueError(f"{link}: timestamps must increase strictly within each link")
    return arrays


def split_masks(time, train_fraction, gap_s):
    if not 0 < train_fraction < 1 or not np.isfinite(gap_s) or gap_s < 0:
        raise ValueError("Require 0 < train_fraction < 1 and finite gap_s >= 0")
    if len(time) < 5 or np.any(np.diff(time) <= 0):
        raise ValueError("Need at least five strictly increasing timestamps")
    # A fraction of elapsed time, not a fraction of rows.
    cutoff = time[0] + train_fraction * (time[-1] - time[0])
    train = time <= cutoff
    test = time > cutoff + gap_s
    if train.sum() < 3 or test.sum() < 2:
        raise ValueError("Split needs at least three training and two test samples")
    return train, test, float(cutoff)


def fit_models(predicted, measured):
    offset = float(np.mean(measured - predicted))
    centered = predicted - predicted.mean()
    variance = float(centered @ centered)
    models = {"uncorrected": (1.0, 0.0), "offset": (1.0, offset)}
    if variance <= len(predicted) * 1e-12:
        return models, "Affine fit omitted: training predictions have no usable variation."
    slope = float(centered @ (measured - measured.mean()) / variance)
    models["affine"] = (slope, float(measured.mean() - slope * predicted.mean()))
    return models, None


def metrics(predicted, measured):
    error = predicted - measured
    return {"n": len(error), "mae_db": float(np.abs(error).mean()),
            "rmse_db": float(np.sqrt(np.mean(error ** 2))),
            "bias_db": float(error.mean())}


def evaluate(groups, train_fraction=0.5, gap_s=10.0):
    report, predictions = {}, []
    for link, rows in sorted(groups.items()):
        time, predicted, measured = rows.T
        train, test, cutoff = split_masks(time, train_fraction, gap_s)
        models, warning = fit_models(predicted[train], measured[train])
        report[link] = {
            "train_n": int(train.sum()), "gap_n": int((~train & ~test).sum()),
            "test_n": int(test.sum()), "cutoff_s": cutoff,
            "test_start_s": float(time[test][0]), "warning": warning, "models": {},
        }
        for model, (slope, intercept) in models.items():
            estimate = slope * predicted + intercept
            report[link]["models"][model] = {
                "slope": slope, "intercept_db": intercept,
                "train": metrics(estimate[train], measured[train]),
                "test": metrics(estimate[test], measured[test]),
            }
            for i in np.flatnonzero(test):
                predictions.append({"link": link, "time_s": float(time[i]),
                                    "model": model, "predicted_dbm": float(estimate[i]),
                                    "measured_dbm": float(measured[i])})
    return report, predictions


def plot_results(groups, report, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(groups), 1, figsize=(10, 3.2 * len(groups)), squeeze=False)
    for ax, (link, rows) in zip(axes[:, 0], sorted(groups.items())):
        time, predicted, measured = rows.T
        item = report[link]
        ax.plot(time, measured, label="measured", color="black", linewidth=1)
        for name, model in item["models"].items():
            ax.plot(time, model["slope"] * predicted + model["intercept_db"],
                    label=name, alpha=0.75, linewidth=1)
        ax.axvspan(time[0], item["cutoff_s"], color="tab:blue", alpha=0.08, label="fit block")
        ax.axvspan(item["cutoff_s"], item["test_start_s"], color="grey", alpha=0.18, label="gap")
        ax.set(title=link, xlabel="Elapsed time (s)", ylabel="RSS (dBm)")
        ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--train-fraction", type=float, default=0.5)
    parser.add_argument("--gap-s", type=float, default=10.0)
    parser.add_argument("--data-kind", choices=["synthetic", "measured", "precalibrated"], required=True)
    parser.add_argument("--source", required=True, help="Dataset DOI, URL, or fixture description")
    args = parser.parse_args()
    groups = read_csv(args.input)
    report, predictions = evaluate(groups, args.train_fraction, args.gap_s)
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"data_kind": args.data_kind, "source": args.source,
                "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
                "numpy_version": np.__version__, "train_fraction": args.train_fraction,
                "gap_s": args.gap_s, "bias_convention": "prediction minus measurement",
                "links": report}
    (args.out / "metrics.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    with (args.out / "held_out.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(predictions[0]))
        writer.writeheader()
        writer.writerows(predictions)
    plot_results(groups, report, args.out / "rss.png")
    for link, item in report.items():
        for name, result in item["models"].items():
            print(f"{link:12} {name:12} test RMSE {result['test']['rmse_db']:.3f} dB")


if __name__ == "__main__":
    main()
