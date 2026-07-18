"""
Pivot Points and daily level calculations (Classic, Camarilla, Woodie, Fibonacci).
"""

from __future__ import annotations

import pandas as pd


def compute_daily_levels(prev_day_df: pd.DataFrame) -> dict[str, float]:
    """
    Compute daily levels from the previous day's trading session DataFrame.
    Expected columns: 'high', 'low', 'close', 'open'.
    """
    if prev_day_df.empty:
        return {}

    high = prev_day_df['high'].max()
    low = prev_day_df['low'].min()
    close = prev_day_df['close'].iloc[-1]
    open_p = prev_day_df['open'].iloc[0]

    # Classic/Standard Pivots
    pp = (high + low + close) / 3
    r1 = (2 * pp) - low
    s1 = (2 * pp) - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    r3 = high + 2 * (pp - low)
    s3 = low - 2 * (high - pp)

    # Camarilla Pivots
    range_val = high - low
    r1_cam = close + range_val * (1.1 / 12)
    s1_cam = close - range_val * (1.1 / 12)
    r2_cam = close + range_val * (1.1 / 6)
    s2_cam = close - range_val * (1.1 / 6)
    r3_cam = close + range_val * (1.1 / 4)
    s3_cam = close - range_val * (1.1 / 4)
    r4_cam = close + range_val * (1.1 / 2)
    s4_cam = close - range_val * (1.1 / 2)

    # Fibonacci Pivots
    r1_fib = pp + (range_val * 0.382)
    s1_fib = pp - (range_val * 0.382)
    r2_fib = pp + (range_val * 0.618)
    s2_fib = pp - (range_val * 0.618)
    r3_fib = pp + (range_val * 1.0)
    s3_fib = pp - (range_val * 1.0)

    # Woodie Pivots
    pp_wood = (high + low + 2 * open_p) / 4
    r1_wood = (2 * pp_wood) - low
    s1_wood = (2 * pp_wood) - high
    r2_wood = pp_wood + (high - low)
    s2_wood = pp_wood - (high - low)

    return {
        "pdh": high,
        "pdl": low,
        "pdc": close,
        "pp": pp,
        "r1": r1,
        "s1": s1,
        "r2": r2,
        "s2": s2,
        "r3": r3,
        "s3": s3,
        "cam_r1": r1_cam,
        "cam_s1": s1_cam,
        "cam_r2": r2_cam,
        "cam_s2": s2_cam,
        "cam_r3": r3_cam,
        "cam_s3": s3_cam,
        "cam_r4": r4_cam,
        "cam_s4": s4_cam,
        "fib_r1": r1_fib,
        "fib_s1": s1_fib,
        "fib_r2": r2_fib,
        "fib_s2": s2_fib,
        "fib_r3": r3_fib,
        "fib_s3": s3_fib,
        "wood_pp": pp_wood,
        "wood_r1": r1_wood,
        "wood_s1": s1_wood,
        "wood_r2": r2_wood,
        "wood_s2": s2_wood,
    }


def compute_gap_percent(today_open: float, prev_close: float) -> float:
    """Calculate the gap percentage of today's open relative to yesterday's close."""
    if prev_close == 0:
        return 0.0
    return ((today_open - prev_close) / prev_close) * 100
