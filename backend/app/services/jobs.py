"""Validation jobs: create, execute (in the worker or inline), read results, export."""
from __future__ import annotations

import gzip
import io
import json
import logging
from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.errors import AppException, not_found
from app.models.orm import Job, RuleSet
from app.services import datasets as ds_service
from app.services.storage import get_storage
from app.services.yaml_generator import parse_rules_yaml
from app.validators.rule_engine import compile_or_raise, run_rules

log = logging.getLogger(__name__)

EXPORT_KINDS = ("clean", "quarantine", "annotated")
EXPORT_FORMATS = ("csv", "json", "parquet", "xlsx")


def _now() -> datetime:
    return datetime.now(UTC)


def _issues_key(job_id: str) -> str:
    return f"jobs/{job_id}/results.json.gz"


# --- creation ----------------------------------------------------------------------

def create_job(db: Session, dataset_id: str, mode: str, rules_yaml: str | None,
               rule_set_id: str | None) -> Job:
    dataset = ds_service.get_dataset(db, dataset_id)
    if rule_set_id:
        rule_set = db.get(RuleSet, rule_set_id)
        if rule_set is None:
            raise not_found("rule_set")
        rules_yaml = rule_set.rules_yaml
    if rules_yaml is None:
        rules_yaml = dataset.rules_yaml

    # Fail fast with a 4xx instead of queueing a job that can only fail.
    compile_or_raise(parse_rules_yaml(rules_yaml),
                     columns=list(dataset.profile.get("columns", {})))

    job = Job(dataset_id=dataset.id, rule_set_id=rule_set_id, mode=mode,
              status="queued", rules_yaml=rules_yaml)
    db.add(job)
    db.commit()
    if mode == "sample":
        _prune_sample_jobs(db, dataset.id)
    return job


def _prune_sample_jobs(db: Session, dataset_id: str) -> None:
    old = db.scalars(
        select(Job).where(Job.dataset_id == dataset_id, Job.mode == "sample")
        .order_by(Job.created_at.desc()).offset(settings.keep_sample_jobs)
    ).all()
    for job in old:
        get_storage().delete_prefix(f"jobs/{job.id}/")
        db.delete(job)
    if old:
        db.commit()


# --- execution -----------------------------------------------------------------------

def execute_job(job_id: str) -> None:
    """Run a job to completion. Never raises: failures are recorded on the job."""
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            log.warning("job %s vanished before it ran", job_id)
            return
        job.status, job.started_at, job.progress = "running", _now(), 5
        db.commit()

        try:
            dataset = job.dataset
            full = ds_service.load_frame(dataset)
            df = ds_service.sample_frame(full) if job.mode == "sample" else full
            job.progress = 15
            db.commit()

            last = {"p": job.progress}

            def on_progress(fraction: float) -> None:
                p = 15 + int(fraction * 80)
                if p - last["p"] >= 5:                   # don't hammer the DB
                    last["p"] = job.progress = p
                    db.commit()

            result = run_rules(df, parse_rules_yaml(job.rules_yaml), on_progress)

            payload = {
                "checked_rows": [int(i) for i in df.index] if job.mode == "sample" else None,
                "issues": {str(k): v for k, v in result.row_issues.items()},
            }
            get_storage().put(_issues_key(job.id),
                              gzip.compress(json.dumps(payload).encode()))

            job.summary = result.summary(dataset_rows=len(full))
            job.violations = [v.model_dump(mode="json") for v in result.violations]
            job.status, job.progress = "succeeded", 100
        except AppException as exc:
            job.status = "failed"
            job.error = {"error": exc.error, "detail": exc.detail, **exc.extra}
        except Exception as exc:  # incl. Celery's SoftTimeLimitExceeded
            log.exception("job %s crashed", job_id)
            job.status = "failed"
            job.error = {"error": "internal_error", "detail": str(exc) or type(exc).__name__}
        finally:
            job.finished_at = _now()
            db.commit()


def dispatch(job: Job, background=None) -> None:
    """Sample jobs run right away (they're the instant-feedback path); full jobs
    go to Celery, or to FastAPI background tasks when INLINE_JOBS=true."""
    if job.mode == "sample":
        execute_job(job.id)
    elif settings.inline_jobs:
        if background is not None:
            background.add_task(execute_job, job.id)
        else:
            execute_job(job.id)
    else:
        from app.workers.celery_app import full_validate_task
        full_validate_task.delay(job.id)


