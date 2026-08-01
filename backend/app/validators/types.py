"""Individual validator functions, registered by rule name."""

from __future__ import annotations

from typing import Callable

import pandas as pd
import regex
from pandas.api import types as pdt

from app.models.schemas import Violation

VALIDATORS: dict[str, Callable[..., Violation | None]] = {}

# Per-value guard against catastrophic backtracking (ReDoS). The `regex` library
# supports a timeout directly, which is thread-safe (unlike signal-based guards).
_REGEX_TIMEOUT_SEC = 1.0


def register(name: str):
    def decorator(fn: Callable[..., Violation | None]):
        VALIDATORS[name] = fn
        return fn
    return decorator


def _rows(mask: pd.Series) -> list[int]:
    """Row indices where the boolean mask is True."""
    return [int(i) for i in mask[mask].index.tolist()]


def _is_missing(value) -> bool:
    """True for a missing scalar; a list/tuple is never 'missing'."""
    if isinstance(value, (list, tuple)):
        return False
    return value is None or pd.isna(value)


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


@register("regex")
def check_regex(series: pd.Series, column: str, pattern: str) -> Violation | None:
    try:
        compiled = regex.compile(pattern)
    except regex.error as exc:
        return Violation(column=column, rule="regex",
                         message=f"Invalid regex pattern: {exc}")
    failed: list[int] = []
    for idx, value in series.items():
        if pd.isna(value):
            continue
        try:
            if compiled.search(str(value), timeout=_REGEX_TIMEOUT_SEC) is None:
                failed.append(int(idx))
        except TimeoutError:
            return Violation(column=column, rule="regex",
                             message="Regex timed out (possible ReDoS) — check the pattern")
    if not failed:
        return None
    return Violation(column=column, rule="regex",
                     message=f"{len(failed)} value(s) do not match the pattern",
                     failed_count=len(failed), failed_rows=failed)


# --- Array validators (for list-valued columns coming from JSON) ---

_ELEMENT_TYPES: dict[str, Callable[[object], bool]] = {
    "int": lambda x: isinstance(x, int) and not isinstance(x, bool),
    "float": lambda x: isinstance(x, float),
    "numeric": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
    "str": lambda x: isinstance(x, str),
    "bool": lambda x: isinstance(x, bool),
}


@register("array_length")
def check_array_length(series: pd.Series, column: str,
                       min=None, max=None) -> Violation | None:
    failed: list[int] = []
    for idx, value in series.items():
        if _is_missing(value):
            continue
        if not isinstance(value, (list, tuple)):
            failed.append(int(idx))
            continue
        n = len(value)
        if (min is not None and n < min) or (max is not None and n > max):
            failed.append(int(idx))
    if not failed:
        return None
    return Violation(column=column, rule="array_length",
                     message=f"{len(failed)} array(s) with a disallowed length",
                     failed_count=len(failed), failed_rows=failed)


@register("array_items")
def check_array_items(series: pd.Series, column: str,
                      type=None, min=None, max=None) -> Violation | None:
    type_pred = _ELEMENT_TYPES.get(type) if type else None
    if type and type_pred is None:
        return Violation(column=column, rule="array_items",
                         message=f"Unknown item type '{type}'")

    failed: list[int] = []
    for idx, value in series.items():
        if _is_missing(value):
            continue
        if not isinstance(value, (list, tuple)):
            failed.append(int(idx))
            continue
        for element in value:
            is_number = isinstance(element, (int, float)) and not isinstance(element, bool)
            if type_pred and not type_pred(element):
                failed.append(int(idx)); break
            if min is not None or max is not None:
                if not is_number:
                    failed.append(int(idx)); break
                if (min is not None and element < min) or (max is not None and element > max):
                    failed.append(int(idx)); break
    if not failed:
        return None
    return Violation(column=column, rule="array_items",
                     message=f"{len(failed)} array(s) with a disallowed element",
                     failed_count=len(failed), failed_rows=failed)