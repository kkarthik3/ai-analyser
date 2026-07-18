"""
OI and volume-based feature generators.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def generate_oi_features(
    df: pd.DataFrame,
    pcr_history: pd.Series = None
) -> pd.DataFrame:
    """
    Generate Open Interest and volume features.
    Produces ~40 features.
    """
    features = pd.DataFrame(index=df.index)

    # Volume spikes
    volume = df['volume']
    vol_mean_20 = volume.rolling(20).mean().replace(0, 1.0)
    features['volume_zscore'] = (volume - vol_mean_20) / volume.rolling(20).std().replace(0, 1.0)
    features['volume_spike_ratio'] = volume / vol_mean_20

    # Open Interest Features
    if 'oi' in df.columns:
        oi = df['oi']
        features['oi'] = oi
        features['oi_change_1m'] = oi.diff(1)
        features['oi_change_5m'] = oi.diff(5)
        features['oi_change_pct_1m'] = oi.pct_change(1)
        features['oi_change_pct_5m'] = oi.pct_change(5)

        # OI Momentum
        features['oi_momentum_10m'] = oi.diff(10) / 10.0
    else:
        features['oi'] = 0.0
        features['oi_change_1m'] = 0.0
        features['oi_change_pct_1m'] = 0.0
        features['oi_momentum_10m'] = 0.0

    # Put-Call Ratio features (if PCR series is provided)
    if pcr_history is not None and not pcr_history.empty:
        features['pcr'] = pcr_history
        features['pcr_change_5m'] = pcr_history.diff(5)
        features['pcr_ma_10'] = pcr_history.rolling(10).mean()
        features['pcr_zscore'] = (pcr_history - pcr_history.rolling(20).mean()) / pcr_history.rolling(20).std().replace(0, 1.0)
    else:
        features['pcr'] = 0.0
        features['pcr_change_5m'] = 0.0
        features['pcr_ma_10'] = 0.0
        features['pcr_zscore'] = 0.0

    return features.fillna(0.0)