# --- results -------------------------------------------------------------------------

def get_job(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise not_found("job")
    return job


def _require_done(job: Job) -> None:
    if job.status != "succeeded":
        raise AppException(409, "not_ready", f"Job is '{job.status}', results not available")


def load_results(job: Job) -> tuple[list[int] | None, dict[int, list]]:
    raw = get_storage().get(_issues_key(job.id))
    if raw is None:
        raise AppException(410, "results_missing", "Detailed results for this job are gone")
    payload = json.loads(gzip.decompress(raw))
    issues = {int(k): [tuple(x) for x in v] for k, v in payload["issues"].items()}
    return payload.get("checked_rows"), issues


ROW_FILTERS = ("all", "issues", "errors", "warnings", "clean")


def job_rows(db: Session, job: Job, row_filter: str, column: str | None,
             offset: int, limit: int) -> dict:
    _require_done(job)
    df = ds_service.load_frame(job.dataset)
    checked, issues = load_results(job)
    universe = checked if checked is not None else list(range(len(df)))

    def keep(rid: int) -> bool:
        items = issues.get(rid, [])
        if column:
            items = [i for i in items if i[0] == column]
        if row_filter == "all":
            return not column or bool(items)
        if row_filter == "clean":
            return not any(sev == "error" for _, _, sev in issues.get(rid, []))
        if row_filter == "errors":
            return any(sev == "error" for _, _, sev in items)
        if row_filter == "warnings":
            return any(sev == "warning" for _, _, sev in items)
        return bool(items)                                 # "issues"

    if row_filter == "all" and not column:
        selected = universe
    elif row_filter == "clean":
        selected = [r for r in universe if keep(r)]
    else:
        selected = sorted(r for r in issues if keep(r))

    page = selected[offset:offset + limit]
    return {
        "total": len(selected),
        "offset": offset,
        "limit": limit,
        "columns": [str(c) for c in df.columns],
        "rows": ds_service.row_payload(df, page, issues),
    }


# --- export --------------------------------------------------------------------------

def _issue_text(items: list) -> str:
    return "; ".join(f"{c}: {r}" + (" (warning)" if s == "warning" else "")
                     for c, r, s in items)


def export_frame(job: Job, kind: str) -> pd.DataFrame:
    _require_done(job)
    if kind not in EXPORT_KINDS:
        raise AppException(400, "bad_export_kind", f"kind must be one of {EXPORT_KINDS}")
    full = ds_service.load_frame(job.dataset)
    checked, issues = load_results(job)
    df = full.loc[checked] if checked is not None else full
    error_rows = {r for r, items in issues.items() if any(s == "error" for _, _, s in items)}

    if kind == "clean":
        return df.drop(index=[r for r in error_rows if r in df.index])
    if kind == "quarantine":
        out = df.loc[sorted(error_rows)].copy()
    else:
        out = df.copy()
        out.insert(0, "_status", ["invalid" if r in error_rows
                                  else "warning" if r in issues else "valid"
                                  for r in out.index])
    out.insert(0, "_row", out.index)
    out["_issues"] = [_issue_text(issues.get(r, [])) for r in out.index]
    return out


def serialize(df: pd.DataFrame, fmt: str) -> tuple[bytes, str]:
    if fmt == "csv":
        return df.to_csv(index=False).encode("utf-8"), "text/csv"
    if fmt == "json":
        return (df.to_json(orient="records", force_ascii=False, date_format="iso")
                .encode("utf-8"), "application/json")
    if fmt == "parquet":
        buf = io.BytesIO()
        try:
            df.to_parquet(buf, index=False)
        except Exception as exc:   # e.g. mixed-type object columns
            raise AppException(422, "parquet_export_failed",
                               f"Cannot write Parquet for this data: {exc}")
        return buf.getvalue(), "application/vnd.apache.parquet"
    if fmt == "xlsx":
        buf = io.BytesIO()
        safe = df.map(lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v)
        safe.to_excel(buf, index=False, engine="openpyxl")
        return buf.getvalue(), ("application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet")
    raise AppException(400, "bad_export_format", f"format must be one of {EXPORT_FORMATS}")
