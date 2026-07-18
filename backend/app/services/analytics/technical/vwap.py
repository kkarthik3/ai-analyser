"""
VWAP (Volume Weighted Average Price) and Anchored VWAP calculations.
"""

from __future__ import annotations

import pandas as pd


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Compute Intraday VWAP.
    Expects a DataFrame with 'high', 'low', 'close', 'volume', and a DatetimeIndex.
    Resets at the start of each trading day.
    """
    # Calculate Typical Price
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    pv = typical_price * df['volume']

    # Group by date (intraday reset)
    date_group = df.index.normalize()

    cum_pv = pv.groupby(date_group).cumsum()
    cum_vol = df['volume'].groupby(date_group).cumsum()

    vwap = cum_pv / cum_vol.replace(0, 1.0)
    return vwap


def compute_anchored_vwap(df: pd.DataFrame, anchor_time: pd.Timestamp) -> pd.Series:
    """
    Compute Anchored VWAP.
    Resets/starts accumulating from the specified anchor_time.
    """
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    pv = typical_price * df['volume']

    # Create mask for values after anchor time
    mask = df.index >= anchor_time

    # Calculate cumulative sums only for rows matching the mask
    cum_pv = pv[mask].cumsum()
    cum_vol = df['volume'][mask].cumsum()

    avwap = pd.Series(index=df.index, dtype=float)
    avwap[mask] = cum_pv / cum_vol.replace(0, 1.0)

    # For pre-anchor values, set as NaN or backfill
    return avwap
