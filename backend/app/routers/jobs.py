"""Validation jobs: launch (sample or full), poll, browse rows, export."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppException
from app.models.orm import Job
from app.models.schemas import JobCreate, JobDetail, JobOut, RowsPage
from app.services import jobs as service
from app.services.storage import get_storage

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _detail(job: Job) -> JobDetail:
    out = JobDetail.model_validate(job, from_attributes=True)
    out.dataset_name = job.dataset.name if job.dataset else None
    return out


@router.post("", response_model=JobDetail, status_code=201)
def create_job(body: JobCreate, background: BackgroundTasks, db: Session = Depends(get_db)):
    job = service.create_job(db, body.dataset_id, body.mode, body.rules_yaml, body.rule_set_id)
    service.dispatch(job, background)
    db.refresh(job)
    return _detail(job)


@router.get("", response_model=list[JobOut])
def list_jobs(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    return db.scalars(select(Job).order_by(Job.created_at.desc()).limit(limit)).all()


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str, db: Session = Depends(get_db)):
    return _detail(service.get_job(db, job_id))


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = service.get_job(db, job_id)
    if job.status in ("queued", "running"):
        raise AppException(409, "job_active", "Wait for the job to finish before deleting it")
    db.delete(job)
    db.commit()
    get_storage().delete_prefix(f"jobs/{job_id}/")


@router.get("/{job_id}/rows", response_model=RowsPage)
def job_rows(job_id: str,
             filter: str = Query("issues", pattern="^(all|issues|errors|warnings|clean)$"),
             column: str | None = None,
             offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500),
             db: Session = Depends(get_db)):
    job = service.get_job(db, job_id)
    return service.job_rows(db, job, filter, column, offset, limit)


@router.get("/{job_id}/export/{kind}")
def export_job(job_id: str, kind: str,
               format: str = Query("csv", pattern="^(csv|json|parquet|xlsx)$"),
               db: Session = Depends(get_db)):
    job = service.get_job(db, job_id)
    content, media_type = service.serialize(service.export_frame(job, kind), format)
    filename = f"{job.dataset.name.rsplit('.', 1)[0]}-{kind}.{format}"
    ascii_name = filename.encode("ascii", "ignore").decode() or f"{kind}.{format}"
    return Response(content=content, media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{ascii_name}"'})
