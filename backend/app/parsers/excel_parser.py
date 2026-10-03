"""XLSX parsing (first sheet) via openpyxl."""
from __future__ import annotations

from io import BytesIO

import pandas as pd

from app.errors import AppException


def parse_excel(raw: bytes) -> pd.DataFrame:
    try:
        df = pd.read_excel(BytesIO(raw), sheet_name=0, engine="openpyxl")
    except Exception as exc:  # openpyxl raises a zoo of exception types
        raise AppException(400, "invalid_xlsx", f"Could not read the workbook: {exc}")
    if df.empty and len(df.columns) == 0:
        raise AppException(400, "empty_file", "The first sheet of the workbook is empty")
    return df
