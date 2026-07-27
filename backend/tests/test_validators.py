import pandas as pd
import pytest

from app.validators.types import (
    check_not_null, check_dtype, check_range, check_unique,
)
from app.validators.rule_engine import run_rules


# --- not_null ---
def test_not_null_passes():
    assert check_not_null(pd.Series([1, 2, 3]), "a") is None


def test_not_null_flags_missing():
    v = check_not_null(pd.Series([1, None, 3]), "a")
    assert v is not None and v.failed_count == 1 and v.failed_rows == [1]


# --- dtype ---
@pytest.mark.parametrize("data,expected,ok", [
    ([1, 2, 3], "int", True),
    ([1.0, 2.5], "float", True),
    (["a", "b"], "str", True),
    ([1, 2, 3], "str", False),
    (["a", "b"], "int", False),
])
def test_dtype(data, expected, ok):
    result = check_dtype(pd.Series(data), "c", expected=expected)
    assert (result is None) == ok


# --- range ---
def test_range_within_bounds():
    assert check_range(pd.Series([0, 50, 120]), "age", min=0, max=120) is None


def test_range_flags_outliers():
    v = check_range(pd.Series([-5, 50, 200]), "age", min=0, max=120)
    assert v.failed_count == 2 and v.failed_rows == [0, 2]


def test_range_ignores_nulls():
    assert check_range(pd.Series([10, None, 20]), "age", min=0, max=100) is None


# --- unique ---
def test_unique_passes():
    assert check_unique(pd.Series([1, 2, 3]), "id") is None


def test_unique_flags_duplicates():
    v = check_unique(pd.Series([1, 2, 2, 3, 3]), "id")
    assert v.failed_count == 4 and set(v.failed_rows) == {1, 2, 3, 4}


# --- engine ---
def test_engine_multiple_violations():
    df = pd.DataFrame({"age": [-1, 200, 30], "id": [1, 1, 2]})
    rules = {"columns": {
        "age": {"range": {"min": 0, "max": 120}},
        "id": {"unique": {}},
    }}
    assert {v.rule for v in run_rules(df, rules)} == {"range", "unique"}


def test_engine_missing_column():
    v = run_rules(pd.DataFrame({"a": [1]}), {"columns": {"ghost": {"not_null": {}}}})
    assert len(v) == 1 and v[0].rule == "column_exists"


def test_engine_unknown_rule():
    v = run_rules(pd.DataFrame({"a": [1]}), {"columns": {"a": {"nonsense": {}}}})
    assert v[0].rule == "nonsense" and "Unknown rule" in v[0].message


def test_engine_all_pass():
    df = pd.DataFrame({"age": [10, 20], "id": [1, 2]})
    rules = {"columns": {
        "age": {"not_null": {}, "range": {"min": 0, "max": 120}},
        "id": {"unique": {}},
    }}
    assert run_rules(df, rules) == []