"""Parquet parsing with a decompression-bomb guard."""
from __future__ import annotations

import io

import pandas as pd
import pyarrow.parquet as pq

from app.config import settings
from app.models.schemas import AppException


def parse_parquet(source: bytes, nrows: int | None = None) -> pd.DataFrame:
    try:
        pf = pq.ParquetFile(io.BytesIO(source))
    except Exception as exc:
        raise AppException(400, "invalid_parquet", f"Could not read Parquet: {exc}")

    meta = pf.metadata
    if meta.num_columns > settings.max_columns:
        raise AppException(413, "too_many_columns",
                           f"{meta.num_columns} columns exceeds the limit "
                           f"of {settings.max_columns}")
    if meta.num_rows > settings.max_rows_full_run:
        raise AppException(413, "too_many_rows",
                           f"{meta.num_rows} rows exceeds the limit "
                           f"of {settings.max_rows_full_run}")

    # Estimated uncompressed size across row groups (decompression-bomb guard).
    budget = settings.max_file_size_mb * 8 * 1024 * 1024
    uncompressed = sum(meta.row_group(i).total_byte_size
                       for i in range(meta.num_row_groups))
    if uncompressed > budget:
        raise AppException(413, "parquet_too_large",
                           f"Uncompressed size ~{uncompressed // (1024 * 1024)} MB "
                           f"exceeds the in-memory budget")

    if nrows is not None:
        batch = next(pf.iter_batches(batch_size=nrows), None)
        return batch.to_pandas() if batch is not None else pd.DataFrame()
    return pf.read().to_pandas()