"""
Celery application configuration.

Configures Celery with Redis as broker and result backend.
Task scheduling, worker concurrency, and serialization settings.
"""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "aibot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # Beat schedule — periodic tasks (Phase 3)
    beat_schedule={
        "trigger-calculations": {
            "task": "app.tasks.analytics_tasks.trigger_all_calculations",
            "schedule": 5.0,  # Every 5 seconds
        },
        "trigger-ai-reports": {
            "task": "app.tasks.ai_tasks.trigger_all_reports",
            "schedule": 60.0,  # Every 60 seconds
        },
    },
)

# Auto-discover tasks from these modules
celery_app.autodiscover_tasks(["app.tasks"])
