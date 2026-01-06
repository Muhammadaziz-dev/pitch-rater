import json
import os
from datetime import datetime
from jobs.models import Job
from redis import Redis


redis_url = os.getenv("CELERY_REDIS_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
redis_client = Redis.from_url(redis_url, decode_responses=True)

def save_job(job: Job):
    redis_client.set(f"job {job.id}", job.json())


def load_job(job_id: str) -> Job | None:
    job_data = redis_client.get(f"job {job_id}")
    if job_data is None:
        return None
    return Job.parse_raw(job_data)


def update_job(job_id: str, **updates) -> Job | None:
    job = load_job(job_id)
    if job is None:
        return None
    updated = job.copy(update=updates)
    save_job(updated)
    return updated


def create_job(job_id: str) -> Job:
    job = Job(
        id=job_id,
        status="pending",
        created_at=datetime.utcnow()
    )
    save_job(job)
    return job
