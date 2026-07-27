"""Async batch jobs: POST /jobs enqueues a full run, GET /jobs/{id} polls it."""
from __future__ import annotations

import base64
import json
import uuid

from fastapi import APIRouter, File, Form, UploadFile

from app.config import settings
from app.models.schemas import AppException, JobCreatedResponse, JobStatusResponse
from app.services import storage
from app.workers.celery_app import full_validate_task

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreatedResponse)
async def create_job(file: UploadFile = File(...), rules_yaml: str = Form(...)):
    raw = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise AppException(413, "file_too_large",
                           f"File exceeds the {settings.max_file_size_mb} MB limit")

    job_id = str(uuid.uuid4())
    ttl = settings.job_ttl_seconds
    payload = json.dumps({
        "filename": file.filename,
        "file_b64": base64.b64encode(raw).decode(),
        "rules_yaml": rules_yaml,
    })
    await storage.set_value(f"job:{job_id}:input", payload, ttl=ttl)
    await storage.set_value(f"job:{job_id}:status", "queued", ttl=ttl)

    full_validate_task.delay(job_id)
    return JobCreatedResponse(job_id=job_id, status="queued")


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str):
    status = await storage.get_value(f"job:{job_id}:status")
    if status is None:
        raise AppException(404, "job_not_found", "Unknown or expired job id")

    result = error = None
    raw = await storage.get_value(f"job:{job_id}:result")
    if raw:
        parsed = json.loads(raw)
        if status == "error":
            error = parsed
        else:
            result = parsed
    return JobStatusResponse(job_id=job_id, status=status, result=result, error=error)