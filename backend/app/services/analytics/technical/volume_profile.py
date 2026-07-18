"""
Volume Profile calculations.

Computes Point of Control (POC), Value Area High (VAH), Value Area Low (VAL),
and price concentration histograms for market volume profiling.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_volume_profile(
    df: pd.DataFrame,
    bins_count: int = 24,
    value_area_pct: float = 0.70
) -> dict[str, any]:
    """
    Compute Volume Profile.
    Returns the distribution of volume across price bins,
    Point of Control (POC), Value Area High (VAH), and Value Area Low (VAL).
    """
    if df.empty:
        return {"poc": None, "vah": None, "val": None, "profile": []}

    high = df['high'].max()
    low = df['low'].min()

    if high == low:
        return {"poc": high, "vah": high, "val": low, "profile": []}

    # Generate price bins
    price_bins = np.linspace(low, high, bins_count + 1)
    bin_centers = (price_bins[:-1] + price_bins[1:]) / 2

    # Map prices to bins and aggregate volume
    typical_prices = (df['high'] + df['low'] + df['close']) / 3
    volumes = df['volume']

    # Digitize typical prices into bins
    bin_idx = np.clip(np.digitize(typical_prices, price_bins) - 1, 0, bins_count - 1)

    # Accumulate volume per bin
    bin_volumes = np.zeros(bins_count)
    for idx, vol in zip(bin_idx, volumes):
        bin_volumes[idx] += vol

    # Point of Control (POC)
    poc_idx = np.argmax(bin_volumes)
    poc = bin_centers[poc_idx]

    # Value Area calculations (default 70% of total volume centered around POC)
    total_volume = bin_volumes.sum()
    target_value_volume = total_volume * value_area_pct

    # Expand from POC index outwards to capture value_area_pct of volume
    low_idx = poc_idx
    high_idx = poc_idx
    current_volume = bin_volumes[poc_idx]

    while current_volume < target_value_volume and (low_idx > 0 or high_idx < bins_count - 1):
        prev_vol = bin_volumes[low_idx - 1] if low_idx > 0 else 0
        next_vol = bin_volumes[high_idx + 1] if high_idx < bins_count - 1 else 0

        if prev_vol >= next_vol:
            low_idx -= 1
            current_volume += prev_vol
        else:
            high_idx += 1
            current_volume += next_vol

    val = price_bins[low_idx]
    vah = price_bins[high_idx + 1]

    profile = [
        {"price": float(center), "volume": float(vol)}
        for center, vol in zip(bin_centers, bin_volumes)
    ]

    return {
        "poc": float(poc),
        "vah": float(vah),
        "val": float(val),
        "profile": profile
    }
