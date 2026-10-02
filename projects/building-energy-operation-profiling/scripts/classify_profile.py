#!/usr/bin/env python3
"""Apply the documented deterministic profile rules to features.csv."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "output/features.csv"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "output/building_profiles.csv"

# Fixed rule thresholds and precedence (A, then B, then C, otherwise D):
# A Office: weekday_mean >= 1.5 * weekend_mean and peak_hour in [8, 18].
# B Stable operating pattern: 0.8 <= day_night_ratio <= 1.25 and
#   std_value / mean_value < 0.3; this rule describes a low-variation load curve.
# C Nighttime high-load profile: night_mean >= 0.7 * day_mean (equivalently day/night <= 1/0.7),
#   OR weekend_mean >= 0.8 * weekday_mean with peak_hour outside [8, 18].
#   Day and night means use hours 08:00–18:00 and 00:00–06:00 inclusive.
# D Other: no earlier rule matches. Missing comparisons are treated as false.


def classify_features(features: pd.DataFrame) -> pd.Series:
    """Apply the shared A→B→C→D fixed rules and return class letters."""
    required = {"building_id", "weekday_mean", "weekend_mean", "day_night_ratio", "peak_hour", "mean_value", "std_value"}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"Missing required feature columns: {sorted(missing)}")

    weekday = features["weekday_mean"]
    weekend = features["weekend_mean"]
    ratio = features["day_night_ratio"]
    peak = features["peak_hour"]
    mean = features["mean_value"]
    std = features["std_value"]
    with np.errstate(divide="ignore", invalid="ignore"):
        cv = std / mean

    is_office = (weekday >= 1.5 * weekend) & peak.between(8, 18, inclusive="both")
    is_continuous = ratio.between(0.8, 1.25, inclusive="both") & (cv < 0.3)
    # The first condition is derived from the day/night ratio. A zero night
    # mean yields an infinite ratio (and does not meet the high-night rule).
    high_night = ratio <= (1.0 / 0.7)
    nonwork_high = (weekend >= 0.8 * weekday) & ~peak.between(8, 18, inclusive="both")
    is_night = high_night | nonwork_high

    labels = np.full(len(features), "D", dtype=object)
    labels[is_night.fillna(False).to_numpy()] = "C"
    labels[is_continuous.fillna(False).to_numpy()] = "B"
    labels[is_office.fillna(False).to_numpy()] = "A"
    return pd.Series(labels, index=features.index, name="profile_class")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    features = pd.read_csv(args.input)
    labels = classify_features(features)
    out = features.assign(profile_class=labels)[
        ["building_id", "profile_class", "weekday_mean", "weekend_mean", "day_night_ratio", "peak_hour"]
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, float_format="%.8g")
    print(f"Wrote {len(out)} classifications to {args.output}")
    print(out["profile_class"].value_counts().reindex(["A", "B", "C", "D"], fill_value=0).to_string())


if __name__ == "__main__":
    main()
