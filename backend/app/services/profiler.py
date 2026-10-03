"""Compute per-column statistics for a DataFrame."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import regex
from pandas.api import types as pdt

from app.models.schemas import ColumnProfile, DatasetProfile, HistogramBin, TopValue
from app.validators.types import _is_missing, _jsonable

_TOP_N = 10
_HIST_BINS = 12
_SEMANTIC_MIN_SHARE = 0.9          # share of non-null values that must match
_SEMANTIC_SAMPLE = 2_000

_SEMANTIC_RE = {
    "email": regex.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    "url": regex.compile(r"^https?://\S+$"),
    "uuid": regex.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                          r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"),
    # Order matters: "2024-01-01" also looks like a phone number.
    "date": regex.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?.*)?$"
                          r"|^\d{1,2}[./]\d{1,2}[./]\d{4}$"),
    "phone": regex.compile(r"^\+?[0-9][0-9 ()\-]{6,18}[0-9]$"),
}


def _finite(x) -> float | None:
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _has_list_values(series: pd.Series) -> bool:
    """True if any non-null value is a list/tuple (unhashable, no nunique/min/max)."""
    return any(isinstance(v, (list, tuple, np.ndarray)) for v in series)


def _inferred_type(series: pd.Series, non_null: pd.Series, is_array: bool) -> str:
    if is_array:
        return "array"
    if non_null.empty:
        return "empty"
    if pdt.is_bool_dtype(series):
        return "boolean"
    if pdt.is_integer_dtype(series):
        return "integer"
    if pdt.is_float_dtype(series):
        # Floats that are all whole numbers are ints with NaNs (a pandas artifact).
        return "integer" if (non_null == non_null.round()).all() else "float"
    if pdt.is_datetime64_any_dtype(series):
        return "datetime"
    kinds = {type(v).__name__ for v in non_null.head(_SEMANTIC_SAMPLE)}
    if kinds <= {"str"}:
        return "string"
    if kinds <= {"bool"}:
        return "boolean"
    return "mixed"


def _semantic_type(texts: pd.Series) -> str | None:
    sample = texts.head(_SEMANTIC_SAMPLE)
    if sample.empty:
        return None
    for name, pattern in _SEMANTIC_RE.items():
        hits = sum(1 for v in sample if pattern.match(v))
        if hits / len(sample) >= _SEMANTIC_MIN_SHARE:
            return name
    return None


def _histogram(numeric: pd.Series) -> list[HistogramBin]:
    values = numeric.dropna().to_numpy(dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return []
    lo, hi = float(values.min()), float(values.max())
    if lo == hi:
        return [HistogramBin(start=lo, end=hi, count=int(values.size))]
    counts, edges = np.histogram(values, bins=_HIST_BINS)
    return [HistogramBin(start=float(edges[i]), end=float(edges[i + 1]), count=int(c))
            for i, c in enumerate(counts)]


def _top_values(non_null: pd.Series) -> list[TopValue]:
    counts = non_null.map(str).value_counts().head(_TOP_N)
    return [TopValue(value=str(k), count=int(v)) for k, v in counts.items()]


def profile_column(series: pd.Series, n_rows: int) -> ColumnProfile:
    missing = series.map(_is_missing)
    null_count = int(missing.sum())
    non_null = series[~missing]
    is_array = _has_list_values(non_null)
    inferred = _inferred_type(series, non_null, is_array)

    p = ColumnProfile(
        dtype=str(series.dtype),
        inferred_type=inferred,
        null_count=null_count,
        null_pct=round(null_count / n_rows * 100, 2) if n_rows else 0.0,
        unique_count=0,
        is_array=is_array,
        sample_values=[_jsonable(v) for v in non_null.head(3).tolist()],
    )

    if is_array:
        lengths = non_null.map(lambda v: len(v) if hasattr(v, "__len__") else 0)
        if not lengths.empty:
            p.min_length, p.max_length = int(lengths.min()), int(lengths.max())
        return p

    p.unique_count = int(non_null.map(str).nunique())
    p.unique_pct = round(p.unique_count / len(non_null) * 100, 2) if len(non_null) else 0.0
    p.top_values = _top_values(non_null)

    if inferred in ("integer", "float"):
        numeric = pd.to_numeric(non_null, errors="coerce")
        p.min, p.max = _finite(numeric.min()), _finite(numeric.max())
        p.mean, p.median = _finite(numeric.mean()), _finite(numeric.median())
        p.std = _finite(numeric.std()) if len(numeric) > 1 else None
        p.histogram = _histogram(numeric)
    elif inferred == "datetime":
        p.sample_values = [str(v) for v in non_null.head(3)]
    elif inferred == "string":
        texts = non_null.astype(str)
        lengths = texts.str.len()
        p.min_length, p.max_length = int(lengths.min()), int(lengths.max())
        p.semantic_type = _semantic_type(texts)
    return p


def profile_dataframe(df: pd.DataFrame) -> DatasetProfile:
    n_rows = len(df)
    columns = {str(col): profile_column(df[col], n_rows) for col in df.columns}
    missing_cells = sum(c.null_count for c in columns.values())
    total_cells = n_rows * len(df.columns)
    return DatasetProfile(
        row_count=n_rows,
        column_count=len(df.columns),
        duplicate_rows=_duplicate_rows(df),
        missing_cells=missing_cells,
        missing_cells_pct=round(missing_cells / total_cells * 100, 2) if total_cells else 0.0,
        memory_bytes=int(df.memory_usage(deep=True).sum()),
        columns=columns,
    )


def _duplicate_rows(df: pd.DataFrame) -> int:
    """df.duplicated() fails on unhashable cells, so compare a text form instead."""
    if df.empty:
        return 0
    try:
        return int(df.duplicated().sum())
    except TypeError:
        return int(df.map(repr).duplicated().sum())
