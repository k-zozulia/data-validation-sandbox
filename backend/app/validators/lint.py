"""Static checks of a rules document before anything runs.

`compile_rules` turns the parsed YAML into a flat list of executable checks and
collects issues with a path (and the YAML line, when the source is known) so
the editor can underline the exact spot.

Document shape (v1 files — only `columns:` — remain valid):

    columns:
      age:
        not_null: {}                # {} / null / true => enabled with defaults
        range: {min: 0, max: 120, severity: warning}
      end_date:
        compare: {op: ">=", column: start_date}
    dataset:
      row_count: {min: 1}
      unique_together: {columns: [first_name, last_name]}
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import regex
from pydantic import BaseModel, ValidationError

from app.validators.types import RULES, BaseParams, RuleSpec

TOP_LEVEL_KEYS = {"version", "description", "columns", "dataset"}


class LintIssue(BaseModel):
    path: list[str | int]
    message: str
    severity: str = "error"           # error | warning
    line: int | None = None


@dataclass
class PlannedCheck:
    spec: RuleSpec
    params: BaseParams
    column: str | None                # None for dataset-level checks
    path: list[str]


def _params_or_issue(spec: RuleSpec, raw: Any, path: list) -> tuple[BaseParams | None,
                                                                  list[LintIssue]]:
    if raw is None or raw is True:
        raw = {}
    if not isinstance(raw, dict):
        return None, [LintIssue(path=path, message=f"Parameters of '{spec.name}' must be a "
                                                   "mapping, e.g. {min: 0}")]
    try:
        params = spec.params.model_validate(raw)
    except ValidationError as exc:
        issues = []
        for err in exc.errors():
            loc = [str(x) for x in err["loc"]]
            where = ".".join(loc) or spec.name
            msg = err["msg"]
            if err["type"] == "extra_forbidden":
                allowed = ", ".join(spec.params.model_fields)
                msg = f"Unknown parameter (allowed: {allowed})"
            issues.append(LintIssue(path=path + loc[:1], message=f"{where}: {msg}"))
        return None, issues
    return params, _semantic_issues(spec, params, path)


def _semantic_issues(spec: RuleSpec, p: Any, path: list) -> list[LintIssue]:
    issues: list[LintIssue] = []
    lo, hi = getattr(p, "min", None), getattr(p, "max", None)
    if spec.name == "date":
        for key in ("min", "max"):
            value = getattr(p, key)
            if value:
                try:
                    pd.Timestamp(value)
                except (ValueError, TypeError):
                    issues.append(LintIssue(path=path + [key],
                                            message=f"'{value}' is not a valid date"))
        if not issues and lo and hi and pd.Timestamp(lo) > pd.Timestamp(hi):
            issues.append(LintIssue(path=path, message="min is after max"))
    elif lo is not None and hi is not None and lo > hi:
        issues.append(LintIssue(path=path, message=f"min ({lo}) is greater than max ({hi})"))
    if spec.name == "regex":
        try:
            regex.compile(p.pattern)
        except regex.error as exc:
            issues.append(LintIssue(path=path + ["pattern"], message=f"Invalid regex: {exc}"))
    return issues


def compile_rules(rules: Any, columns: list[str] | None = None
                  ) -> tuple[list[PlannedCheck], list[LintIssue]]:
    """Validate a parsed rules document. `columns`, when given, enables
    "column not found" warnings against the actual dataset."""
    checks: list[PlannedCheck] = []
    issues: list[LintIssue] = []
    known = set(columns) if columns is not None else None

    if rules is None:
        return checks, issues
    if not isinstance(rules, dict):
        return checks, [LintIssue(path=[], message="Rules must be a mapping at the top level")]

    for key in rules:
        if key not in TOP_LEVEL_KEYS:
            issues.append(LintIssue(path=[key], severity="warning",
                                    message=f"Unknown top-level key '{key}' is ignored "
                                            "(expected: columns, dataset)"))

    cols = rules.get("columns") or {}
    if not isinstance(cols, dict):
        issues.append(LintIssue(path=["columns"], message="'columns' must be a mapping "
                                                          "of column name -> checks"))
        cols = {}

    for column, col_checks in cols.items():
        column = str(column)
        cpath = ["columns", column]
        if known is not None and column not in known:
            issues.append(LintIssue(path=cpath, severity="warning",
                                    message=f"Column '{column}' is not in this dataset"))
        if col_checks is None:
            continue
        if not isinstance(col_checks, dict):
            issues.append(LintIssue(path=cpath, message="Checks must be a mapping, "
                                                        "e.g. {not_null: {}}"))
            continue
        for name, raw in col_checks.items():
            path = cpath + [str(name)]
            spec = RULES.get(str(name))
            if spec is None:
                issues.append(LintIssue(path=path, message=f"Unknown rule '{name}'"))
                continue
            if spec.scope != "column":
                issues.append(LintIssue(path=path, message=f"'{name}' is a dataset-level "
                                                           "rule; put it under 'dataset:'"))
                continue
            if raw is False:
                continue                                   # explicitly disabled
            params, found = _params_or_issue(spec, raw, path)
            issues.extend(found)
            if params is None:
                continue
            if spec.name == "compare" and known is not None and params.column not in known:
                issues.append(LintIssue(path=path + ["column"], severity="warning",
                                        message=f"Column '{params.column}' is not "
                                                "in this dataset"))
            if not any(i.severity == "error" for i in found):
                checks.append(PlannedCheck(spec, params, column, path))

    ds = rules.get("dataset") or {}
    if not isinstance(ds, dict):
        issues.append(LintIssue(path=["dataset"], message="'dataset' must be a mapping"))
        ds = {}
    for name, raw in ds.items():
        path = ["dataset", str(name)]
        spec = RULES.get(str(name))
        if spec is None or spec.scope != "dataset":
            issues.append(LintIssue(path=path, message=f"Unknown dataset-level rule '{name}'"))
            continue
        if raw is False:
            continue
        params, found = _params_or_issue(spec, raw, path)
        issues.extend(found)
        if params is not None and not any(i.severity == "error" for i in found):
            checks.append(PlannedCheck(spec, params, None, path))

    return checks, issues
