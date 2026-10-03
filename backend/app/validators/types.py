"""Rule catalog: every check, its parameters and its implementation.

A rule is registered once with a typed parameter model. That single definition
drives three things:
  * validation of the user's YAML (unknown params, wrong types -> lint issues),
  * the rule catalog served to the UI (the visual builder renders forms from it),
  * execution: the check gets the parsed params and returns a Failure or None.

Every check accepts two generic options on top of its own params:
  severity: error | warning   (warnings are reported but don't quarantine rows)
  message:  custom text shown instead of the generated message
"""
from __future__ import annotations

import math
import operator
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd
import regex
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings

Severity = Literal["error", "warning"]
Scope = Literal["column", "dataset"]
AppliesTo = Literal["scalar", "array", "any"]

DTYPES = ["int", "float", "numeric", "bool", "str", "datetime"]
ITEM_TYPES = ["int", "float", "numeric", "bool", "str"]
COMPARE_OPS: dict[str, Callable[[Any, Any], Any]] = {
    "==": operator.eq, "!=": operator.ne,
    "<": operator.lt, "<=": operator.le,
    ">": operator.gt, ">=": operator.ge,
}


def ui(kind: str, **extra) -> dict:
    """json_schema_extra helper: how the visual builder should render a param."""
    return {"kind": kind, **extra}


class BaseParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Severity = Field("error", json_schema_extra=ui("select",
                                                             options=["error", "warning"]))
    message: str | None = Field(None, json_schema_extra=ui("text"))


@dataclass
class CheckContext:
    df: pd.DataFrame
    column: str | None = None

    @property
    def series(self) -> pd.Series:
        assert self.column is not None
        return self.df[self.column]


@dataclass
class Failure:
    message: str
    rows: list[int] = field(default_factory=list)      # empty => column/dataset-level
    values: list[Any] = field(default_factory=list)    # a few offending values


@dataclass
class RuleSpec:
    name: str
    label: str
    description: str
    scope: Scope
    applies_to: AppliesTo
    params: type[BaseParams]
    check: Callable[[CheckContext, Any], Failure | None]


RULES: dict[str, RuleSpec] = {}


def register(name: str, *, label: str, description: str, params: type[BaseParams] = BaseParams,
             scope: Scope = "column", applies_to: AppliesTo = "scalar"):
    def decorator(fn):
        RULES[name] = RuleSpec(name, label, description, scope, applies_to, params, fn)
        return fn
    return decorator


# --- helpers ----------------------------------------------------------------

def _is_missing(value) -> bool:
    """True for a missing scalar; a list/tuple is never 'missing'."""
    if isinstance(value, (list, tuple, dict)):
        return False
    try:
        return value is None or bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _failure_from_mask(series: pd.Series, mask: pd.Series, message: str) -> Failure | None:
    mask = mask.fillna(False).astype(bool)
    if not mask.any():
        return None
    failed = series[mask]
    return Failure(message=message.format(n=int(mask.sum())),
                   rows=[int(i) for i in failed.index],
                   values=[_jsonable(v) for v in failed.head(5).tolist()])


def _failure_from_rows(series: pd.Series, rows: list[int], message: str) -> Failure | None:
    if not rows:
        return None
    return Failure(message=message.format(n=len(rows)), rows=rows,
                   values=[_jsonable(series.loc[r]) for r in rows[:5]])


def _jsonable(value):
    """Make a cell value safe to put into a JSON response."""
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if _is_missing(value):
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "item"):                     # numpy scalar -> python
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _norm_value(value, case_sensitive: bool = True) -> str:
    """Canonical text form so that 1, 1.0 and "1" compare equal."""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)) or hasattr(value, "item"):
        try:
            num = float(value)
            if num.is_integer():
                return str(int(num))
            return repr(num)
        except (TypeError, ValueError):
            pass
    text = str(value).strip()
    return text if case_sensitive else text.casefold()


# --- scalar column rules ----------------------------------------------------

@register("not_null", label="Not null", applies_to="any",
          description="Value must be present (no nulls / empty cells).")
def check_not_null(ctx: CheckContext, p: BaseParams) -> Failure | None:
    s = ctx.series
    mask = s.map(_is_missing)
    return _failure_from_mask(s, mask, "{n} missing value(s) in a required column")


@register("not_blank", label="Not blank",
          description="Text must not be empty or whitespace-only (nulls are ignored).")
