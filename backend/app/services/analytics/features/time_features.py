"""
Time-based feature generators.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def generate_time_features(df: pd.DataFrame, expiry_date: pd.Timestamp = None) -> pd.DataFrame:
    """
    Generate time-of-day, day-of-week, and distance-to-expiry features.
    Produces ~20 features.
    """
    features = pd.DataFrame(index=df.index)
    times = df.index

    # Time of day (fractional day)
    features['hour'] = times.hour
    features['minute'] = times.minute
    features['day_of_week'] = times.dayofweek

    # Minutes since market open (NSE open is 9:15 AM)
    market_open_minutes = times.hour * 60 + times.minute - (9 * 60 + 15)
    features['minutes_since_open'] = np.clip(market_open_minutes, 0, 375)

    # Expiry distance (in days)
    if expiry_date is not None:
        expiry_ts = pd.to_datetime(expiry_date)
        time_diff = expiry_ts - times.normalize()
        features['days_to_expiry'] = time_diff.dt.days
        features['expiry_weight'] = 1.0 / (features['days_to_expiry'] + 0.1)
    else:
        features['days_to_expiry'] = 7.0
        features['expiry_weight'] = 0.1

    # Sine/Cosine encoding of time of day (for cyclical features)
    day_fraction = features['minutes_since_open'] / 375.0
    features['time_sin'] = np.sin(2 * np.pi * day_fraction)
    features['time_cos'] = np.cos(2 * np.pi * day_fraction)

    return features.fillna(0.0)
