"""Compute per-column statistics for a DataFrame.

Numeric min/max are guarded so a NaN never leaks into the JSON response
(NaN is not valid JSON).
"""
from __future__ import annotations

import pandas as pd
from pandas.api import types as pdt

from app.models.schemas import ColumnProfile, DatasetProfile


def profile_dataframe(df: pd.DataFrame) -> DatasetProfile:
    n_rows = len(df)
    columns: dict[str, ColumnProfile] = {}

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())

        min_val = max_val = None
        if pdt.is_numeric_dtype(series):
            lo, hi = series.min(), series.max()
            if pd.notna(lo):
                min_val = float(lo)
            if pd.notna(hi):
                max_val = float(hi)

        columns[str(col)] = ColumnProfile(
            dtype=str(series.dtype),
            null_count=null_count,
            null_pct=round(null_count / n_rows * 100, 2) if n_rows else 0.0,
            unique_count=int(series.nunique(dropna=True)),
            min=min_val,
            max=max_val,
        )

    return DatasetProfile(
        row_count=n_rows,
        column_count=len(df.columns),
        duplicate_rows=int(df.duplicated().sum()),
        columns=columns,
    )