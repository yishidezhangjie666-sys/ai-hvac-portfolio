#!/usr/bin/env python3
"""Plot observed electricity daily mean profiles and class counts."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = Path.home() / "workspace/goals/goal-4/hidden_files/data/electricity_cleaned.csv"
DEFAULT_PROFILES = ROOT / "output/building_profiles.csv"
DEFAULT_FIGURES = ROOT / "output/figures"
CHUNK_ROWS = 512


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--figures", type=Path, default=DEFAULT_FIGURES)
    args = parser.parse_args()
    profiles = pd.read_csv(args.profiles)
    args.figures.mkdir(parents=True, exist_ok=True)

    # Pick the lowest building_id in each class for reproducible examples.
    # This is a deterministic selection, not a claim that it is statistically
    # representative of the entire class.
    chosen = {}
    for label in ("A", "B", "C"):
        ids = sorted(profiles.loc[profiles.profile_class == label, "building_id"].astype(str))
        if ids:
            chosen[label] = ids[0]
        else:
            print(f"No class {label} buildings; corresponding profile figure cannot be generated.")
    wanted = set(chosen.values())
    hourly_sum = {building: np.zeros(24, dtype=np.float64) for building in wanted}
    hourly_count = {building: np.zeros(24, dtype=np.int64) for building in wanted}
    header = pd.read_csv(args.input, nrows=0).columns.tolist()
    available = wanted.intersection(header[1:])
    if available != wanted:
        raise ValueError(f"Selected buildings missing from electricity input: {sorted(wanted - available)}")

    for chunk in pd.read_csv(args.input, usecols=["timestamp", *sorted(wanted)], chunksize=CHUNK_ROWS):
        timestamps = pd.to_datetime(chunk.pop("timestamp"), errors="coerce")
        hours = timestamps.dt.hour.to_numpy()
        values = chunk.apply(pd.to_numeric, errors="coerce")
        for building in wanted:
            series = values[building].to_numpy(dtype=np.float64)
            for hour in range(24):
                mask = (hours == hour) & np.isfinite(series)
                if mask.any():
                    hourly_sum[building][hour] += series[mask].sum()
                    hourly_count[building][hour] += int(mask.sum())

    titles = {"A": "Office profile", "B": "Stable operating pattern profile", "C": "Nighttime high-load profile"}
    filenames = {"A": "office_profile.png", "B": "continuous_profile.png", "C": "night_profile.png"}
    for label, building in chosen.items():
        counts = hourly_count[building]
        curve = np.divide(hourly_sum[building], counts, out=np.full(24, np.nan), where=counts > 0)
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(np.arange(24), curve, marker="o", linewidth=1.8)
        ax.set(title=f"{titles[label]} - sample building (building {building})", xlabel="Hour of day", ylabel="Mean electricity load")
        ax.set_xticks(range(0, 24, 2))
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(args.figures / filenames[label], dpi=150)
        plt.close(fig)

    counts = profiles["profile_class"].value_counts().reindex(["A", "B", "C", "D"], fill_value=0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(counts.index, counts.values, color=["#4C78A8", "#59A14F", "#E15759", "#9C9C9C"])
    ax.set(title="Building profile distribution", xlabel="Profile class", ylabel="Number of buildings")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.figures / "profile_distribution.png", dpi=150)
    plt.close(fig)
    print(f"Figures written to {args.figures}")
    print("Selected buildings: " + ", ".join(f"{label}={building}" for label, building in chosen.items()))


if __name__ == "__main__":
    main()
