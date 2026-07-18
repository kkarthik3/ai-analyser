"""
Price and momentum-based feature generators.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from app.services.analytics.technical.indicators import compute_ema
from app.services.analytics.technical.vwap import compute_vwap


def generate_price_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate price, return, trend, and indicator distance features.
    Produces ~50 features.
    """
    features = pd.DataFrame(index=df.index)
    close = df['close']

    # Returns and Log Returns
    features['return_1m'] = close.pct_change(1)
    features['return_5m'] = close.pct_change(5)
    features['return_15m'] = close.pct_change(15)
    features['return_1h'] = close.pct_change(60)

    features['log_return_1m'] = np.log(close / close.shift(1))
    features['log_return_5m'] = np.log(close / close.shift(5))

    # Realized Volatility proxy (rolling standard deviation of log returns)
    features['realized_vol_5m'] = features['log_return_1m'].rolling(5).std()
    features['realized_vol_15m'] = features['log_return_1m'].rolling(15).std()
    features['realized_vol_1h'] = features['log_return_1m'].rolling(60).std()

    # EMA Distances
    for period in [9, 20, 50, 200]:
        ema = compute_ema(close, period)
        features[f'ema_{period}'] = ema
        features[f'dist_ema_{period}'] = (close - ema) / ema

    # VWAP Distance
    vwap = compute_vwap(df)
    features['vwap'] = vwap
    features['dist_vwap'] = (close - vwap) / vwap

    # Momentum oscillators (ROC)
    for period in [5, 10, 20, 50]:
        features[f'roc_{period}'] = close.pct_change(period) * 100

    # Min/Max ranges (Breakout flags)
    for period in [10, 20, 50]:
        high_period = df['high'].rolling(period).max()
        low_period = df['low'].rolling(period).min()
        features[f'dist_high_{period}'] = (df['high'] - high_period.shift(1)) / close
        features[f'dist_low_{period}'] = (df['low'] - low_period.shift(1)) / close

    # Bollinger Bands Position
    basis = close.rolling(20).mean()
    std = close.rolling(20).std().replace(0, 1e-5)
    features['bollinger_pct'] = (close - (basis - 2 * std)) / (4 * std)

    return features.fillna(0.0)
