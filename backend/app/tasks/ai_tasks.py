"""
Celery AI explanation and reporting tasks.
"""

from __future__ import annotations

import asyncio
import logging

from app.tasks.celery_app import celery_app
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def _run_async_ai_report(symbol: str) -> None:
    """Load latest metrics and scores from cache and generate Groq AI report."""
    from app.dependencies import initialize_services, get_cache_instance
    from app.services.ai.groq_client import GroqClient
    from app.services.ai.report_generator import AIReportGenerator

    await initialize_services()
    cache = get_cache_instance()

    if not cache:
        logger.error("Market cache not available")
        return

    # Fetch cached state
    metrics = await cache.get_metrics(symbol)
    scores = await cache.get_scores(symbol)

    if not metrics or not scores:
        logger.warning(f"Skipping AI report for {symbol}: metrics or scores missing in cache.")
        return

    # Initialize Groq client and generator
    groq = GroqClient()
    generator = AIReportGenerator(groq_client=groq)

    await generator.generate_and_save_report(
        symbol=symbol,
        metrics=metrics,
        scores=scores
    )


@celery_app.task(name="app.tasks.ai_tasks.generate_market_report")
def generate_market_report(symbol: str) -> None:
    """Generate and save AI intelligence report for a symbol."""
    logger.info(f"[Celery] Generating AI report for {symbol}")
    asyncio.run(_run_async_ai_report(symbol))


@celery_app.task(name="app.tasks.ai_tasks.trigger_all_reports")
def trigger_all_reports() -> None:
    """Periodically triggers report generation for active indices."""
    indices = settings.watchlist_indices_list
    for idx in indices:
        generate_market_report.delay(idx)
