"""
Walk-Forward Validation split generator.
"""

from __future__ import annotations

from typing import Generator, Tuple
import pandas as pd


def walk_forward_split(
    df: pd.DataFrame,
    train_window_days: int = 30,
    val_window_days: int = 7
) -> Generator[Tuple[pd.DataFrame, pd.DataFrame], None, None]:
    """
    Generate sequential walk-forward training and validation splits.
    Guarantees no temporal data leakage (validation is always chronologically after training).
    """
    if df.empty:
        return

    # Normalize timestamps to days
    times = df.index
    start_date = times.min().normalize()
    end_date = times.max().normalize()

    current_train_start = start_date

    while True:
        current_train_end = current_train_start + pd.Timedelta(days=train_window_days)
        current_val_end = current_train_end + pd.Timedelta(days=val_window_days)

        if current_val_end > end_date:
            break

        # Slices
        train_slice = df[(df.index >= current_train_start) & (df.index < current_train_end)]
        val_slice = df[(df.index >= current_train_end) & (df.index <= current_val_end)]

        if not train_slice.empty and not val_slice.empty:
            yield train_slice, val_slice

        # Step forward by validation window
        current_train_start += pd.Timedelta(days=val_window_days)
