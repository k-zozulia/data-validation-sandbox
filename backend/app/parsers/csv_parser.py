"""CSV parsing with a UTF-8 -> CP1251 fallback and clean errors.

Pass nrows to read only a sample instead of loading the whole file.
"""
from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

import pandas as pd

from app.config import settings
from app.models.schemas import AppException


def parse_csv(source: str | bytes | BinaryIO, nrows: int | None = None) -> pd.DataFrame:
    raw = _read_bytes(source)
    if not raw.strip():
        raise AppException(400, "empty_file", "The uploaded CSV is empty")

    df = None
    for encoding in ("utf-8", "cp1251"):
        try:
            df = pd.read_csv(BytesIO(raw), nrows=nrows, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            raise AppException(400, "empty_file", "The CSV has no columns or rows")
        except pd.errors.ParserError as exc:
            raise AppException(400, "invalid_csv", f"Could not parse CSV: {exc}")

    if df is None:
        raise AppException(400, "bad_encoding",
                           "Could not decode the file as UTF-8 or CP1251")
    if len(df.columns) > settings.max_columns:
        raise AppException(413, "too_many_columns",
                           f"{len(df.columns)} columns exceeds the limit "
                           f"of {settings.max_columns}")
    return df


def _read_bytes(source: str | bytes | BinaryIO) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, str):
        with open(source, "rb") as fh:
            return fh.read()
    return source.read()