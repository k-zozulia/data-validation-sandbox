"""Rules YAML: parsing (with line numbers for the editor) and starter-rule generation.

Generation heuristics are intentionally conservative: the goal is a helpful
first draft the user then edits, not a perfect ruleset.
"""
from __future__ import annotations

import math

import yaml

from app.errors import AppException
from app.models.schemas import ColumnProfile, DatasetProfile
from app.validators.lint import LintIssue

# If a column is almost never null, suggest it is required.
_NULL_REQUIRED_THRESHOLD_PCT = 5.0
# Low-cardinality text columns become an allowed_values list.
_CATEGORY_MAX_VALUES = 10
_CATEGORY_MIN_ROWS = 20

SEMANTIC_PATTERNS = {
    "email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    "url": r"^https?://\S+$",
    "uuid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    "phone": r"^\+?[0-9][0-9 ()\-]{6,18}[0-9]$",
}


# --- (de)serialization -------------------------------------------------------

def rules_to_yaml(rules: dict) -> str:
    return yaml.safe_dump(rules, sort_keys=False, allow_unicode=True, width=100)


def parse_rules_yaml(text: str) -> dict:
    """Parse or raise a clean 400 with the YAML error position."""
    try:
        data = yaml.safe_load(text or "")
    except yaml.YAMLError as exc:
        line = getattr(getattr(exc, "problem_mark", None), "line", None)
        raise AppException(400, "invalid_yaml", f"Could not parse rules YAML: {exc}",
                           extra={"issues": [LintIssue(
                               path=[], message=str(getattr(exc, "problem", None) or exc),
                               line=line + 1 if line is not None else None).model_dump()]})
    if data is None:
        return {"columns": {}}
    if not isinstance(data, dict):
        raise AppException(400, "invalid_yaml", "Rules YAML must be a mapping at the top level")
    return data


def yaml_line(text: str, path: list) -> int | None:
    """1-based line of the node at `path` in the YAML source (best effort)."""
    try:
        node = yaml.compose(text or "")
    except yaml.YAMLError:
        return None
    line = node.start_mark.line + 1 if node is not None else None
    for key in path:
        if not isinstance(node, yaml.MappingNode):
            break
        for k_node, v_node in node.value:
            if str(k_node.value) == str(key):
                line = k_node.start_mark.line + 1
                node = v_node
                break
        else:
            break
    return line


def attach_lines(text: str, issues: list[LintIssue]) -> list[LintIssue]:
    for issue in issues:
        if issue.line is None:
            issue.line = yaml_line(text, issue.path)
    return issues


# --- starter rules ------------------------------------------------------------

def _map_dtype(col: ColumnProfile) -> str | None:
    return {
        "integer": "int",
        "float": "numeric",
        "boolean": "bool",
        "datetime": "datetime",
        "string": "str",
    }.get(col.inferred_type)


def _round_down(x: float) -> float:
    return float(math.floor(x))


def _round_up(x: float) -> float:
    return float(math.ceil(x))


def _column_rules(col: ColumnProfile, row_count: int) -> dict:
    checks: dict[str, dict] = {}
    non_null = row_count - col.null_count

    if row_count and col.null_pct < _NULL_REQUIRED_THRESHOLD_PCT:
        checks["not_null"] = {}

    if col.is_array:
        if col.min_length is not None and col.max_length is not None:
            checks["array_length"] = {"min": col.min_length, "max": col.max_length}
        return checks

    if col.semantic_type == "date":
        checks["date"] = {}
    elif col.semantic_type in SEMANTIC_PATTERNS:
        checks["regex"] = {"pattern": SEMANTIC_PATTERNS[col.semantic_type]}
    else:
        rule_dtype = _map_dtype(col)
        if rule_dtype:
            checks["dtype"] = {"expected": rule_dtype}

    if col.min is not None and col.max is not None and col.inferred_type in ("integer", "float"):
        checks["range"] = {"min": _round_down(col.min), "max": _round_up(col.max)}

    if (col.inferred_type == "string" and col.semantic_type is None
            and row_count >= _CATEGORY_MIN_ROWS
            and 0 < col.unique_count <= _CATEGORY_MAX_VALUES
            and col.unique_count < non_null / 2):
        checks["allowed_values"] = {"values": [t.value for t in col.top_values]}

    if non_null > 1 and col.unique_count == non_null and col.inferred_type in (
            "integer", "string"):
        checks["unique"] = {}

    return checks


def generate_rules(profile: DatasetProfile) -> dict:
    columns: dict[str, dict] = {}
    for name, col in profile.columns.items():
        checks = _column_rules(col, profile.row_count)
        if checks:
            columns[name] = checks
    rules: dict = {"columns": columns}
    if profile.row_count:
        rules["dataset"] = {"row_count": {"min": 1}}
    return rules
