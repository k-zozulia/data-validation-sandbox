"""Common ingestion entry point: enforce the size limit and dispatch by format.

Routers/worker call load_dataframe() and stay format-agnostic. Adding a new
format is a single branch here plus its parser module.
"""
from __future__ import annotations

import pandas as pd

from app.config import settings
from app.models.schemas import AppException
from app.parsers.csv_parser import parse_csv
from app.parsers.json_parser import parse_json
from app.parsers.parquet_parser import parse_parquet


def load_dataframe(filename: str | None, raw: bytes, nrows: int | None = None) -> pd.DataFrame:
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise AppException(413, "file_too_large",
                           f"File exceeds the {settings.max_file_size_mb} MB limit")

    name = (filename or "").lower()
    if name.endswith(".csv"):
        return parse_csv(raw, nrows=nrows)
    if name.endswith(".json"):
        return parse_json(raw, nrows=nrows)
    if name.endswith(".parquet"):
        return parse_parquet(raw, nrows=nrows)
    raise AppException(415, "unsupported_format",
                       "Supported formats: CSV, JSON, Parquet")