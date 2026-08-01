import pandas as pd

from app.models.schemas import Violation
from app.workers.celery_app import dirty_indices, split_dataframe


def test_dirty_indices_union():
    vs = [
        Violation(column="age", rule="range", message="", failed_rows=[1, 3]),
        Violation(column="id", rule="unique", message="", failed_rows=[3, 5]),
        Violation(column="t", rule="dtype", message=""),   # column-level: no rows
    ]
    assert dirty_indices(vs) == [1, 3, 5]


def test_split_clean_quarantine():
    df = pd.DataFrame({"x": [10, 20, 30, 40]})
    clean, quarantine = split_dataframe(df, [1, 3])
    assert list(clean["x"]) == [10, 30]
    assert list(quarantine["x"]) == [20, 40]


def test_split_no_dirty_all_clean():
    df = pd.DataFrame({"x": [1, 2, 3]})
    clean, quarantine = split_dataframe(df, [])
    assert len(clean) == 3 and len(quarantine) == 0


def test_clean_plus_quarantine_equals_original():
    df = pd.DataFrame({"x": list(range(10))})
    clean, quarantine = split_dataframe(df, [2, 4, 6])
    assert len(clean) + len(quarantine) == len(df)