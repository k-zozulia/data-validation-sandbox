import time

import pandas as pd

from app.validators.types import (
    check_regex, check_array_length, check_array_items,
)


# --- regex ---
def test_regex_passes():
    s = pd.Series(["a@x.com", "b@y.com"])
    assert check_regex(s, "email", pattern=r".+@.+\..+") is None


def test_regex_flags_nonmatching():
    s = pd.Series(["a@x.com", "not-an-email", "c@y.com"])
    v = check_regex(s, "email", pattern=r".+@.+\..+")
    assert v.failed_count == 1 and v.failed_rows == [1]


def test_regex_invalid_pattern():
    v = check_regex(pd.Series(["x"]), "c", pattern=r"(unclosed")
    assert v is not None and "Invalid regex" in v.message


def test_regex_redos_times_out():
    # Catastrophic backtracking must be caught by the timeout, not hang.
    s = pd.Series(["a" * 45 + "b"])
    start = time.time()
    v = check_regex(s, "c", pattern=r"(a|a)*$")
    assert v is not None and "timed out" in v.message
    assert time.time() - start < 3    # guarded, did not hang


# --- array_length ---
def test_array_length_passes():
    s = pd.Series([["a", "b"], ["c"]])
    assert check_array_length(s, "tags", min=1, max=3) is None


def test_array_length_flags_too_long():
    s = pd.Series([["a", "b", "c", "d"], ["e"]])
    v = check_array_length(s, "tags", max=2)
    assert v.failed_count == 1 and v.failed_rows == [0]


def test_array_length_flags_non_array():
    s = pd.Series([["a"], "not-a-list"])
    v = check_array_length(s, "tags", min=1)
    assert v.failed_rows == [1]


# --- array_items ---
def test_array_items_type_passes():
    s = pd.Series([[1, 2, 3], [4, 5]])
    assert check_array_items(s, "scores", type="int") is None


def test_array_items_type_flags():
    s = pd.Series([[1, 2], [3, "x"]])
    v = check_array_items(s, "scores", type="int")
    assert v.failed_rows == [1]


def test_array_items_range_flags():
    s = pd.Series([[10, 20], [10, 200]])
    v = check_array_items(s, "scores", min=0, max=100)
    assert v.failed_rows == [1]