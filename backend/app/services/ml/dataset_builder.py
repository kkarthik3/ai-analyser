"""
ML Dataset Builder.

Constructs training datasets from historical features and option chain ticks,
labeling targets representing fractional gains within forward time horizons.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

import pandas as pd
import numpy as np

from app.db.engine import get_async_session
from app.db.repositories.base import BaseRepository
from app.db.models.feature_store import FeatureStoreEntry
from app.db.models.market_ticks import MarketTick

logger = logging.getLogger(__name__)


class DatasetBuilder:
    """Extracts features and builds targets with forward-looking labels (no leakage)."""

    def __init__(self) -> None:
        pass

    async def build_dataset(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Query feature store and tick records to construct features (X) and labels (y).
        Forward horizons: 5, 15, 30, 60 minutes.
        Forward targets: close price return >= 0.5%, 1.0%, 2.0%.
        """
        async with get_async_session() as session:
            # Query feature store
            feat_repo = BaseRepository(session, FeatureStoreEntry)
            ticks_repo = BaseRepository(session, MarketTick)

            # Raw SQL/ORM query to pull feature entries in range
            from sqlalchemy import select
            feat_stmt = (
                select(FeatureStoreEntry)
                .where(
                    FeatureStoreEntry.symbol == symbol,
                    FeatureStoreEntry.time >= start_time,
                    FeatureStoreEntry.time <= end_time
                )
                .order_by(FeatureStoreEntry.time.asc())
            )
            feat_records = await feat_repo.execute_query(feat_stmt)

            tick_stmt = (
                select(MarketTick)
                .where(
                    MarketTick.symbol == symbol,
                    MarketTick.time >= start_time,
                    MarketTick.time <= end_time + timedelta(hours=2) # Fetch extra forward data for labeling
                )
                .order_by(MarketTick.time.asc())
            )
            ticks = await ticks_repo.execute_query(tick_stmt)

        if not feat_records or not ticks:
            return pd.DataFrame(), pd.DataFrame()

        # Parse features
        features_df = pd.DataFrame([
            {
                "time": f.time,
                **f.features
            }
            for f in feat_records
        ])
        features_df.set_index("time", inplace=True)

        # Parse ticks
        ticks_df = pd.DataFrame([
            {
                "time": t.time,
                "close": t.ltp
            }
            for t in ticks
        ])
        ticks_df.set_index("time", inplace=True)
        ticks_df.sort_index(inplace=True)

        # Labels construction
        labels = []
        for time_idx in features_df.index:
            current_close = ticks_df.asof(time_idx)["close"] if time_idx in ticks_df.index else None
            if current_close is None or np.isnan(current_close):
                labels.append({
                    "target_5m_1pct": 0,
                    "target_15m_2pct": 0,
                    "target_30m_3pct": 0
                })
                continue

            # Look forward
            fwd_5m = time_idx + timedelta(minutes=5)
            fwd_15m = time_idx + timedelta(minutes=15)
            fwd_30m = time_idx + timedelta(minutes=30)

            # Find closest future closes
            close_5m = ticks_df.asof(fwd_5m)["close"] if fwd_5m <= ticks_df.index[-1] else current_close
            close_15m = ticks_df.asof(fwd_15m)["close"] if fwd_15m <= ticks_df.index[-1] else current_close
            close_30m = ticks_df.asof(fwd_30m)["close"] if fwd_30m <= ticks_df.index[-1] else current_close

            # Target labels: binary indicator of target threshold hit
            labels.append({
                "target_5m_1pct": int(((close_5m - current_close) / current_close) >= 0.005),
                "target_15m_2pct": int(((close_15m - current_close) / current_close) >= 0.01),
                "target_30m_3pct": int(((close_30m - current_close) / current_close) >= 0.02)
            })

        labels_df = pd.DataFrame(labels, index=features_df.index)
        return features_df, labels_df
