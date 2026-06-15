from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "eye_boutique",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.health",
        "app.workers.tasks.campaigns",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    enable_utc=True,
    timezone="UTC",
    task_track_started=True,
)
