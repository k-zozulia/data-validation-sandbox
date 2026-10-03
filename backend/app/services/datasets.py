"""Dataset lifecycle: ingest an upload, load it back (cached), page through rows."""
from __future__ import annotations

import threading
from collections import OrderedDict

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppException, not_found
from app.models.orm import Dataset
from app.parsers import load_dataframe
from app.services.profiler import profile_dataframe
from app.services.storage import get_storage
from app.services.yaml_generator import generate_rules, rules_to_yaml
from app.validators.types import _jsonable

# --- in-process cache of parsed DataFrames ---------------------------------------
# Re-parsing a 100 MB CSV on every page of the data grid would be painful, so a
# few recently used frames are kept per process. Datasets are immutable once
# uploaded, so the cache never goes stale (only evicted on delete / LRU).

_cache: OrderedDict[str, pd.DataFrame] = OrderedDict()
_cache_lock = threading.Lock()


def _cache_get(dataset_id: str) -> pd.DataFrame | None:
    with _cache_lock:
        df = _cache.get(dataset_id)
        if df is not None:
            _cache.move_to_end(dataset_id)
        return df


def _cache_put(dataset_id: str, df: pd.DataFrame) -> None:
    with _cache_lock:
        _cache[dataset_id] = df
        _cache.move_to_end(dataset_id)
        while len(_cache) > settings.dataset_cache_size:
            _cache.popitem(last=False)


def cache_evict(dataset_id: str) -> None:
    with _cache_lock:
        _cache.pop(dataset_id, None)


# --- ingestion -------------------------------------------------------------------

def _source_key(dataset_id: str, fmt: str) -> str:
    return f"datasets/{dataset_id}/source.{fmt}"


def create_dataset(db: Session, filename: str, raw: bytes, name: str | None = None) -> Dataset:
    df, fmt = load_dataframe(filename, raw)
    profile = profile_dataframe(df)
    rules_yaml = rules_to_yaml(generate_rules(profile))

    ds = Dataset(
        name=(name or filename).strip()[:255] or filename,
        filename=filename,
        format=fmt,
        size_bytes=len(raw),
        storage_key="",
        row_count=profile.row_count,
        column_count=profile.column_count,
        profile=profile.model_dump(mode="json"),
        rules_yaml=rules_yaml,
    )
    db.add(ds)
    db.flush()                                    # assigns the id
    ds.storage_key = _source_key(ds.id, fmt)
    get_storage().put(ds.storage_key, raw)
    db.commit()
    _cache_put(ds.id, df)
    return ds


def get_dataset(db: Session, dataset_id: str) -> Dataset:
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise not_found("dataset")
    return ds


def load_frame(ds: Dataset) -> pd.DataFrame:
    df = _cache_get(ds.id)
    if df is not None:
        return df
    raw = get_storage().get(ds.storage_key)
    if raw is None:
        raise AppException(410, "dataset_file_missing",
                           "The stored file for this dataset is gone; upload it again")
    df, _ = load_dataframe(ds.filename, raw)
    _cache_put(ds.id, df)
    return df


def delete_dataset(db: Session, ds: Dataset) -> None:
    storage = get_storage()
    job_ids = [j.id for j in ds.jobs]
    db.delete(ds)
    db.commit()
    storage.delete_prefix(f"datasets/{ds.id}/")
    for job_id in job_ids:
        storage.delete_prefix(f"jobs/{job_id}/")
    cache_evict(ds.id)


# --- paging ----------------------------------------------------------------------

def sample_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Deterministic random sample that keeps the original row numbers."""
    if len(df) <= settings.sample_rows:
        return df
    return df.sample(n=settings.sample_rows, random_state=settings.sample_seed).sort_index()


def row_payload(df: pd.DataFrame, row_ids: list[int],
                issues: dict[int, list] | None = None) -> list[dict]:
    rows = []
    for rid in row_ids:
        record = df.loc[rid]
        rows.append({
            "_row": int(rid),
            "values": {str(c): _jsonable(record[c]) for c in df.columns},
            "issues": [{"column": c, "rule": r, "severity": s}
                       for c, r, s in (issues or {}).get(rid, [])],
        })
    return rows
