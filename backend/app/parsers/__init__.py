"""Common ingestion entry point: size limit, format detection by magic bytes, dispatch.

The extension says what the file *claims* to be; the magic bytes say what it
is. Parquet ("PAR1") and XLSX (a ZIP, "PK\\x03\\x04") have reliable signatures,
so a mismatch there is rejected outright. JSON is sanity-checked to start with
an object/array. This stops e.g. a binary Parquet renamed to .csv from
reaching the parsers.

Every loader returns a DataFrame with a clean 0..n-1 RangeIndex: the index *is*
the row number reported in violations and used for exports.
"""
from __future__ import annotations

import pandas as pd

from app.config import settings
from app.errors import AppException
from app.parsers.csv_parser import parse_csv
from app.parsers.excel_parser import parse_excel
from app.parsers.json_parser import parse_json, parse_jsonl
from app.parsers.parquet_parser import parse_parquet

# extension -> canonical format name
EXTENSIONS: dict[str, str] = {
    "csv": "csv",
    "tsv": "csv",
    "txt": "csv",
    "json": "json",
    "jsonl": "jsonl",
    "ndjson": "jsonl",
    "parquet": "parquet",
    "xlsx": "xlsx",
}
SUPPORTED_FORMATS = sorted(set(EXTENSIONS.values()))


def detect_extension_format(filename: str | None) -> str | None:
    name = (filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    return EXTENSIONS.get(ext)


def _detect_content(raw: bytes) -> str | None:
    if raw[:4] == b"PAR1":
        return "parquet"
    if raw[:4] == b"PK\x03\x04":
        return "zip"
    head = raw.lstrip()[:1]
    if head in (b"{", b"["):
        return "json"
    return None  # unknown / plain text (likely CSV)


def load_dataframe(filename: str | None, raw: bytes) -> tuple[pd.DataFrame, str]:
    """Parse an uploaded file. Returns (dataframe, canonical format)."""
    if len(raw) > settings.max_file_bytes:
        raise AppException(413, "file_too_large",
                           f"File exceeds the {settings.max_file_size_mb} MB limit")

    fmt = detect_extension_format(filename)
    if fmt is None:
        raise AppException(415, "unsupported_format",
                           "Supported formats: CSV/TSV, JSON, JSON Lines, Parquet, XLSX")
    detected = _detect_content(raw)

    # Binary signatures are reliable -> enforce a match in both directions.
    if detected == "parquet" and fmt != "parquet":
        raise AppException(415, "format_mismatch",
                           "File content is Parquet but the extension is not .parquet")
    if fmt == "parquet" and detected != "parquet":
        raise AppException(415, "format_mismatch",
                           "Extension is .parquet but the content is not a valid Parquet file")
    if detected == "zip" and fmt != "xlsx":
        raise AppException(415, "format_mismatch",
                           "File content is a ZIP/Excel archive but the extension is not .xlsx")
    if fmt == "xlsx" and detected != "zip":
        raise AppException(415, "format_mismatch",
                           "Extension is .xlsx but the content is not an Excel workbook")
    if fmt in ("json", "jsonl") and raw.strip() and detected != "json":
        raise AppException(415, "format_mismatch",
                           "Extension is JSON but the content does not look like JSON")

    parser = {
        "csv": parse_csv,
        "json": parse_json,
        "jsonl": parse_jsonl,
        "parquet": parse_parquet,
        "xlsx": parse_excel,
    }[fmt]
    df = parser(raw)

    if len(df.columns) > settings.max_columns:
        raise AppException(413, "too_many_columns",
                           f"{len(df.columns)} columns exceeds the limit "
                           f"of {settings.max_columns}")
    if len(df) > settings.max_rows:
        raise AppException(413, "too_many_rows",
                           f"{len(df)} rows exceeds the limit of {settings.max_rows}")

    df.columns = [str(c) for c in df.columns]
    return df.reset_index(drop=True), fmt
