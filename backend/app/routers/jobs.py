"""Async batch jobs: enqueue a full run, poll it, and export clean/quarantine data."""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, File, Form, Response, UploadFile

from app.config import settings
from app.models.schemas import AppException, JobCreatedResponse, JobStatusResponse
from app.parsers import load_dataframe
from app.services import storage
from app.workers.celery_app import full_validate_task

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _input_key(job_id: str) -> str:
    return f"jobs/{job_id}/input"


@router.post("", response_model=JobCreatedResponse)
async def create_job(file: UploadFile = File(...), rules_yaml: str = Form(...)):
    raw = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise AppException(413, "file_too_large",
                           f"File exceeds the {settings.max_file_size_mb} MB limit")

    job_id = str(uuid.uuid4())
    ttl = settings.job_ttl_seconds

    # Raw file bytes -> S3; lightweight metadata -> Redis.
    storage.put_file(_input_key(job_id), raw)
    meta = json.dumps({"filename": file.filename, "rules_yaml": rules_yaml})
    await storage.set_value(f"job:{job_id}:meta", meta, ttl=ttl)
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

    meta_raw = await storage.get_value(f"job:{job_id}:meta")
    reasons_raw = await storage.get_value(f"job:{job_id}:reasons")
    file_bytes = storage.get_file(_input_key(job_id))
    if meta_raw is None or reasons_raw is None or file_bytes is None:
        raise AppException(404, "export_not_found", "Export data expired or unavailable")

    meta = json.loads(meta_raw)
    df = load_dataframe(meta["filename"], file_bytes)
    reasons = {int(k): v for k, v in json.loads(reasons_raw).items()}
    dirty = sorted(reasons.keys())

    if kind == "quarantine":
        out_df = df.loc[dirty].copy()
        out_df["_violations"] = ["; ".join(reasons[i]) for i in dirty]
        csv_text = out_df.to_csv(index=False)
    else:
        csv_text = df.drop(index=dirty).to_csv(index=False)

    return Response(content=csv_text, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{kind}.csv"'})