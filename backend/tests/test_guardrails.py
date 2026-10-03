import io
import json

import pandas as pd
import pytest

from app.errors import AppException
from app.parsers import load_dataframe


def _parquet_bytes(df):
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


# --- magic bytes ---
def test_parquet_content_wrong_extension_rejected():
    with pytest.raises(AppException) as exc:
        load_dataframe("data.csv", _parquet_bytes(pd.DataFrame({"a": [1, 2]})))
    assert exc.value.status_code == 415 and exc.value.error == "format_mismatch"


def test_parquet_extension_non_parquet_content_rejected():
    with pytest.raises(AppException) as exc:
        load_dataframe("data.parquet", b"name,age\nAnna,30\n")
    assert exc.value.error == "format_mismatch"


def test_json_extension_non_json_content_rejected():
    with pytest.raises(AppException) as exc:
        load_dataframe("data.json", b"name,age\nAnna,30\n")
    assert exc.value.error == "format_mismatch"


def test_zip_disguised_as_csv_rejected():
    with pytest.raises(AppException) as exc:
        load_dataframe("data.csv", b"PK\x03\x04garbage")
    assert exc.value.error == "format_mismatch"


def test_valid_formats_pass_magic_check():
    assert len(load_dataframe("d.csv", b"a,b\n1,2\n")[0]) == 1
    assert len(load_dataframe("d.json", json.dumps([{"a": 1}]).encode())[0]) == 1
    assert len(load_dataframe("d.parquet", _parquet_bytes(pd.DataFrame({"a": [1]})))[0]) == 1


# --- limits ---
def test_oversize_file_rejected(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "max_file_size_mb", 0)
    with pytest.raises(AppException) as exc:
        load_dataframe("d.csv", b"a,b\n1,2\n")
    assert exc.value.status_code == 413


def test_too_many_rows_rejected(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "max_rows", 2)
    with pytest.raises(AppException) as exc:
        load_dataframe("d.csv", b"a\n1\n2\n3\n")
    assert exc.value.error == "too_many_rows"


def test_empty_csv_clean_error():
    with pytest.raises(AppException) as exc:
        load_dataframe("d.csv", b"")
    assert exc.value.status_code == 400 and exc.value.error == "empty_file"
