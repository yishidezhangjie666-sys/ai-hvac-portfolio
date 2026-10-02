#!/usr/bin/env python3
"""Compare fixed profile classes from electricity and chilled-water records."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from classify_profile import classify_features
from feature_extract import extract_features_from_csv


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = Path.home() / "workspace/goals/goal-4/hidden_files/data/chilledwater_cleaned.csv"
DEFAULT_PROFILES = ROOT / "output/building_profiles.csv"
DEFAULT_OUTPUT = ROOT / "output/chilledwater_crosscheck.csv"
DEFAULT_FIGURE = ROOT / "output/figures/power_vs_chilledwater.png"
CLASSES = ["A", "B", "C", "D"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--figure", type=Path, default=DEFAULT_FIGURE)
    args = parser.parse_args()

    power = pd.read_csv(args.profiles, dtype={"building_id": str})[["building_id", "profile_class"]]
    power = power.rename(columns={"profile_class": "power_class"})
    power["building_id"] = power["building_id"].astype(str)

    chilled_features, timestamp_rows, missing_cells = extract_features_from_csv(args.input)
    chilled_features["building_id"] = chilled_features["building_id"].astype(str)
    power_ids = set(power["building_id"])
    shared_ids = set(chilled_features["building_id"]) & power_ids
    if not shared_ids:
        raise ValueError("No building IDs overlap between electricity classifications and chilled-water data.")

    shared_features = chilled_features.loc[chilled_features["building_id"].isin(shared_ids)].copy()
    shared_features["chilledwater_class"] = classify_features(shared_features)
    power_lookup = power.set_index("building_id")["power_class"]
    crosscheck = shared_features[["building_id", "chilledwater_class"]].copy()
    crosscheck.insert(1, "power_class", crosscheck["building_id"].map(power_lookup))
    crosscheck["agree"] = crosscheck["power_class"] == crosscheck["chilledwater_class"]
    crosscheck = crosscheck[["building_id", "power_class", "chilledwater_class", "agree"]]
    crosscheck = crosscheck.sort_values("building_id", kind="stable").reset_index(drop=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    crosscheck.to_csv(args.output, index=False)

    agree_count = int(crosscheck["agree"].sum())
    total = len(crosscheck)
    agree_rate = agree_count / total
    table = pd.crosstab(crosscheck["power_class"], crosscheck["chilledwater_class"])
    table = table.reindex(index=CLASSES, columns=CLASSES, fill_value=0)
    power_counts = crosscheck["power_class"].value_counts().reindex(CLASSES, fill_value=0)
    chilled_counts = crosscheck["chilledwater_class"].value_counts().reindex(CLASSES, fill_value=0)

    x = range(len(CLASSES))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar([i - width / 2 for i in x], power_counts.values, width, label="Electricity", color="#4C78A8")
    ax.bar([i + width / 2 for i in x], chilled_counts.values, width, label="Chilled water", color="#F28E2B")
    ax.set(title="Power vs. Chilled Water Profile Class Distribution", xlabel="Profile class", ylabel="Number of shared buildings")
    ax.set_xticks(list(x), CLASSES)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.text(0.5, 0.01, f"Agreement rate: {agree_rate:.1%} ({agree_count}/{total} shared buildings)", ha="center")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    args.figure.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.figure, dpi=150)
    plt.close(fig)

    print(f"Shared buildings: {total}")
    print(f"Chilled-water timestamps: {timestamp_rows}; missing/coerced cells: {missing_cells}")
    print(f"Agree rate: {agree_rate:.6f} ({agree_count}/{total}, {agree_rate:.2%})")
    print("Class distribution on shared buildings:")
    print(pd.DataFrame({"power_class": power_counts, "chilledwater_class": chilled_counts}).to_string())
    print("Power class (rows) vs. chilled-water class (columns):")
    print(table.to_string())
    print(f"Wrote cross-check table to {args.output}")
    print(f"Wrote distribution figure to {args.figure}")


if __name__ == "__main__":
    main()
