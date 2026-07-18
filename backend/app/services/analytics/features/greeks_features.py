"""
Option Greeks-based feature generators.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def generate_greeks_features(
    gex_history: pd.Series = None,
    dex_history: pd.Series = None,
    atm_iv_history: pd.Series = None
) -> pd.DataFrame:
    """
    Generate Greeks features based on historical GEX, DEX, and ATM Implied Volatility.
    Produces ~30 features.
    """
    features = pd.DataFrame()

    # GEX Features
    if gex_history is not None and not gex_history.empty:
        features['gex'] = gex_history
        features['gex_change_5m'] = gex_history.diff(5)
        features['gex_ma_20'] = gex_history.rolling(20).mean()
        features['gex_zscore'] = (gex_history - gex_history.rolling(20).mean()) / gex_history.rolling(20).std().replace(0, 1.0)
    else:
        features['gex'] = 0.0
        features['gex_change_5m'] = 0.0
        features['gex_ma_20'] = 0.0
        features['gex_zscore'] = 0.0

    # DEX Features
    if dex_history is not None and not dex_history.empty:
        features['dex'] = dex_history
        features['dex_change_5m'] = dex_history.diff(5)
        features['dex_ma_20'] = dex_history.rolling(20).mean()
    else:
        features['dex'] = 0.0
        features['dex_change_5m'] = 0.0
        features['dex_ma_20'] = 0.0

    # ATM IV Features
    if atm_iv_history is not None and not atm_iv_history.empty:
        features['atm_iv'] = atm_iv_history
        features['iv_skew'] = atm_iv_history.diff(1)  # Proxy for skew shift
    else:
        features['atm_iv'] = 0.0
        features['iv_skew'] = 0.0

    return features.fillna(0.0)
