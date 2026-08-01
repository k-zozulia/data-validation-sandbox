import io
import json

import pandas as pd
import pytest

from app.parsers import load_dataframe
from app.parsers.json_parser import parse_json
from app.parsers.parquet_parser import parse_parquet
from app.models.schemas import AppException


# --- JSON ---
def test_json_array_of_records():
    data = json.dumps([{"name": "Anna", "age": 30}, {"name": "Ivan", "age": 25}]).encode()
    df = parse_json(data)
    assert list(df.columns) == ["name", "age"] and len(df) == 2


def test_json_flattens_nested_objects():
    data = json.dumps([{"name": "Anna", "addr": {"city": "Kyiv"}}]).encode()
    df = parse_json(data)
    assert "addr.city" in df.columns and df["addr.city"][0] == "Kyiv"


def test_json_single_object_ok():
    df = parse_json(json.dumps({"a": 1}).encode())
    assert len(df) == 1


def test_json_too_deep_raises():
    deep = {"a": {"b": {"c": {"d": {"e": {"f": 1}}}}}}   # depth 6 > default 5
    with pytest.raises(AppException) as exc:
        parse_json(json.dumps([deep]).encode())
    assert exc.value.error == "json_too_deep"


def test_json_invalid_raises():
    with pytest.raises(AppException) as exc:
        parse_json(b"{not valid json")
    assert exc.value.status_code == 400


def test_json_nrows_samples():
    data = json.dumps([{"n": i} for i in range(10)]).encode()
    assert len(parse_json(data, nrows=3)) == 3


# --- Parquet ---
def _parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


def test_parquet_roundtrip():
    raw = _parquet_bytes(pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]}))
    df = parse_parquet(raw)
    assert list(df.columns) == ["id", "name"] and len(df) == 3


def test_parquet_nrows_samples():
    raw = _parquet_bytes(pd.DataFrame({"n": range(100)}))
    assert len(parse_parquet(raw, nrows=10)) == 10


def test_parquet_invalid_raises():
    with pytest.raises(AppException) as exc:
        parse_parquet(b"not a parquet file")
    assert exc.value.status_code == 400


# --- dispatcher ---
def test_dispatch_by_extension():
    jdata = json.dumps([{"a": 1}]).encode()
    assert len(load_dataframe("x.json", jdata)) == 1
    pdata = _parquet_bytes(pd.DataFrame({"a": [1, 2]}))
    assert len(load_dataframe("x.parquet", pdata)) == 2


def test_dispatch_unknown_format():
    with pytest.raises(AppException) as exc:
        load_dataframe("x.txt", b"whatever")
    assert exc.value.error == "unsupported_format"