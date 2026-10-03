"""Celery worker: runs full validation jobs asynchronously.

A separate process from the API; the two share state only through the
database (job status/progress/results) and object storage (files).
"""
from __future__ import annotations

from celery import Celery

from app.config import settings
from app.services.jobs import execute_job

celery = Celery("dvs", broker=settings.redis_url)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,                         # results live in the DB
    task_acks_late=True,                             # re-run if a worker dies mid-job
    worker_prefetch_multiplier=1,                    # jobs are long; don't hoard them
    task_soft_time_limit=settings.job_soft_time_limit,   # guard against runaway jobs
    task_time_limit=settings.job_soft_time_limit + 30,   # hard kill a bit later
    broker_connection_retry_on_startup=True,
)


@celery.task(name="full_validate")
def full_validate_task(job_id: str) -> None:
    execute_job(job_id)
