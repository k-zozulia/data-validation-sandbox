"""JSON parsing with nested-object flattening and a depth guard."""
from __future__ import annotations

import json
import pandas as pd

from app.config import settings
from app.models.schemas import AppException


def _depth(obj) -> int:
    if isinstance(obj, dict):
        return 1 + max((_depth(v) for v in obj.values()), default=0)
    if isinstance(obj, list):
        return 1 + max((_depth(v) for v in obj), default=0)
    return 0


def parse_json(source: bytes, nrows: int | None = None) -> pd.DataFrame:
    try:
        data = json.loads(source.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AppException(400, "invalid_json", f"Could not parse JSON: {exc}")

    if isinstance(data, dict):
        records = [data]
    elif isinstance(data, list):
        records = data
    else:
        raise AppException(400, "invalid_json",
                           "JSON must be an object or an array of objects")
    if not records:
        raise AppException(400, "empty_file", "The JSON contains no records")

    max_depth = max(_depth(r) for r in records)
    if max_depth > settings.max_json_depth:
        raise AppException(400, "json_too_deep",
                           f"Nesting depth {max_depth} exceeds the limit "
                           f"of {settings.max_json_depth}")

    if nrows is not None:
        records = records[:nrows]

    df = pd.json_normalize(records)
    if len(df.columns) > settings.max_columns:
        raise AppException(413, "too_many_columns",
                           f"{len(df.columns)} columns exceeds the limit "
                           f"of {settings.max_columns}")
    return df