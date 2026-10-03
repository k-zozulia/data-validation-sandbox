import io
import json

import pandas as pd
import pytest

from app.errors import AppException
from app.parsers import load_dataframe
from app.parsers.json_parser import parse_json, parse_jsonl
from app.parsers.parquet_parser import parse_parquet


def _parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


def _xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


# --- JSON ---
def test_json_array_of_records():
    df = parse_json(json.dumps([{"name": "Anna", "age": 30}, {"name": "Ivan"}]).encode())
    assert list(df.columns) == ["name", "age"] and len(df) == 2


def test_json_flattens_nested_objects():
    df = parse_json(json.dumps([{"name": "Anna", "addr": {"city": "Kyiv"}}]).encode())
    assert df["addr.city"][0] == "Kyiv"


def test_json_wrapper_object():
    df = parse_json(json.dumps({"data": [{"a": 1}, {"a": 2}]}).encode())
    assert len(df) == 2


def test_json_too_deep_raises():
    deep = {"a": {"b": {"c": {"d": {"e": {"f": 1}}}}}}
    with pytest.raises(AppException) as exc:
        parse_json(json.dumps([deep]).encode())
    assert exc.value.error == "json_too_deep"


def test_json_invalid_raises():
    with pytest.raises(AppException) as exc:
        parse_json(b"{not valid json")
    assert exc.value.status_code == 400


def test_jsonl():
    df = parse_jsonl(b'{"a": 1}\n\n{"a": 2, "b": [1, 2]}\n')
    assert len(df) == 2 and df["b"][1] == [1, 2]


def test_jsonl_bad_line():
    with pytest.raises(AppException) as exc:
        parse_jsonl(b'{"a": 1}\n{oops\n')
    assert "Line 2" in exc.value.detail


# --- Parquet / XLSX ---
def test_parquet_roundtrip():
    df = parse_parquet(_parquet_bytes(pd.DataFrame({"id": [1, 2, 3], "name": list("abc")})))
    assert list(df.columns) == ["id", "name"] and len(df) == 3


def test_parquet_invalid_raises():
    with pytest.raises(AppException) as exc:
        parse_parquet(b"not a parquet file")
    assert exc.value.status_code == 400


def test_xlsx_roundtrip():
    df, fmt = load_dataframe("book.xlsx", _xlsx_bytes(pd.DataFrame({"a": [1, 2]})))
    assert fmt == "xlsx" and list(df["a"]) == [1, 2]


# --- dispatcher ---
def test_dispatch_by_extension_and_clean_index():
    df, fmt = load_dataframe("x.json", json.dumps([{"a": 1}, {"a": 2}]).encode())
    assert fmt == "json" and list(df.index) == [0, 1]
    df, fmt = load_dataframe("x.ndjson", b'{"a": 1}\n')
    assert fmt == "jsonl"
    df, fmt = load_dataframe("x.tsv", b"a\tb\n1\t2\n")
    assert fmt == "csv" and list(df.columns) == ["a", "b"]


def test_dispatch_unknown_format():
    with pytest.raises(AppException) as exc:
        load_dataframe("x.docx", b"whatever")
    assert exc.value.error == "unsupported_format"
