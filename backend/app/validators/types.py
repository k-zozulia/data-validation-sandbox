"""Individual validator functions, registered by rule name.

Each validator inspects one column (a pandas Series) and returns a Violation if
the rule is broken, or None if it passes.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd
from pandas.api import types as pdt

from app.models.schemas import Violation

VALIDATORS: dict[str, Callable[..., Violation | None]] = {}


def register(name: str):
    def decorator(fn: Callable[..., Violation | None]):
        VALIDATORS[name] = fn
        return fn
    return decorator


def _rows(mask: pd.Series) -> list[int]:
    """Row indices where the boolean mask is True."""
    return [int(i) for i in mask[mask].index.tolist()]


@register("not_null")
def check_not_null(series: pd.Series, column: str) -> Violation | None:
    mask = series.isna()
    if not mask.any():
        return None
    rows = _rows(mask)
    return Violation(column=column, rule="not_null",
                     message=f"{len(rows)} null value(s) in a required column",
                     failed_count=len(rows), failed_rows=rows)


_DTYPE_CHECKS: dict[str, Callable[[pd.Series], bool]] = {
    "int": pdt.is_integer_dtype,
    "float": pdt.is_float_dtype,
    "numeric": pdt.is_numeric_dtype,
    "bool": pdt.is_bool_dtype,
    "str": lambda s: pdt.is_object_dtype(s) or pdt.is_string_dtype(s),
    "string": lambda s: pdt.is_object_dtype(s) or pdt.is_string_dtype(s),
    "datetime": pdt.is_datetime64_any_dtype,
}


@register("dtype")
def check_dtype(series: pd.Series, column: str, expected: str) -> Violation | None:
    check = _DTYPE_CHECKS.get(expected)
    if check is None:
        return Violation(column=column, rule="dtype",
                         message=f"Unknown expected dtype '{expected}'")
    if check(series):
        return None
    return Violation(column=column, rule="dtype",
                     message=f"Column dtype is '{series.dtype}', expected '{expected}'",
                     failed_count=int(series.notna().sum()))


@register("range")
def check_range(series: pd.Series, column: str,
                min=None, max=None) -> Violation | None:
    numeric = pd.to_numeric(series, errors="coerce")
    mask = pd.Series(False, index=series.index)
    if min is not None:
        mask |= numeric < min
    if max is not None:
        mask |= numeric > max
    mask &= series.notna()  # nulls are a not_null concern, not a range concern
    if not mask.any():
        return None
    rows = _rows(mask)
    bounds = [b for b in (f"min={min}" if min is not None else None,
                          f"max={max}" if max is not None else None) if b]
    return Violation(column=column, rule="range",
                     message=f"{len(rows)} value(s) out of range ({', '.join(bounds)})",
                     failed_count=len(rows), failed_rows=rows)


@register("unique")
def check_unique(series: pd.Series, column: str) -> Violation | None:
    mask = series.duplicated(keep=False) & series.notna()
    if not mask.any():
        return None
    rows = _rows(mask)
    return Violation(column=column, rule="unique",
                     message=f"{len(rows)} row(s) involved in duplicate values",
                     failed_count=len(rows), failed_rows=rows)