"""Celery worker: runs the full batch validation asynchronously.

Separate process from the API, so state is shared only through Redis
(the uploaded file is stashed there as base64 with a TTL for now).
"""
from __future__ import annotations

import base64
import json

import redis
from celery import Celery

from app.config import settings
from app.models.schemas import AppException
from app.parsers import load_dataframe
from app.services.yaml_generator import parse_rules_yaml
from app.validators.rule_engine import run_rules

celery = Celery("dvs", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_soft_time_limit=120, 
    task_time_limit=150,
)

# Sync Redis client for the worker process (FastAPI uses the async client).
_r = redis.from_url(settings.redis_url, decode_responses=True)


def _key(job_id: str, suffix: str) -> str:
    return f"job:{job_id}:{suffix}"


@celery.task(name="full_validate")
def full_validate_task(job_id: str) -> None:
    ttl = settings.job_ttl_seconds
    _r.set(_key(job_id, "status"), "running", ex=ttl)
    try:
        payload = _r.get(_key(job_id, "input"))
        if payload is None:
            raise AppException(404, "job_input_missing", "Job input has expired")

        data = json.loads(payload)
        raw = base64.b64decode(data["file_b64"])
        df = load_dataframe(data["filename"], raw)             # full file, no nrows
        rules = parse_rules_yaml(data["rules_yaml"])
        violations = run_rules(df, rules)[: settings.max_violations_stored]

        result = {
            "row_count": len(df),
            "total_violations": len(violations),
            "rules_failed": sorted({v.rule for v in violations}),
            "columns_flagged": sorted({v.column for v in violations}),
            "violations": [v.model_dump() for v in violations],
        }
        _r.set(_key(job_id, "result"), json.dumps(result), ex=ttl)
        _r.set(_key(job_id, "status"), "done", ex=ttl)

    except AppException as exc:
        _r.set(_key(job_id, "result"),
               json.dumps({"error": exc.error, "detail": exc.detail}), ex=ttl)
        _r.set(_key(job_id, "status"), "error", ex=ttl)
    except Exception as exc:  # incl. SoftTimeLimitExceeded
        _r.set(_key(job_id, "result"),
               json.dumps({"error": "internal_error", "detail": str(exc)}), ex=ttl)
        _r.set(_key(job_id, "status"), "error", ex=ttl)