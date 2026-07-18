"""
Real-time market state cache backed by Redis.

Stores the latest tick data, option chain snapshots, computed metrics,
and scores in Redis for ultra-fast access by the API layer and WebSocket
broadcasts. TTL-based expiry prevents stale data accumulation.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Redis key prefixes
TICK_PREFIX = "market:tick:"
CHAIN_PREFIX = "market:chain:"
METRIC_PREFIX = "market:metric:"
SCORE_PREFIX = "market:score:"
STATE_PREFIX = "market:state:"

# Default TTL for cached data (5 minutes)
DEFAULT_TTL = 300


class MarketCache:
    """Redis-backed cache for real-time market state.

    Provides sub-millisecond reads for the latest market data,
    avoiding database queries for hot-path operations.
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    # ---- Tick Data ----

    async def update_tick(self, symbol: str, tick: dict[str, Any]) -> None:
        """Update the latest tick for a symbol."""
        key = f"{TICK_PREFIX}{symbol}"
        await self._redis.set(key, json.dumps(tick, default=str), ex=DEFAULT_TTL)

    async def get_tick(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get the latest tick for a symbol."""
        key = f"{TICK_PREFIX}{symbol}"
        data = await self._redis.get(key)
        return json.loads(data) if data else None

    async def get_all_ticks(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        """Get latest ticks for multiple symbols."""
        pipeline = self._redis.pipeline()
        for symbol in symbols:
            pipeline.get(f"{TICK_PREFIX}{symbol}")

        results = await pipeline.execute()
        return {
            symbol: json.loads(data) if data else None
            for symbol, data in zip(symbols, results)
        }

    # ---- Option Chain ----

    async def update_chain(
        self, underlying: str, chain: list[dict[str, Any]]
    ) -> None:
        """Cache the latest option chain for an underlying."""
        key = f"{CHAIN_PREFIX}{underlying}"
        await self._redis.set(key, json.dumps(chain, default=str), ex=DEFAULT_TTL)

    async def get_chain(self, underlying: str) -> Optional[list[dict[str, Any]]]:
        """Get the cached option chain for an underlying."""
        key = f"{CHAIN_PREFIX}{underlying}"
        data = await self._redis.get(key)
        return json.loads(data) if data else None

    # ---- Computed Metrics ----

    async def update_metrics(
        self, symbol: str, metrics: dict[str, float]
    ) -> None:
        """Cache computed metrics for a symbol."""
        key = f"{METRIC_PREFIX}{symbol}"
        await self._redis.hset(key, mapping={
            k: str(v) for k, v in metrics.items()
        })
        await self._redis.expire(key, DEFAULT_TTL)

    async def get_metrics(self, symbol: str) -> Optional[dict[str, float]]:
        """Get cached metrics for a symbol."""
        key = f"{METRIC_PREFIX}{symbol}"
        data = await self._redis.hgetall(key)
        if data:
            return {k: float(v) for k, v in data.items()}
        return None

    async def get_metric(self, symbol: str, metric_name: str) -> Optional[float]:
        """Get a single cached metric value."""
        key = f"{METRIC_PREFIX}{symbol}"
        value = await self._redis.hget(key, metric_name)
        return float(value) if value else None

    # ---- Scores ----

    async def update_scores(self, symbol: str, scores: dict[str, Any]) -> None:
        """Cache scoring snapshot for a symbol."""
        key = f"{SCORE_PREFIX}{symbol}"
        await self._redis.set(key, json.dumps(scores, default=str), ex=DEFAULT_TTL)

    async def get_scores(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get cached scores for a symbol."""
        key = f"{SCORE_PREFIX}{symbol}"
        data = await self._redis.get(key)
        return json.loads(data) if data else None

    # ---- Global State ----

    async def set_state(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        """Set a global state value."""
        full_key = f"{STATE_PREFIX}{key}"
        await self._redis.set(full_key, json.dumps(value, default=str), ex=ttl)

    async def get_state(self, key: str) -> Optional[Any]:
        """Get a global state value."""
        full_key = f"{STATE_PREFIX}{key}"
        data = await self._redis.get(full_key)
        return json.loads(data) if data else None

    # ---- Pub/Sub for real-time broadcast ----

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        """Publish a message to a Redis channel (for real-time broadcast)."""
        await self._redis.publish(channel, json.dumps(message, default=str))
