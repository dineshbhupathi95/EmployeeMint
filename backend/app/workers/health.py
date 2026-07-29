"""Celery worker tasks."""

from app.core.celery_app import celery_app


@celery_app.task(name="app.workers.health.ping")
def ping() -> str:
    return "pong"
