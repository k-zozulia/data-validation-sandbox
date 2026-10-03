import time

import pandas as pd

from tests.conftest import run_check


# --- not_null / not_blank ---
def test_not_null_passes():
    assert run_check("not_null", [1, 2, 3]) is None


def test_not_null_flags_missing():
    f = run_check("not_null", [1, None, 3])
    assert f is not None and f.rows == [1]


def test_not_blank_flags_whitespace_only():
    f = run_check("not_blank", ["a", "  ", "", None])
    assert f.rows == [1, 2]


# --- dtype ---
def test_dtype_flags_only_the_offending_rows():
    assert run_check("dtype", [1, 2, 3, "abc", 5], expected="int").rows == [3]


def test_dtype_allows_coercible_values():
    assert run_check("dtype", [1, "5", 5.0, 3], expected="int") is None


def test_dtype_rejects_non_whole_for_int():
    assert run_check("dtype", [1, 5.3, 3], expected="int").rows == [1]


def test_dtype_ignores_nulls():
    assert run_check("dtype", [1, None, 3], expected="int") is None


def test_dtype_datetime_strings():
    assert run_check("dtype", ["2024-01-02", "nope"], expected="datetime").rows == [1]


# --- range ---
def test_range_within_bounds():
    assert run_check("range", [0, 50, 120], min=0, max=120) is None


def test_range_flags_outliers_and_non_numbers():
    f = run_check("range", [-5, 50, 200, "abc"], min=0, max=120)
    assert f.rows == [0, 2, 3]
    assert f.values == [-5, 200, "abc"]


def test_range_ignores_nulls():
    assert run_check("range", [10, None, 20], min=0, max=100) is None


# --- unique ---
def test_unique_flags_duplicates():
    assert set(run_check("unique", [1, 2, 2, 3, 3]).rows) == {1, 2, 3, 4}


def test_unique_treats_1_and_1_0_as_equal():
    assert run_check("unique", [1, 1.0, 2]).rows == [0, 1]


# --- allowed_values ---
def test_allowed_values():
    f = run_check("allowed_values", ["UA", "PL", "XX", None], values=["UA", "PL"])
    assert f.rows == [2]


def test_allowed_values_case_insensitive_and_numbers():
    assert run_check("allowed_values", ["ua", "Pl"], values=["UA", "PL"],
                     case_sensitive=False) is None
    assert run_check("allowed_values", [1, 2.0, 3], values=[1, 2]).rows == [2]


# --- length ---
def test_length():
    assert run_check("length", ["ab", "abcdef", "abc"], min=2, max=4).rows == [1]


# --- regex ---
def test_regex_flags_nonmatching():
    f = run_check("regex", ["a@x.com", "not-an-email", "c@y.com"], pattern=r".+@.+\..+")
    assert f.rows == [1]


def test_regex_full_match():
    assert run_check("regex", ["abc", "abcd"], pattern="abc", full_match=True).rows == [1]


def test_regex_redos_times_out():
    start = time.time()
    f = run_check("regex", ["a" * 45 + "b"], pattern=r"(a|a)*$")
    assert f is not None and "timed out" in f.message
    assert time.time() - start < 5


# --- date ---
def test_date_format_and_bounds():
    f = run_check("date", ["2024-01-01", "01/02/2024", "1999-12-31", None],
                  format="%Y-%m-%d", min="2000-01-01")
    assert f.rows == [1, 2]


def test_date_mixed_formats_without_format():
    assert run_check("date", ["2024-01-01", "2024-02-03T10:00:00"]) is None


# --- compare ---
def test_compare_dates_and_numbers():
    df = pd.DataFrame({"start": ["2024-01-01", "2024-03-01", None],
                       "end": ["2024-02-01", "2024-01-01", "2024-01-01"]})
    from app.validators.types import RULES, CheckContext
    spec = RULES["compare"]
    f = spec.check(CheckContext(df=df, column="end"),
                   spec.params.model_validate({"op": ">=", "column": "start"}))
    assert f.rows == [1]

    df = pd.DataFrame({"a": [1, 5, 3], "b": [2, 4, 3]})
    f = spec.check(CheckContext(df=df, column="a"),
                   spec.params.model_validate({"op": "<", "column": "b"}))
    assert f.rows == [1, 2]


# --- arrays ---
def test_array_length():
    assert run_check("array_length", [["a", "b", "c", "d"], ["e"]], max=2).rows == [0]
    assert run_check("array_length", [["a"], "not-a-list"], min=1).rows == [1]


def test_array_items():
    assert run_check("array_items", [[1, 2], [3, "x"]], type="int").rows == [1]
    assert run_check("array_items", [[10, 20], [10, 200]], min=0, max=100).rows == [1]


# --- dataset-level ---
def test_row_count():
    df = pd.DataFrame({"a": [1, 2]})
    assert run_check("row_count", None, df=df, min=3) is not None
    assert run_check("row_count", None, df=df, min=1, max=2) is None


def test_unique_together():
    df = pd.DataFrame({"a": [1, 1, 1], "b": ["x", "x", "y"]})
    assert run_check("unique_together", None, df=df, columns=["a", "b"]).rows == [0, 1]
