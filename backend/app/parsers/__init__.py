"""Common ingestion entry point: enforce the size limit and dispatch by format.

Routers call load_dataframe() and stay format-agnostic. Add JSON/Parquet here
later without touching the endpoints.
"""
from __future__ import annotations

import pandas as pd

from app.config import settings
from app.models.schemas import AppException
from app.parsers.csv_parser import parse_csv


def load_dataframe(filename: str | None, raw: bytes, nrows: int | None = None) -> pd.DataFrame:
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise AppException(413, "file_too_large",
                           f"File exceeds the {settings.max_file_size_mb} MB limit")

    name = (filename or "").lower()
    if name.endswith(".csv"):
        return parse_csv(raw, nrows=nrows)
    raise AppException(415, "unsupported_format",
                       "Only CSV is supported so far (JSON/Parquet coming later)")