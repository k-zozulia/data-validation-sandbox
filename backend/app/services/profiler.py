"""Compute per-column statistics for a DataFrame."""
from __future__ import annotations

import pandas as pd
from pandas.api import types as pdt

from app.models.schemas import ColumnProfile, DatasetProfile


def _has_list_values(series: pd.Series) -> bool:
    """True if any non-null value is a list/tuple (unhashable, no nunique/min/max)."""
    for value in series:
        if isinstance(value, (list, tuple)):
            return True
    return False


def profile_dataframe(df: pd.DataFrame) -> DatasetProfile:
    n_rows = len(df)
    columns: dict[str, ColumnProfile] = {}

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())

        is_listy = _has_list_values(series)

        unique_count = 0 if is_listy else int(series.nunique(dropna=True))

        min_val = max_val = None
        if not is_listy and pdt.is_numeric_dtype(series):
            lo, hi = series.min(), series.max()
            if pd.notna(lo):
                min_val = float(lo)
            if pd.notna(hi):
                max_val = float(hi)

        columns[str(col)] = ColumnProfile(
            dtype=str(series.dtype),
            null_count=null_count,
            null_pct=round(null_count / n_rows * 100, 2) if n_rows else 0.0,
            unique_count=unique_count,
            min=min_val,
            max=max_val,
            is_array=is_listy,
        )

    return DatasetProfile(
        row_count=n_rows,
        column_count=len(df.columns),
        duplicate_rows=_duplicate_rows(df),
        columns=columns,
    )


def _duplicate_rows(df: pd.DataFrame) -> int:
    """df.duplicated() also fails on unhashable cells, so guard it too."""
    try:
        return int(df.duplicated().sum())
    except TypeError:
        hashable = [c for c in df.columns if not _has_list_values(df[c])]
        return int(df[hashable].duplicated().sum()) if hashable else 0