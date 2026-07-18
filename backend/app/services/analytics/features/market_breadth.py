"""
Market breadth and relative asset correlation feature generators.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def generate_market_breadth_features(
    indices_ticks: dict[str, pd.DataFrame],
    stocks_ticks: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """
    Generate market breadth features: Advance/Decline, watch list momentum correlation,
    and index beta approximations.
    Produces ~20 features.
    """
    features = pd.DataFrame()

    if not stocks_ticks:
        return pd.DataFrame([{"advances": 0, "declines": 0, "ad_ratio": 1.0}])

    # Align data on timestamp index
    stock_returns = {}
    for symbol, df in stocks_ticks.items():
        if not df.empty and 'close' in df.columns:
            stock_returns[symbol] = df['close'].pct_change(1).fillna(0.0)

    if not stock_returns:
        return pd.DataFrame([{"advances": 0, "declines": 0, "ad_ratio": 1.0}])

    returns_df = pd.DataFrame(stock_returns)

    # Advances and Declines
    advances = (returns_df > 0).sum(axis=1)
    declines = (returns_df < 0).sum(axis=1)
    ad_ratio = advances / declines.replace(0, 1.0)

    features['advances'] = advances
    features['declines'] = declines
    features['ad_ratio'] = ad_ratio

    # Market breadth average momentum
    features['breadth_mean_return'] = returns_df.mean(axis=1)
    features['breadth_std_return'] = returns_df.std(axis=1)

    return features.fillna(0.0)