def check_not_blank(ctx: CheckContext, p: BaseParams) -> Failure | None:
    s = ctx.series
    mask = s.map(lambda v: isinstance(v, str) and not v.strip())
    return _failure_from_mask(s, mask, "{n} blank value(s)")


class DtypeParams(BaseParams):
    expected: Literal["int", "float", "numeric", "bool", "str", "string", "datetime"] = Field(
        ..., json_schema_extra=ui("select", options=DTYPES))


def _value_matches_type(value, expected: str) -> bool:
    # Coercion is intentional: "5" and 5.0 satisfy int, "5.3" does not.
    if expected in ("str", "string"):
        return isinstance(value, str)
    if expected == "bool":
        if isinstance(value, bool) or (hasattr(value, "dtype") and value.dtype == bool):
            return True
        if isinstance(value, str):
            return value.strip().lower() in ("true", "false", "0", "1", "yes", "no")
        return value in (0, 1)
    if expected == "datetime":
        if isinstance(value, pd.Timestamp):
            return True
        if not isinstance(value, str):
            return False
        return not pd.isna(pd.to_datetime(value, errors="coerce", format="mixed"))
    try:
        num = float(value)
    except (TypeError, ValueError):
        return False
    if math.isnan(num) or math.isinf(num):
        return False
    if expected in ("float", "numeric"):
        return True
    return num == int(num)          # int: must be a whole number


@register("dtype", label="Type", params=DtypeParams,
          description="Each value must be convertible to the expected type.")
def check_dtype(ctx: CheckContext, p: DtypeParams) -> Failure | None:
    s = ctx.series
    if p.expected == "datetime" and pd.api.types.is_datetime64_any_dtype(s):
        return None
    mask = s.map(lambda v: not _is_missing(v) and not _value_matches_type(v, p.expected))
    return _failure_from_mask(s, mask, "{n} value(s) do not conform to type '%s'" % p.expected)


class RangeParams(BaseParams):
    min: float | None = Field(None, json_schema_extra=ui("number"))
    max: float | None = Field(None, json_schema_extra=ui("number"))


@register("range", label="Range", params=RangeParams,
          description="Numeric value must be within [min, max]. Non-numbers fail too.")
def check_range(ctx: CheckContext, p: RangeParams) -> Failure | None:
    s = ctx.series
    numeric = pd.to_numeric(s, errors="coerce")
    present = ~s.map(_is_missing)
    mask = present & numeric.isna()                     # present but not a number
    if p.min is not None:
        mask |= numeric < p.min
    if p.max is not None:
        mask |= numeric > p.max
    bounds = ", ".join(b for b in (f"min={p.min:g}" if p.min is not None else "",
                                   f"max={p.max:g}" if p.max is not None else "") if b)
    return _failure_from_mask(s, mask & present, "{n} value(s) out of range (%s)" % bounds)


@register("unique", label="Unique",
          description="No two rows may share the same value (nulls are ignored).")
def check_unique(ctx: CheckContext, p: BaseParams) -> Failure | None:
    s = ctx.series
    keys = s.map(lambda v: None if _is_missing(v) else _norm_value(v))
    mask = keys.duplicated(keep=False) & keys.notna()
    return _failure_from_mask(s, mask, "{n} row(s) involved in duplicate values")


class AllowedValuesParams(BaseParams):
    values: list[str | int | float | bool] = Field(..., min_length=1,
                                                   json_schema_extra=ui("list"))
    case_sensitive: bool = Field(True, json_schema_extra=ui("boolean"))


@register("allowed_values", label="Allowed values", params=AllowedValuesParams,
          description="Value must be one of a fixed list (an enum / category).")
def check_allowed_values(ctx: CheckContext, p: AllowedValuesParams) -> Failure | None:
    s = ctx.series
    allowed = {_norm_value(v, p.case_sensitive) for v in p.values}
    mask = s.map(lambda v: not _is_missing(v) and _norm_value(v, p.case_sensitive) not in allowed)
    return _failure_from_mask(s, mask, "{n} value(s) not in the allowed list")


class LengthParams(BaseParams):
    min: int | None = Field(None, ge=0, json_schema_extra=ui("number"))
    max: int | None = Field(None, ge=0, json_schema_extra=ui("number"))


@register("length", label="Text length", params=LengthParams,
          description="Length of the text value must be within [min, max] characters.")
def check_length(ctx: CheckContext, p: LengthParams) -> Failure | None:
    s = ctx.series

    def bad(v) -> bool:
        if _is_missing(v):
            return False
        n = len(str(v))
        return (p.min is not None and n < p.min) or (p.max is not None and n > p.max)

    return _failure_from_mask(s, s.map(bad), "{n} value(s) with a disallowed length")


