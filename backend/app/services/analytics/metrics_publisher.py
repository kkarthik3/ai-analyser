"""
Metrics publisher.

Saves computed metrics and features to the database and Redis cache,
and broadcasts updates to subscribers.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.db.engine import get_async_session
from app.db.models.computed_metrics import ComputedMetric
from app.db.models.feature_store import FeatureStoreEntry
from app.services.cache.market_cache import MarketCache

logger = logging.getLogger(__name__)


class MetricsPublisher:
    """Publishes calculated indicators, Greeks, and features to storage and real-time clients."""

    def __init__(self, market_cache: MarketCache) -> None:
        self._cache = market_cache

    async def publish_metrics(
        self,
        symbol: str,
        metrics: Dict[str, float],
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Publish computed metrics to Redis and database.
        """
        now = datetime.now(timezone.utc)
        meta = metadata or {}

        # 1. Update Redis cache
        await self._cache.update_metrics(symbol, metrics)

        # 2. Write to DB
        try:
            async with get_async_session() as session:
                records = [
                    ComputedMetric(
                        time=now,
                        symbol=symbol,
                        metric_name=name,
                        value=float(val),
                        metadata_=meta
                    )
                    for name, val in metrics.items()
                ]
                session.add_all(records)
            logger.debug(f"Published {len(metrics)} metrics for {symbol}")
        except Exception as e:
            logger.error(f"Error saving computed metrics to database: {e}")

    async def publish_features(
        self,
        symbol: str,
        features: Dict[str, float]
    ) -> None:
        """
        Save computed feature vector to the feature store.
        """
        now = datetime.now(timezone.utc)

        try:
            async with get_async_session() as session:
                record = FeatureStoreEntry(
                    time=now,
                    symbol=symbol,
                    features=features
                )
                session.add(record)
        except Exception as e:
            logger.error(f"Error saving features to store: {e}")

    async def publish_scores(
        self,
        symbol: str,
        scores: Dict[str, Any]
    ) -> None:
        """
        Publish computed scores to Redis and database.
        """
        now = datetime.now(timezone.utc)

        # 1. Update Redis cache
        await self._cache.update_scores(symbol, scores)

        # 2. Write to DB
        try:
            async with get_async_session() as session:
                from app.db.models.computed_metrics import ComputedMetric
                records = [
                    ComputedMetric(
                        time=now,
                        symbol=symbol,
                        metric_name=f"score_{name}",
                        value=float(val) if isinstance(val, (int, float)) else 0.0,
                        metadata_={"string_val": str(val)} if not isinstance(val, (int, float)) else {}
                    )
                    for name, val in scores.items()
                ]
                session.add_all(records)
            logger.debug(f"Published scores for {symbol}")
        except Exception as e:
            logger.error(f"Error saving computed scores to database: {e}")
