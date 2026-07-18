"""
Market Structure and Smart Money Concepts (SMC) engine.

Detects swing points (HH, HL, LH, LL), breakouts, breakdowns,
BOS (Break of Structure), CHOCH (Change of Character), FVG (Fair Value Gaps),
Order Blocks (OB), and liquidity sweeps.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def detect_swings(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Detect swing highs and swing lows.
    A swing high is the highest high in a window of size (2*window + 1).
    """
    highs = df['high']
    lows = df['low']

    swing_highs = highs.rolling(window=2*window+1, center=True).max() == highs
    swing_lows = lows.rolling(window=2*window+1, center=True).min() == lows

    result = pd.DataFrame(index=df.index)
    result['swing_high'] = np.where(swing_highs, highs, np.nan)
    result['swing_low'] = np.where(swing_lows, lows, np.nan)

    # Label HH/LH/HL/LL
    last_sh = None
    last_sl = None

    result['swing_type'] = ""

    for idx, row in result.iterrows():
        sh = row['swing_high']
        sl = row['swing_low']

        if not np.isnan(sh):
            if last_sh is not None:
                if sh > last_sh:
                    result.at[idx, 'swing_type'] = "HH"
                else:
                    result.at[idx, 'swing_type'] = "LH"
            last_sh = sh

        if not np.isnan(sl):
            if last_sl is not None:
                if sl < last_sl:
                    result.at[idx, 'swing_type'] = "LL"
                else:
                    result.at[idx, 'swing_type'] = "HL"
            last_sl = sl

    return result


def detect_fvg(df: pd.DataFrame) -> list[dict[str, any]]:
    """
    Detect Fair Value Gaps (FVG) in a 3-candle sequence.
    Bullish FVG: Low of candle 3 > High of candle 1.
    Bearish FVG: High of candle 3 < Low of candle 1.
    """
    fvgs = []
    if len(df) < 3:
        return fvgs

    highs = df['high'].values
    lows = df['low'].values
    times = df.index

    for i in range(2, len(df)):
        # Bullish FVG
        if lows[i] > highs[i-2]:
            fvgs.append({
                "time": times[i],
                "type": "BULLISH_FVG",
                "top": float(lows[i]),
                "bottom": float(highs[i-2]),
                "mitigated": False
            })
        # Bearish FVG
        elif highs[i] < lows[i-2]:
            fvgs.append({
                "time": times[i],
                "type": "BEARISH_FVG",
                "top": float(lows[i-2]),
                "bottom": float(highs[i]),
                "mitigated": False
            })

    return fvgs


def detect_bos_choch(
    df: pd.DataFrame,
    swings: pd.DataFrame
) -> list[dict[str, any]]:
    """
    Detect Break of Structure (BOS) and Change of Character (CHOCH).
    BOS is a continuation of the trend, breaking the latest swing high (up) or swing low (down).
    CHOCH is the trend reversal, breaking the opposite swing point.
    """
    events = []
    if df.empty or swings.empty:
        return events

    closes = df['close'].values
    times = df.index

    last_high_val = None
    last_low_val = None
    trend = 0  # 1 for up, -1 for down, 0 for unknown

    for i in range(len(df)):
        current_close = closes[i]
        current_time = times[i]

        sh = swings['swing_high'].iloc[i]
        sl = swings['swing_low'].iloc[i]

        if not np.isnan(sh):
            last_high_val = sh
        if not np.isnan(sl):
            last_low_val = sl

        # Bullish Breakout (BOS or CHOCH)
        if last_high_val is not None and current_close > last_high_val:
            if trend == -1:
                events.append({"time": current_time, "type": "CHOCH_BULLISH", "level": float(last_high_val)})
                trend = 1
            elif trend == 1 or trend == 0:
                events.append({"time": current_time, "type": "BOS_BULLISH", "level": float(last_high_val)})
                trend = 1
            last_high_val = None  # Reset broken level

        # Bearish Breakdown (BOS or CHOCH)
        elif last_low_val is not None and current_close < last_low_val:
            if trend == 1:
                events.append({"time": current_time, "type": "CHOCH_BEARISH", "level": float(last_low_val)})
                trend = -1
            elif trend == -1 or trend == 0:
                events.append({"time": current_time, "type": "BOS_BEARISH", "level": float(last_low_val)})
                trend = -1
            last_low_val = None

    return events


def detect_order_blocks(
    df: pd.DataFrame,
    events: list[dict[str, any]]
) -> list[dict[str, any]]:
    """
    Detect Order Blocks (OB).
    An Order Block is the last opposite-colored candle before a BOS/CHOCH break.
    """
    order_blocks = []
    if df.empty:
        return order_blocks

    opens = df['open'].values
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    times = df.index

    # Index mapping for quick lookup
    time_to_idx = {t: i for i, t in enumerate(times)}

    for ev in events:
        ev_time = ev["time"]
        ev_type = ev["type"]

        if ev_time not in time_to_idx:
            continue

        idx = time_to_idx[ev_time]

        # Look backward to find the last opposite candle
        if "BULLISH" in ev_type:
            # Find last bearish candle
            for j in range(idx - 1, max(0, idx - 15), -1):
                if closes[j] < opens[j]:
                    order_blocks.append({
                        "time": times[j],
                        "type": "BULLISH_OB",
                        "top": float(highs[j]),
                        "bottom": float(lows[j]),
                        "mitigated": False
                    })
                    break
        elif "BEARISH" in ev_type:
            # Find last bullish candle
            for j in range(idx - 1, max(0, idx - 15), -1):
                if closes[j] > opens[j]:
                    order_blocks.append({
                        "time": times[j],
                        "type": "BEARISH_OB",
                        "top": float(highs[j]),
                        "bottom": float(lows[j]),
                        "mitigated": False
                    })
                    break

    return order_blocks


def detect_liquidity_sweeps(df: pd.DataFrame, swings: pd.DataFrame) -> list[dict[str, any]]:
    """
    Detect liquidity sweeps.
    A sweep is when price wicks past a swing high/low but closes inside.
    """
    sweeps = []
    if df.empty or swings.empty:
        return sweeps

    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    times = df.index

    # Find historical swings
    swing_highs = swings['swing_high'].dropna()
    swing_lows = swings['swing_low'].dropna()

    for i in range(len(df)):
        curr_high = highs[i]
        curr_low = lows[i]
        curr_close = closes[i]
        curr_time = times[i]

        # Bullish Liquidity Sweep (price goes below key low, closes above)
        relevant_lows = swing_lows[swing_lows.index < curr_time]
        if not relevant_lows.empty:
            key_low = relevant_lows.iloc[-1]
            if curr_low < key_low and curr_close > key_low:
                sweeps.append({
                    "time": curr_time,
                    "type": "LIQUIDITY_SWEEP_BULLISH",
                    "level": float(key_low),
                    "sweep_depth": float(key_low - curr_low)
                })

        # Bearish Liquidity Sweep (price goes above key high, closes below)
        relevant_highs = swing_highs[swing_highs.index < curr_time]
        if not relevant_highs.empty:
            key_high = relevant_highs.iloc[-1]
            if curr_high > key_high and curr_close < key_high:
                sweeps.append({
                    "time": curr_time,
                    "type": "LIQUIDITY_SWEEP_BEARISH",
                    "level": float(key_high),
                    "sweep_depth": float(curr_high - key_high)
                })

    return sweeps