class RegexParams(BaseParams):
    pattern: str = Field(..., min_length=1, json_schema_extra=ui("text"))
    full_match: bool = Field(False, json_schema_extra=ui("boolean"))


@register("regex", label="Pattern (regex)", params=RegexParams,
          description="Value must match a regular expression (ReDoS-safe, with a timeout).")
def check_regex(ctx: CheckContext, p: RegexParams) -> Failure | None:
    s = ctx.series
    compiled = regex.compile(p.pattern)              # validity is checked by the linter
    match = compiled.fullmatch if p.full_match else compiled.search
    failed: list[int] = []
    for idx, value in s.items():
        if _is_missing(value):
            continue
        try:
            if match(str(value), timeout=settings.regex_timeout_sec) is None:
                failed.append(int(idx))
        except TimeoutError:
            return Failure(message="Regex timed out (possible ReDoS) — simplify the pattern")
    return _failure_from_rows(s, failed, "{n} value(s) do not match the pattern")


class DateParams(BaseParams):
    format: str | None = Field(None, json_schema_extra=ui("text", placeholder="%Y-%m-%d"))
    min: str | None = Field(None, json_schema_extra=ui("text", placeholder="2000-01-01"))
    max: str | None = Field(None, json_schema_extra=ui("text", placeholder="2030-12-31"))


def to_datetime(series: pd.Series, fmt: str | None = None) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    as_text = series.map(lambda v: None if _is_missing(v) else str(v))
    return pd.to_datetime(as_text, errors="coerce", format=fmt or "mixed")


@register("date", label="Date", params=DateParams,
          description="Value must be a valid date/time (optionally in a strftime format) "
                      "within [min, max].")
def check_date(ctx: CheckContext, p: DateParams) -> Failure | None:
    s = ctx.series
    parsed = to_datetime(s, p.format)
    if getattr(parsed.dt, "tz", None) is not None:
        parsed = parsed.dt.tz_convert(None)
    present = ~s.map(_is_missing)
    mask = present & parsed.isna()
    if p.min:
        mask |= parsed < pd.Timestamp(p.min)
    if p.max:
        mask |= parsed > pd.Timestamp(p.max)
    what = f"format '{p.format}'" if p.format else "a valid date"
    return _failure_from_mask(s, mask & present, "{n} value(s) are not %s or out of bounds" % what)


class CompareParams(BaseParams):
    op: Literal["==", "!=", "<", "<=", ">", ">="] = Field(
        ..., json_schema_extra=ui("select", options=list(COMPARE_OPS)))
    column: str = Field(..., min_length=1, json_schema_extra=ui("column"))


