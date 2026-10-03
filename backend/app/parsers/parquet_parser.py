"""Parquet parsing with a decompression-bomb guard."""
from __future__ import annotations

import io

import pandas as pd
import pyarrow.parquet as pq

from app.config import settings
from app.errors import AppException


def parse_parquet(raw: bytes) -> pd.DataFrame:
    try:
        pf = pq.ParquetFile(io.BytesIO(raw))
    except Exception as exc:
        raise AppException(400, "invalid_parquet", f"Could not read Parquet: {exc}")

    meta = pf.metadata
    if meta.num_columns > settings.max_columns:
        raise AppException(413, "too_many_columns",
                           f"{meta.num_columns} columns exceeds the limit "
                           f"of {settings.max_columns}")
    if meta.num_rows > settings.max_rows:
        raise AppException(413, "too_many_rows",
                           f"{meta.num_rows} rows exceeds the limit of {settings.max_rows}")

    # Estimated uncompressed size across row groups (decompression-bomb guard).
    budget = settings.max_file_bytes * 8
    uncompressed = sum(meta.row_group(i).total_byte_size
                       for i in range(meta.num_row_groups))
    if uncompressed > budget:
        raise AppException(413, "parquet_too_large",
                           f"Uncompressed size ~{uncompressed // (1024 * 1024)} MB "
                           f"exceeds the in-memory budget")
    return pf.read().to_pandas()
