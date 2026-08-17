"""Common ingestion entry point: size limit, format detection by magic bytes, dispatch.

The extension says what the file *claims* to be; the magic bytes say what it
is. Parquet has a reliable signature ("PAR1"), so a mismatch there is rejected
outright. JSON is sanity-checked to start with an object/array. This stops a
binary Parquet renamed to .csv (or similar) from reaching the parsers.
"""
from __future__ import annotations

import pandas as pd

from app.config import settings
from app.models.schemas import AppException
from app.parsers.csv_parser import parse_csv
from app.parsers.json_parser import parse_json
from app.parsers.parquet_parser import parse_parquet


def _extension(filename: str | None) -> str | None:
    name = (filename or "").lower()
    for ext in ("csv", "json", "parquet"):
        if name.endswith("." + ext):
            return ext
    return None


def _detect_format(raw: bytes) -> str | None:
    if raw[:4] == b"PAR1":
        return "parquet"
    head = raw.lstrip()[:1]
    if head in (b"{", b"["):
        return "json"
    return None  # unknown / plain text (likely CSV)


def load_dataframe(filename: str | None, raw: bytes, nrows: int | None = None) -> pd.DataFrame:
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise AppException(413, "file_too_large",
                           f"File exceeds the {settings.max_file_size_mb} MB limit")

    ext = _extension(filename)
    detected = _detect_format(raw)

    # Parquet magic bytes are reliable -> enforce a match both directions.
    if detected == "parquet" and ext != "parquet":
        raise AppException(415, "format_mismatch",
                           "File content is Parquet but the extension is not .parquet")
    if ext == "parquet" and detected != "parquet":
        raise AppException(415, "format_mismatch",
                           "Extension is .parquet but the content is not a valid Parquet file")
    if ext == "json" and raw.strip() and detected != "json":
        raise AppException(415, "format_mismatch",
                           "Extension is .json but the content does not look like JSON")

    if ext == "csv":
        return parse_csv(raw, nrows=nrows)
    if ext == "json":
        return parse_json(raw, nrows=nrows)
    if ext == "parquet":
        return parse_parquet(raw, nrows=nrows)
    raise AppException(415, "unsupported_format", "Supported formats: CSV, JSON, Parquet")