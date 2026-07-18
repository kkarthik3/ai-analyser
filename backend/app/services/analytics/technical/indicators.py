"""
Technical analysis indicators engine.

Computes standard technical indicators: EMA, RSI, ATR, ADX, MACD, Supertrend,
Bollinger Bands, Keltner Channels, and Donchian Channels using Pandas and NumPy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ema(series: pd.Series, period: int) -> pd.Series:
    """Compute Exponential Moving Average (EMA)."""
    return series.ewm(span=period, adjust=False).mean()


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute Average True Range (ATR)."""
    high = df['high']
    low = df['low']
    close = df['close']

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    return atr


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Compute Average Directional Index (ADX) along with +DI and -DI."""
    high = df['high']
    low = df['low']
    close = df['close']

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    up_move = high.diff()
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr_smoothed = pd.Series(tr).ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm).ewm(alpha=1 / period, adjust=False).mean() / tr_smoothed.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1 / period, adjust=False).mean() / tr_smoothed.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()

    return pd.DataFrame({
        'adx': adx.fillna(0),
        'plus_di': plus_di.fillna(0),
        'minus_di': minus_di.fillna(0)
    }, index=df.index)


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Compute Moving Average Convergence Divergence (MACD)."""
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    histogram = macd_line - signal_line

    return pd.DataFrame({
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    })


def compute_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    """Compute Supertrend indicator."""
    high = df['high']
    low = df['low']
    close = df['close']

    atr = compute_atr(df, period)
    hl2 = (high + low) / 2

    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)

    # Initialize trend and bands
    supertrend = pd.Series(0.0, index=df.index)
    direction = pd.Series(1, index=df.index)  # 1 for bull, -1 for bear

    final_upper_band = upper_band.copy()
    final_lower_band = lower_band.copy()

    for i in range(1, len(df)):
        # Upper band adjustment
        if upper_band.iloc[i] < final_upper_band.iloc[i-1] or close.iloc[i-1] > final_upper_band.iloc[i-1]:
            final_upper_band.iloc[i] = upper_band.iloc[i]
        else:
            final_upper_band.iloc[i] = final_upper_band.iloc[i-1]

        # Lower band adjustment
        if lower_band.iloc[i] > final_lower_band.iloc[i-1] or close.iloc[i-1] < final_lower_band.iloc[i-1]:
            final_lower_band.iloc[i] = lower_band.iloc[i]
        else:
            final_lower_band.iloc[i] = final_lower_band.iloc[i-1]

        # Determine direction
        if close.iloc[i] > final_upper_band.iloc[i-1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < final_lower_band.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]

        # Final supertrend line
        if direction.iloc[i] == 1:
            supertrend.iloc[i] = final_lower_band.iloc[i]
        else:
            supertrend.iloc[i] = final_upper_band.iloc[i]

    return pd.DataFrame({
        'supertrend': supertrend,
        'direction': direction
    })


def compute_bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Compute Bollinger Bands (basis, upper, lower)."""
    basis = series.rolling(window=period).mean()
    std = series.rolling(window=period).shadow = series.rolling(window=period).std()
    upper = basis + (num_std * std)
    lower = basis - (num_std * std)
    return pd.DataFrame({
        'basis': basis,
        'upper': upper,
        'lower': lower
    })


def compute_keltner_channel(df: pd.DataFrame, period: int = 20, multiplier: float = 2.0) -> pd.DataFrame:
    """Compute Keltner Channels (basis, upper, lower)."""
    close = df['close']
    atr = compute_atr(df, period)
    basis = compute_ema(close, period)
    upper = basis + (multiplier * atr)
    lower = basis - (multiplier * atr)

    return pd.DataFrame({
        'basis': basis,
        'upper': upper,
        'lower': lower
    })


def compute_donchian_channel(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Compute Donchian Channels (basis, upper, lower)."""
    high = df['high']
    low = df['low']

    upper = high.rolling(window=period).max()
    lower = low.rolling(window=period).min()
    basis = (upper + lower) / 2

    return pd.DataFrame({
        'basis': basis,
        'upper': upper,
        'lower': lower
    })
