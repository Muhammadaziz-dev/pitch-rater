import os

from celery import Celery


def _redis_url() -> str:
    return os.getenv("CELERY_REDIS_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"


celery_app = Celery(
    "pitch_rater",
    broker=_redis_url(),
    backend=_redis_url(),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Ensure task modules are imported so Celery registers them.
celery_app.conf.include = ["jobs.tasks"]

