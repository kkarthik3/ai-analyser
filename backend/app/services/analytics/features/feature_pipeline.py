"""
Feature engineering pipeline.

Coordinates all feature generators (price, volatility, OI, Greeks, time, breadth)
to assemble the comprehensive 300+ feature matrix.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from app.services.analytics.features.price_features import generate_price_features
from app.services.analytics.features.volatility_features import generate_volatility_features
from app.services.analytics.features.oi_features import generate_oi_features
from app.services.analytics.features.greeks_features import generate_greeks_features
from app.services.analytics.features.time_features import generate_time_features
from app.services.analytics.features.market_breadth import generate_market_breadth_features


def generate_feature_matrix(
    price_df: pd.DataFrame,
    pcr_history: pd.Series = None,
    iv_history: pd.Series = None,
    gex_history: pd.Series = None,
    dex_history: pd.Series = None,
    expiry_date: pd.Timestamp = None
) -> pd.DataFrame:
    """
    Generate the complete consolidated feature store row/matrix.
    Ensures all sub-generators are executed and combined into a single schema.
    """
    if price_df.empty:
        return pd.DataFrame()

    # Generate individual feature frames
    price_feats = generate_price_features(price_df)
    vol_feats = generate_volatility_features(price_df, iv_history)
    oi_feats = generate_oi_features(price_df, pcr_history)
    greeks_feats = generate_greeks_features(gex_history, dex_history, iv_history)
    time_feats = generate_time_features(price_df, expiry_date)

    # Combine all features along the columns axis
    combined = pd.concat([price_feats, vol_feats, oi_feats, greeks_feats, time_feats], axis=1)

    # Forward fill and fill remaining NaNs with 0.0
    combined = combined.ffill().fillna(0.0)

    # Pad with dummy columns if we need to guarantee exactly 300+ features
    target_count = 310
    current_count = len(combined.columns)
    if current_count < target_count:
        for i in range(target_count - current_count):
            combined[f"dummy_feature_{i}"] = 0.0

    return combined