def _comparable(a: pd.Series, b: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Pick the strongest common interpretation: numbers, then dates, then text."""
    present = ~a.map(_is_missing) & ~b.map(_is_missing)
    for convert in (lambda x: pd.to_numeric(x, errors="coerce"), to_datetime):
        ca, cb = convert(a), convert(b)
        if (ca[present].notna().all() and cb[present].notna().all()):
            return ca, cb
    return a.map(str), b.map(str)


@register("compare", label="Compare with column", params=CompareParams,
          description="Cross-column check, e.g. end_date >= start_date. "
                      "Rows where either side is missing are skipped.")
def check_compare(ctx: CheckContext, p: CompareParams) -> Failure | None:
    s = ctx.series
    if p.column not in ctx.df.columns:
        return Failure(message=f"Column '{p.column}' to compare with was not found")
    other = ctx.df[p.column]
    present = ~s.map(_is_missing) & ~other.map(_is_missing)
    left, right = _comparable(s, other)
    ok = COMPARE_OPS[p.op](left[present], right[present])
    mask = pd.Series(False, index=s.index)
    mask[present] = ~ok.astype(bool)
    return _failure_from_mask(s, mask, "{n} row(s) where %s %s %s is false"
                              % (ctx.column, p.op, p.column))


# --- array rules (list-valued columns, e.g. from JSON) ----------------------

_ELEMENT_TYPES: dict[str, Callable[[object], bool]] = {
    "int": lambda x: isinstance(x, int) and not isinstance(x, bool),
    "float": lambda x: isinstance(x, float),
    "numeric": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
    "str": lambda x: isinstance(x, str),
    "bool": lambda x: isinstance(x, bool),
}


@register("array_length", label="Array length", params=LengthParams, applies_to="array",
          description="Array must contain between min and max elements.")
def check_array_length(ctx: CheckContext, p: LengthParams) -> Failure | None:
    s = ctx.series

    def bad(v) -> bool:
        if _is_missing(v):
            return False
        if not isinstance(v, (list, tuple)):
            return True
        return (p.min is not None and len(v) < p.min) or (p.max is not None and len(v) > p.max)

    return _failure_from_mask(s, s.map(bad), "{n} array(s) with a disallowed length")


class ArrayItemsParams(BaseParams):
    type: Literal["int", "float", "numeric", "bool", "str"] | None = Field(
        None, json_schema_extra=ui("select", options=ITEM_TYPES))
    min: float | None = Field(None, json_schema_extra=ui("number"))
    max: float | None = Field(None, json_schema_extra=ui("number"))


@register("array_items", label="Array items", params=ArrayItemsParams, applies_to="array",
          description="Every element must have the given type and lie within [min, max].")
def check_array_items(ctx: CheckContext, p: ArrayItemsParams) -> Failure | None:
    s = ctx.series
    type_pred = _ELEMENT_TYPES.get(p.type) if p.type else None

    def bad_element(e) -> bool:
        if type_pred and not type_pred(e):
            return True
        if p.min is not None or p.max is not None:
            if not (isinstance(e, (int, float)) and not isinstance(e, bool)):
                return True
            if (p.min is not None and e < p.min) or (p.max is not None and e > p.max):
                return True
        return False

    def bad(v) -> bool:
        if _is_missing(v):
            return False
        if not isinstance(v, (list, tuple)):
            return True
        return any(bad_element(e) for e in v)

    return _failure_from_mask(s, s.map(bad), "{n} array(s) with a disallowed element")


# --- dataset-level rules ----------------------------------------------------

class RowCountParams(BaseParams):
    min: int | None = Field(None, ge=0, json_schema_extra=ui("number"))
    max: int | None = Field(None, ge=0, json_schema_extra=ui("number"))


@register("row_count", label="Row count", params=RowCountParams, scope="dataset",
          applies_to="any", description="The dataset must have between min and max rows.")
def check_row_count(ctx: CheckContext, p: RowCountParams) -> Failure | None:
    n = len(ctx.df)
    if (p.min is not None and n < p.min) or (p.max is not None and n > p.max):
        return Failure(message=f"Dataset has {n} row(s); expected "
                               f"{p.min if p.min is not None else 0}..{p.max or '∞'}")
    return None


class UniqueTogetherParams(BaseParams):
    columns: list[str] = Field(..., min_length=2, json_schema_extra=ui("columns"))


@register("unique_together", label="Unique combination", params=UniqueTogetherParams,
          scope="dataset", applies_to="any",
          description="The combination of these columns must be unique (a composite key).")
def check_unique_together(ctx: CheckContext, p: UniqueTogetherParams) -> Failure | None:
    missing = [c for c in p.columns if c not in ctx.df.columns]
    if missing:
        return Failure(message=f"Column(s) not found: {', '.join(missing)}")
    keys = ctx.df[p.columns].map(lambda v: None if _is_missing(v) else _norm_value(v))
    mask = keys.duplicated(keep=False) & keys.notna().all(axis=1)   # like SQL: nulls never clash
    if not mask.any():
        return None
    rows = [int(i) for i in keys.index[mask]]
    return Failure(message=f"{len(rows)} row(s) share a duplicate ({', '.join(p.columns)})",
                   rows=rows,
                   values=[" | ".join(map(str, keys.loc[r].tolist())) for r in rows[:5]])


# --- catalog for the UI -----------------------------------------------------

def param_specs(model: type[BaseParams]) -> list[dict]:
    specs = []
    for name, f in model.model_fields.items():
        extra = f.json_schema_extra if isinstance(f.json_schema_extra, dict) else {}
        specs.append({
            "name": name,
            "kind": extra.get("kind", "text"),
            "required": f.is_required(),
            "default": None if f.is_required() else f.default,
            "options": extra.get("options"),
            "placeholder": extra.get("placeholder"),
            "common": name in BaseParams.model_fields,
        })
    return specs


def catalog() -> list[dict]:
    return [{
        "name": spec.name,
        "label": spec.label,
        "description": spec.description,
        "scope": spec.scope,
        "applies_to": spec.applies_to,
        "params": param_specs(spec.params),
    } for spec in RULES.values()]
