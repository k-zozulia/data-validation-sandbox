import io
import json

import pandas as pd
import pytest

from app.parsers import load_dataframe
from app.services.profiler import profile_dataframe
from app.models.schemas import AppException


def _parquet_bytes(df):
    buf = io.BytesIO(); df.to_parquet(buf, index=False); return buf.getvalue()


# --- magic bytes ---
def test_parquet_content_wrong_extension_rejected():
    raw = _parquet_bytes(pd.DataFrame({"a": [1, 2]}))
    with pytest.raises(AppException) as exc:
        load_dataframe("data.csv", raw)          # parquet bytes, .csv name
    assert exc.value.status_code == 415 and exc.value.error == "format_mismatch"


def test_parquet_extension_non_parquet_content_rejected():
    with pytest.raises(AppException) as exc:
        load_dataframe("data.parquet", b"name,age\nAnna,30\n")  # csv text, .parquet name
    assert exc.value.error == "format_mismatch"


def test_json_extension_non_json_content_rejected():
    with pytest.raises(AppException) as exc:
        load_dataframe("data.json", b"name,age\nAnna,30\n")     # csv text, .json name
    assert exc.value.error == "format_mismatch"


def test_valid_formats_pass_magic_check():
    assert len(load_dataframe("d.csv", b"a,b\n1,2\n")) == 1
    assert len(load_dataframe("d.json", json.dumps([{"a": 1}]).encode())) == 1
    assert len(load_dataframe("d.parquet", _parquet_bytes(pd.DataFrame({"a": [1]})))) == 1


# --- other guardrails / edge cases ---
def test_unsupported_extension():
    with pytest.raises(AppException) as exc:
        load_dataframe("data.txt", b"whatever")
    assert exc.value.error == "unsupported_format"


def test_oversize_file_rejected(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "max_file_size_mb", 0)   # everything is "too big"
    with pytest.raises(AppException) as exc:
        load_dataframe("d.csv", b"a,b\n1,2\n")
    assert exc.value.status_code == 413


def test_empty_csv_clean_error():
    with pytest.raises(AppException) as exc:
        load_dataframe("d.csv", b"")
    assert exc.value.status_code == 400 and exc.value.error == "empty_file"


def test_csv_bom_and_utf8():
    raw = "\ufeffname,age\nОля,30\n".encode("utf-8")   # UTF-8 BOM + Cyrillic
    df = load_dataframe("d.csv", raw)
    assert len(df) == 1


# --- profiler robustness on list-valued columns ---
def test_profiler_handles_list_columns():
    df = pd.DataFrame({"id": [1, 2], "tags": [["a", "b"], ["c"]]})
    p = profile_dataframe(df)                # must not raise unhashable type: 'list'
    assert p.columns["tags"].is_array is True
    assert p.columns["tags"].unique_count == 0
    assert p.columns["id"].is_array is False