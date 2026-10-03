"""CSV parsing with delimiter sniffing, a UTF-8 -> CP1251 fallback and clean errors."""
from __future__ import annotations

import csv
from io import StringIO

import pandas as pd

from app.errors import AppException

_DELIMITERS = ",;\t|"


def sniff_delimiter(text: str) -> str:
    """Guess the delimiter from the first lines; default to a comma."""
    sample = "\n".join(text.splitlines()[:50])
    try:
        return csv.Sniffer().sniff(sample, delimiters=_DELIMITERS).delimiter
    except csv.Error:
        return ","


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise AppException(400, "bad_encoding", "Could not decode the file as UTF-8 or CP1251")


def parse_csv(raw: bytes) -> pd.DataFrame:
    if not raw.strip():
        raise AppException(400, "empty_file", "The uploaded CSV is empty")

    text = _decode(raw)
    sep = sniff_delimiter(text[:64 * 1024])
    try:
        return pd.read_csv(StringIO(text), sep=sep)
    except pd.errors.EmptyDataError:
        raise AppException(400, "empty_file", "The CSV has no columns or rows")
    except pd.errors.ParserError as exc:
        raise AppException(400, "invalid_csv", f"Could not parse CSV: {exc}")
