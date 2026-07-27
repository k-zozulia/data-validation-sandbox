import pytest

from app.parsers.csv_parser import parse_csv
from app.models.schemas import AppException


def test_parse_simple_csv():
    df = parse_csv(b"name,age\nAnna,30\nBohdan,25\n")
    assert list(df.columns) == ["name", "age"] and len(df) == 2


def test_parse_empty_raises():
    with pytest.raises(AppException) as exc:
        parse_csv(b"")
    assert exc.value.status_code == 400


def test_parse_nrows_limits_sample():
    df = parse_csv(b"n\n1\n2\n3\n4\n5\n", nrows=2)
    assert len(df) == 2


def test_parse_cp1251_fallback():
    # Cyrillic encoded as CP1251 is invalid UTF-8 -> must parse via fallback
    text = "місто,значення\nКиїв,1\n".encode("cp1251")
    df = parse_csv(text)
    assert len(df) == 1 and "місто" in df.columns