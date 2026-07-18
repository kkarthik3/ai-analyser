"""
Celery analytics tasks.

Defines the periodic tasks that trigger the calculations cycle for all indices and stocks.
"""

from __future__ import annotations

import asyncio
import logging

from app.tasks.celery_app import celery_app
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def _run_async_calculation_cycle(symbol: str) -> None:
    """Initialize dependency injection container and execute the compute engine cycle."""
    from app.dependencies import initialize_services, get_compute_engine_instance
    from app.services.cache.redis_client import get_redis

    # Ensure Redis client and dependencies are active inside the Celery worker process
    await initialize_services()
    engine = get_compute_engine_instance()
    await engine.run_calculation_cycle(symbol)


@celery_app.task(name="app.tasks.analytics_tasks.compute_symbol_metrics")
def compute_symbol_metrics(symbol: str) -> None:
    """Run technical and option analysis for a given symbol."""
    logger.info(f"[Celery] Running calculations for {symbol}")
    asyncio.run(_run_async_calculation_cycle(symbol))


@celery_app.task(name="app.tasks.analytics_tasks.trigger_all_calculations")
def trigger_all_calculations() -> None:
    """Periodically triggers calculation cycles for all watchlisted symbols."""
    symbols = settings.all_watchlist_symbols
    for symbol in symbols:
        compute_symbol_metrics.delay(symbol)
