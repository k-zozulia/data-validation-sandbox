"""JSON / JSON Lines parsing with nested-object flattening and a depth guard."""
from __future__ import annotations

import json

import pandas as pd

from app.config import settings
from app.errors import AppException


def _depth(obj) -> int:
    if isinstance(obj, dict):
        return 1 + max((_depth(v) for v in obj.values()), default=0)
    if isinstance(obj, list):
        return 1 + max((_depth(v) for v in obj), default=0)
    return 0


def _records_to_frame(records: list) -> pd.DataFrame:
    if not records:
        raise AppException(400, "empty_file", "The JSON contains no records")
    if not all(isinstance(r, dict) for r in records):
        raise AppException(400, "invalid_json", "Every JSON record must be an object")

    max_depth = max(_depth(r) for r in records)
    if max_depth > settings.max_json_depth:
        raise AppException(400, "json_too_deep",
                           f"Nesting depth {max_depth} exceeds the limit "
                           f"of {settings.max_json_depth}")
    return pd.json_normalize(records)


def parse_json(raw: bytes) -> pd.DataFrame:
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AppException(400, "invalid_json", f"Could not parse JSON: {exc}")

    if isinstance(data, dict):
        # {"data": [...]} style wrappers: take the single list-of-objects value.
        lists = [v for v in data.values() if isinstance(v, list)]
        records = lists[0] if len(data) == 1 and len(lists) == 1 else [data]
    elif isinstance(data, list):
        records = data
    else:
        raise AppException(400, "invalid_json",
                           "JSON must be an object or an array of objects")
    return _records_to_frame(records)


def parse_jsonl(raw: bytes) -> pd.DataFrame:
    records = []
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppException(400, "invalid_json", f"Could not decode JSON Lines: {exc}")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise AppException(400, "invalid_json", f"Line {lineno}: {exc.msg}")
    return _records_to_frame(records)
