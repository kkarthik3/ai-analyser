"""
Volatility-based feature generators.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from app.services.analytics.technical.indicators import compute_atr


def generate_volatility_features(
    df: pd.DataFrame,
    iv_history: pd.Series = None
) -> pd.DataFrame:
    """
    Generate volatility features: ATR, IV Rank, IV Percentile, Bollinger Band Width.
    Produces ~30 features.
    """
    features = pd.DataFrame(index=df.index)
    close = df['close']

    # ATR Features
    atr_14 = compute_atr(df, 14)
    features['atr_14'] = atr_14
    features['atr_pct'] = atr_14 / close

    # Bollinger Band Width (volatility indicator)
    basis = close.rolling(20).mean()
    std = close.rolling(20).std()
    features['bb_width'] = (4 * std) / basis.replace(0, 1.0)

    # Implied Volatility Features (if IV series is provided)
    if iv_history is not None and not iv_history.empty:
        features['iv'] = iv_history
        features['iv_change_1m'] = iv_history.pct_change(1)
        features['iv_change_5m'] = iv_history.pct_change(5)

        # IV Rank & Percentile (rolling 252 periods or length of series)
        window = min(252, len(iv_history))
        if window > 1:
            roll_min = iv_history.rolling(window).min()
            roll_max = iv_history.rolling(window).max()
            features['iv_rank'] = (iv_history - roll_min) / (roll_max - roll_min).replace(0, 1.0)

            # IV Percentile
            features['iv_percentile'] = iv_history.rolling(window).apply(
                lambda x: (x < x.iloc[-1]).sum() / len(x), raw=False
            )
        else:
            features['iv_rank'] = 0.5
            features['iv_percentile'] = 0.5
    else:
        features['iv'] = 0.0
        features['iv_rank'] = 0.0
        features['iv_percentile'] = 0.0

    return features.fillna(0.0)
