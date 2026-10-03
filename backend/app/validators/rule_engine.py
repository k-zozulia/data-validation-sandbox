"""Rule engine: apply a compiled rules document to a DataFrame.

Produces two views of the same result:
  * violations  – one entry per failed check (what the summary/charts show),
  * row_issues  – row number -> [(column, rule, severity)] (what the data grid
                  highlights and what decides clean vs. quarantine).
Rows with at least one *error* go to quarantine; warnings are only reported.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd

from app.config import settings
from app.errors import AppException
from app.models.schemas import Violation
from app.validators.lint import LintIssue, PlannedCheck, compile_rules
from app.validators.types import CheckContext

DATASET_COLUMN = "(dataset)"
RowIssue = tuple[str, str, str]          # (column, rule, severity)


@dataclass
class EngineResult:
    rows_checked: int
    checks: list[PlannedCheck]
    violations: list[Violation] = field(default_factory=list)
    row_issues: dict[int, list[RowIssue]] = field(default_factory=dict)

    def summary(self, dataset_rows: int) -> dict:
        error_rows = {r for r, items in self.row_issues.items()
                      if any(sev == "error" for _, _, sev in items)}
        warning_rows = {r for r, items in self.row_issues.items()
                        if any(sev == "warning" for _, _, sev in items)}
        clean = self.rows_checked - len(error_rows)

        per_column: dict[str, dict] = {}
        for check in self.checks:
            col = check.column or DATASET_COLUMN
            per_column.setdefault(col, {"checks": 0, "failed_checks": 0,
                                        "error_rows": 0, "warning_rows": 0})
            per_column[col]["checks"] += 1
        for v in self.violations:
            stats = per_column.setdefault(v.column, {"checks": 0, "failed_checks": 0,
                                                     "error_rows": 0, "warning_rows": 0})
            stats["failed_checks"] += 1
        for items in self.row_issues.values():
            for col in {c for c, _, sev in items if sev == "error"}:
                per_column[col]["error_rows"] += 1
            for col in {c for c, _, sev in items if sev == "warning"}:
                per_column[col]["warning_rows"] += 1

        failed_checks = len(self.violations)
        return {
            "dataset_rows": dataset_rows,
            "rows_checked": self.rows_checked,
            "clean_rows": clean,
            "quarantine_rows": len(error_rows),
            "warning_rows": len(warning_rows),
            "warning_only_rows": len(warning_rows - error_rows),
            "checks_total": len(self.checks),
            "checks_failed": failed_checks,
            "checks_passed": max(len(self.checks) - failed_checks, 0),
            "errors": sum(1 for v in self.violations if v.severity == "error"),
            "warnings": sum(1 for v in self.violations if v.severity == "warning"),
            "total_failures": sum(v.failed_count for v in self.violations),
            "score": round(clean / self.rows_checked * 100, 2) if self.rows_checked else 100.0,
            "rules_failed": sorted({v.rule for v in self.violations}),
            "columns_flagged": sorted({v.column for v in self.violations}),
            "columns": per_column,
        }


def compile_or_raise(rules: dict, columns: list[str] | None = None) -> list[PlannedCheck]:
    checks, issues = compile_rules(rules, columns)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        raise AppException(422, "invalid_rules",
                           f"{len(errors)} problem(s) in the rules — fix them and retry",
                           extra={"issues": [i.model_dump() for i in issues]})
    return checks


def run_rules(df: pd.DataFrame, rules: dict,
              on_progress: Callable[[float], None] | None = None) -> EngineResult:
    checks = compile_or_raise(rules)
    result = EngineResult(rows_checked=len(df), checks=checks)
    cap = settings.max_failed_rows_per_violation

    for i, check in enumerate(checks):
        p = check.params
        column = check.column or DATASET_COLUMN

        if check.column is not None and check.column not in df.columns:
            result.violations.append(Violation(
                column=column, rule="column_exists", severity=p.severity,
                message=p.message or f"Column '{check.column}' not found in data"))
        else:
            failure = check.spec.check(CheckContext(df=df, column=check.column), p)
            if failure is not None:
                result.violations.append(Violation(
                    column=column, rule=check.spec.name, severity=p.severity,
                    message=p.message or failure.message,
                    failed_count=len(failure.rows),
                    failed_rows=failure.rows[:cap],
                    sample_values=failure.values,
                ))
                for row in failure.rows:
                    result.row_issues.setdefault(row, []).append(
                        (column, check.spec.name, p.severity))

        if on_progress:
            on_progress((i + 1) / max(len(checks), 1))

    # Dedupe "column_exists" if several checks target the same missing column.
    seen: set[tuple[str, str]] = set()
    unique: list[Violation] = []
    for v in result.violations:
        key = (v.column, v.rule)
        if v.rule == "column_exists" and key in seen:
            continue
        seen.add(key)
        unique.append(v)
    result.violations = unique
    return result


__all__ = ["EngineResult", "LintIssue", "compile_or_raise", "run_rules", "DATASET_COLUMN"]
