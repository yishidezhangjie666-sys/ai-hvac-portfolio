#!/usr/bin/env python3
"""Extract per-building hourly features from a wide CSV in chunks."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_DATA = Path.home() / "workspace/goals/goal-4/hidden_files/data/electricity_cleaned.csv"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "output/features.csv"
CHUNK_ROWS = 512


def extract_features_from_csv(input_path: Path) -> tuple[pd.DataFrame, int, int]:
    """Return the standard feature table, timestamp row count, and missing-cell count."""
    columns = pd.read_csv(input_path, nrows=0).columns.tolist()
    if not columns or columns[0] != "timestamp":
        raise ValueError("Expected the first CSV column to be 'timestamp'.")
    building_ids = columns[1:]
    if not building_ids:
        raise ValueError("No building columns found in the CSV.")

    n = len(building_ids)
    total_sum = np.zeros(n, dtype=np.float64)
    total_sumsq = np.zeros(n, dtype=np.float64)
    total_count = np.zeros(n, dtype=np.int64)
    maximum = np.full(n, -np.inf, dtype=np.float64)
    period_sum = {"weekday": np.zeros(n), "weekend": np.zeros(n), "day": np.zeros(n), "night": np.zeros(n)}
    period_count = {key: np.zeros(n, dtype=np.int64) for key in period_sum}
    hour_sum = np.zeros((24, n), dtype=np.float64)
    hour_count = np.zeros((24, n), dtype=np.int64)
    missing_cells = 0
    timestamp_rows = 0

    for chunk in pd.read_csv(input_path, chunksize=CHUNK_ROWS):
        timestamps = pd.to_datetime(chunk.pop("timestamp"), errors="coerce")
        values = chunk.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float64)
        if values.shape[1] != n:
            raise ValueError("Building columns changed while reading the CSV.")
        missing_cells += int(np.isnan(values).sum())
        timestamp_rows += len(values)
        valid_times = ~timestamps.isna().to_numpy()
        values[~valid_times, :] = np.nan

        valid = np.isfinite(values)
        safe_values = np.where(valid, values, 0.0)
        total_sum += safe_values.sum(axis=0)
        total_sumsq += (safe_values * safe_values).sum(axis=0)
        total_count += valid.sum(axis=0)
        chunk_max = np.max(np.where(valid, values, -np.inf), axis=0)
        maximum = np.maximum(maximum, chunk_max)

        ts = timestamps
        weekday_mask = (ts.dt.dayofweek < 5).to_numpy() & valid_times
        weekend_mask = (ts.dt.dayofweek >= 5).to_numpy() & valid_times
        # Inclusive clock-hour windows: daytime 08:00–18:00; nighttime 00:00–06:00.
        day_mask = ts.dt.hour.between(8, 18, inclusive="both").to_numpy() & valid_times
        night_mask = ts.dt.hour.between(0, 6, inclusive="both").to_numpy() & valid_times
        for key, mask in (("weekday", weekday_mask), ("weekend", weekend_mask), ("day", day_mask), ("night", night_mask)):
            selected = safe_values[mask]
            period_sum[key] += selected.sum(axis=0)
            period_count[key] += valid[mask].sum(axis=0)

        hours = ts.dt.hour.to_numpy()
        for hour in range(24):
            mask = (hours == hour) & valid_times
            if mask.any():
                hour_sum[hour] += safe_values[mask].sum(axis=0)
                hour_count[hour] += valid[mask].sum(axis=0)

    def mean_for(key: str) -> np.ndarray:
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.divide(period_sum[key], period_count[key], out=np.full(n, np.nan), where=period_count[key] > 0)

    weekday_mean = mean_for("weekday")
    weekend_mean = mean_for("weekend")
    day_mean = mean_for("day")
    night_mean = mean_for("night")
    with np.errstate(divide="ignore", invalid="ignore"):
        day_night_ratio = np.divide(day_mean, night_mean, out=np.full(n, np.nan), where=night_mean != 0)
        # Positive daytime load over zero night load has an infinite ratio; 0/0 is undefined.
        day_night_ratio[(night_mean == 0) & (day_mean > 0)] = np.inf
        mean_value = np.divide(total_sum, total_count, out=np.full(n, np.nan), where=total_count > 0)
        variance = np.divide(total_sumsq - total_sum * mean_value, total_count - 1,
                             out=np.full(n, np.nan), where=total_count > 1)
    std_value = np.sqrt(np.maximum(variance, 0.0))
    maximum[~np.isfinite(maximum)] = np.nan

    hourly_mean = np.divide(hour_sum, hour_count, out=np.full_like(hour_sum, np.nan), where=hour_count > 0)
    peak_hour = np.full(n, np.nan)
    peak_valley_diff = np.full(n, np.nan)
    for j in range(n):
        curve = hourly_mean[:, j]
        observed = np.isfinite(curve)
        if observed.any():
            peak_hour[j] = int(np.nanargmax(curve))
            peak_valley_diff[j] = float(np.nanmax(curve) - np.nanmin(curve))

    features = pd.DataFrame({
        "building_id": building_ids,
        "weekday_mean": weekday_mean,
        "weekend_mean": weekend_mean,
        "day_night_ratio": day_night_ratio,
        "peak_hour": peak_hour,
        "max_value": maximum,
        "mean_value": mean_value,
        "std_value": std_value,
        "peak_valley_diff": peak_valley_diff,
    })
    return features, timestamp_rows, missing_cells


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    features, timestamp_rows, missing_cells = extract_features_from_csv(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(args.output, index=False, float_format="%.8g")
    print(f"Wrote {len(features)} buildings to {args.output}")
    print(f"Input timestamp rows: {timestamp_rows}; missing/coerced cells: {missing_cells}")
    print(f"Buildings with all-period mean available: {int(features['mean_value'].notna().sum())}")


if __name__ == "__main__":
    main()
