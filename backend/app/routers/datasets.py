"""Datasets: upload once, then profile / preview / draft rules by id."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.errors import AppException
from app.models.orm import Dataset, Job
from app.models.schemas import (
    DatasetDetail,
    DatasetOut,
    DatasetProfile,
    DatasetUpdate,
    JobOut,
    LastJob,
    RowsPage,
    SuggestedRules,
)
from app.services import datasets as service
from app.services.yaml_generator import generate_rules, rules_to_yaml

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _last_jobs(db: Session, ids: list[str]) -> dict[str, Job]:
    if not ids:
        return {}
    latest = (select(Job.dataset_id, func.max(Job.created_at).label("ts"))
              .where(Job.dataset_id.in_(ids)).group_by(Job.dataset_id).subquery())
    rows = db.scalars(select(Job).join(latest, (Job.dataset_id == latest.c.dataset_id)
                                       & (Job.created_at == latest.c.ts))).all()
    return {j.dataset_id: j for j in rows}


def _to_out(ds: Dataset, job: Job | None, cls=DatasetOut):
    out = cls.model_validate(ds, from_attributes=True)
    if job is not None:
        out.last_job = LastJob(id=job.id, mode=job.mode, status=job.status,
                               score=(job.summary or {}).get("score"),
                               created_at=job.created_at)
    return out


@router.post("", response_model=DatasetDetail, status_code=201)
def upload_dataset(file: UploadFile = File(...), name: str | None = Form(None),
                   db: Session = Depends(get_db)):
    # Sync handler on purpose: parsing/profiling is CPU-bound, so FastAPI runs it
    # in its thread pool instead of blocking the event loop.
    raw = file.file.read(settings.max_file_bytes + 1)
    if len(raw) > settings.max_file_bytes:
        raise AppException(413, "file_too_large",
                           f"File exceeds the {settings.max_file_size_mb} MB limit")
    ds = service.create_dataset(db, file.filename or "upload", raw, name)
    return _to_out(ds, None, DatasetDetail)


@router.get("", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db)):
    items = db.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all()
    last = _last_jobs(db, [d.id for d in items])
    return [_to_out(d, last.get(d.id)) for d in items]


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    ds = service.get_dataset(db, dataset_id)
    return _to_out(ds, _last_jobs(db, [ds.id]).get(ds.id), DatasetDetail)


@router.patch("/{dataset_id}", response_model=DatasetDetail)
def update_dataset(dataset_id: str, body: DatasetUpdate, db: Session = Depends(get_db)):
    ds = service.get_dataset(db, dataset_id)
    if body.name is not None:
        ds.name = body.name
    if body.rules_yaml is not None:
        ds.rules_yaml = body.rules_yaml
    db.commit()
    return _to_out(ds, _last_jobs(db, [ds.id]).get(ds.id), DatasetDetail)


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    service.delete_dataset(db, service.get_dataset(db, dataset_id))


@router.get("/{dataset_id}/rows", response_model=RowsPage)
def dataset_rows(dataset_id: str, offset: int = Query(0, ge=0),
                 limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    df = service.load_frame(service.get_dataset(db, dataset_id))
    ids = list(range(offset, min(offset + limit, len(df))))
    return RowsPage(total=len(df), offset=offset, limit=limit,
                    columns=[str(c) for c in df.columns], rows=service.row_payload(df, ids))


@router.get("/{dataset_id}/suggested-rules", response_model=SuggestedRules)
def suggested_rules(dataset_id: str, db: Session = Depends(get_db)):
    ds = service.get_dataset(db, dataset_id)
    profile = DatasetProfile.model_validate(ds.profile)
    return SuggestedRules(rules_yaml=rules_to_yaml(generate_rules(profile)))


@router.get("/{dataset_id}/jobs", response_model=list[JobOut])
def dataset_jobs(dataset_id: str, mode: str | None = None, db: Session = Depends(get_db)):
    service.get_dataset(db, dataset_id)
    q = select(Job).where(Job.dataset_id == dataset_id)
    if mode:
        q = q.where(Job.mode == mode)
    return db.scalars(q.order_by(Job.created_at.desc())).all()
