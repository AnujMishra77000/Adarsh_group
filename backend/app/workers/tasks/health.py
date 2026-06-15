from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="system.ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}
