import pytest

from app.errors import AppException
from app.parsers.csv_parser import parse_csv, sniff_delimiter


def test_parse_simple_csv():
    df = parse_csv(b"name,age\nAnna,30\nBohdan,25\n")
    assert list(df.columns) == ["name", "age"] and len(df) == 2


def test_parse_semicolon_csv():
    df = parse_csv(b"name;city\nAnna;Kyiv\nOlha;Lviv\n")
    assert list(df.columns) == ["name", "city"]


def test_sniff_tab():
    assert sniff_delimiter("a\tb\n1\t2\n") == "\t"


def test_parse_empty_raises():
    with pytest.raises(AppException) as exc:
        parse_csv(b"")
    assert exc.value.status_code == 400


def test_parse_cp1251_fallback():
    text = "місто,значення\nКиїв,1\n".encode("cp1251")
    df = parse_csv(text)
    assert len(df) == 1 and "місто" in df.columns


def test_csv_bom_and_utf8():
    df = parse_csv("﻿name,age\nОля,30\n".encode())
    assert list(df.columns) == ["name", "age"]
