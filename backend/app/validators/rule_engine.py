"""Rule engine: apply a set of declarative rules to a DataFrame.

Rules dict (already parsed from the user's YAML):
    {
      "columns": {
        "age":   {"not_null": {}, "dtype": {"expected": "int"}, "range": {"min": 0, "max": 120}},
        "email": {"not_null": {}, "unique": {}}
      }
    }
Each key under a column is one check; its value is the params passed to the validator.
"""
from __future__ import annotations

import pandas as pd

from app.models.schemas import Violation
from app.validators.types import VALIDATORS


def run_rules(df: pd.DataFrame, rules: dict) -> list[Violation]:
    violations: list[Violation] = []
    columns = (rules or {}).get("columns", {}) or {}

    for column, checks in columns.items():
        if column not in df.columns:
            violations.append(Violation(column=column, rule="column_exists",
                                        message=f"Column '{column}' not found in data"))
            continue
        series = df[column]
        for check_name, params in (checks or {}).items():
            validator = VALIDATORS.get(check_name)
            if validator is None:
                violations.append(Violation(column=column, rule=check_name,
                                            message=f"Unknown rule '{check_name}'"))
                continue
            result = validator(series, column, **(params or {}))
            if result is not None:
                violations.append(result)
    return violations