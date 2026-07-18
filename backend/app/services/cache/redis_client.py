"""
Async Redis client with connection pool.

Provides a reusable Redis connection for the entire application.
"""

from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level client instance (initialized on first use)
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Get or create the async Redis client.

    Uses a connection pool for efficient connection reuse.
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        # Verify connection
        try:
            await _redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")
