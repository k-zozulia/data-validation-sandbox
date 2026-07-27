"""Turn a dataset profile into a starter set of validation rules (YAML).

Heuristics are intentionally conservative: the goal is a helpful first draft the
user then edits, not a perfect ruleset. Also hosts YAML (de)serialization for the
rules, with a clean 4xx on malformed YAML from the editor.
"""
from __future__ import annotations

import yaml

from app.models.schemas import AppException, DatasetProfile

# If a column is almost never null, suggest it is required.
_NULL_REQUIRED_THRESHOLD_PCT = 5.0


def _map_dtype(pandas_dtype: str) -> str | None:
    d = pandas_dtype.lower()
    if d.startswith("int"):
        return "int"
    if d.startswith("float"):
        return "numeric"
    if d.startswith("bool"):
        return "bool"
    if "datetime" in d:
        return "datetime"
    if d.startswith(("object", "string", "str")):
        return "str"
    return None


def generate_rules(profile: DatasetProfile) -> dict:
    columns: dict[str, dict] = {}

    for name, col in profile.columns.items():
        checks: dict[str, dict] = {}

        if col.null_pct < _NULL_REQUIRED_THRESHOLD_PCT:
            checks["not_null"] = {}

        rule_dtype = _map_dtype(col.dtype)
        if rule_dtype:
            checks["dtype"] = {"expected": rule_dtype}

        if col.min is not None and col.max is not None:
            checks["range"] = {"min": col.min, "max": col.max}

        non_null = profile.row_count - col.null_count
        if non_null > 1 and col.unique_count == non_null:
            checks["unique"] = {}

        if checks:
            columns[name] = checks

    return {"columns": columns}


def rules_to_yaml(rules: dict) -> str:
    return yaml.safe_dump(rules, sort_keys=False, allow_unicode=True)


def parse_rules_yaml(text: str) -> dict:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise AppException(400, "invalid_yaml", f"Could not parse rules YAML: {exc}")
    if data is None:
        return {"columns": {}}
    if not isinstance(data, dict):
        raise AppException(400, "invalid_yaml", "Rules YAML must be a mapping at the top level")
    return data