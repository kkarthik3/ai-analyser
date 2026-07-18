"""
Celery alert notification tasks.
"""

from __future__ import annotations

import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_async_dispatch(title: str, message: str) -> None:
    from app.services.alerts.alert_manager import AlertManager
    manager = AlertManager()
    await manager.trigger_alert(title, message)


@celery_app.task(name="app.tasks.alert_tasks.dispatch_alert")
def dispatch_alert(title: str, message: str) -> None:
    """Dispatch an alert message across all configured channels."""
    logger.info(f"[Celery] Dispatching alert: {title}")
    asyncio.run(_run_async_dispatch(title, message))
