"""Async batch jobs: enqueue a full run, poll it, and export clean/quarantine data."""
from __future__ import annotations

import base64
import json
import uuid

from fastapi import APIRouter, File, Form, Response, UploadFile

from app.config import settings
from app.models.schemas import AppException, JobCreatedResponse, JobStatusResponse
from app.parsers import load_dataframe
from app.services import storage
from app.workers.celery_app import full_validate_task, split_dataframe

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


@router.get("/{job_id}/export/{kind}")
async def export_job(job_id: str, kind: str):
    if kind not in ("clean", "quarantine"):
        raise AppException(400, "bad_export_kind", "kind must be 'clean' or 'quarantine'")

    status = await storage.get_value(f"job:{job_id}:status")
    if status is None:
        raise AppException(404, "job_not_found", "Unknown or expired job id")
    if status != "done":
        raise AppException(409, "not_ready", f"Job is '{status}', export not available yet")

    input_raw = await storage.get_value(f"job:{job_id}:input")
    idx_raw = await storage.get_value(f"job:{job_id}:quarantine_idx")
    if input_raw is None or idx_raw is None:
        raise AppException(404, "export_not_found", "Export data expired or unavailable")

    data = json.loads(input_raw)
    df = load_dataframe(data["filename"], base64.b64decode(data["file_b64"]))
    clean, quarantine = split_dataframe(df, json.loads(idx_raw))
    csv_text = (quarantine if kind == "quarantine" else clean).to_csv(index=False)

    return Response(content=csv_text, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{kind}.csv"'})