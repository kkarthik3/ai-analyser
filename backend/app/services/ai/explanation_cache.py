"""
Explanation Cache.

Caches AI reports in Redis to avoid redundant external LLM API calls.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.services.cache.market_cache import MarketCache

logger = logging.getLogger(__name__)

CACHE_PREFIX = "ai:report:"
DEFAULT_EXPIRE = 60  # Cache for 1 minute (reports are generated every minute)


class ExplanationCache:
    """Caches recent AI generated explanations."""

    def __init__(self, market_cache: MarketCache) -> None:
        self._cache = market_cache

    async def get_cached_report(self, symbol: str, report_type: str) -> Optional[str]:
        """Fetch cached report if available."""
        key = f"{CACHE_PREFIX}{symbol}:{report_type}"
        return await self._cache.get_state(key)

    async def cache_report(self, symbol: str, report_type: str, content: str) -> None:
        """Cache generated report."""
        key = f"{CACHE_PREFIX}{symbol}:{report_type}"
        await self._cache.set_state(key, content, ttl=DEFAULT_EXPIRE)
        logger.debug(f"Cached report for {symbol} ({report_type})")
