"""Engine-level behaviour: severities, row issues, summary, missing columns."""
import pandas as pd
import pytest

from app.errors import AppException
from app.validators.rule_engine import run_rules


def test_engine_multiple_violations():
    df = pd.DataFrame({"age": [-1, 200, 30], "id": [1, 1, 2]})
    rules = {"columns": {"age": {"range": {"min": 0, "max": 120}}, "id": {"unique": {}}}}
    result = run_rules(df, rules)
    assert {v.rule for v in result.violations} == {"range", "unique"}
    assert result.row_issues[0] == [("age", "range", "error"), ("id", "unique", "error")]


def test_engine_all_pass():
    df = pd.DataFrame({"age": [10, 20], "id": [1, 2]})
    rules = {"columns": {"age": {"not_null": {}, "range": {"min": 0, "max": 120}},
                         "id": {"unique": None}}}
    result = run_rules(df, rules)
    assert result.violations == []
    assert result.summary(2)["score"] == 100.0


def test_missing_column_is_a_violation_once():
    result = run_rules(pd.DataFrame({"a": [1]}),
                       {"columns": {"ghost": {"not_null": {}, "unique": {}}}})
    assert [v.rule for v in result.violations] == ["column_exists"]


def test_unknown_rule_rejected_before_running():
    with pytest.raises(AppException) as exc:
        run_rules(pd.DataFrame({"a": [1]}), {"columns": {"a": {"nonsense": {}}}})
    assert exc.value.status_code == 422
    assert "Unknown rule" in exc.value.extra["issues"][0]["message"]


def test_warnings_do_not_quarantine():
    df = pd.DataFrame({"age": [10, 130, None]})
    rules = {"columns": {"age": {"not_null": {},
                                 "range": {"max": 120, "severity": "warning",
                                           "message": "suspiciously old"}}}}
    result = run_rules(df, rules)
    s = result.summary(3)
    assert s["quarantine_rows"] == 1 and s["warning_rows"] == 1 and s["clean_rows"] == 2
    assert s["warning_only_rows"] == 1
    warn = next(v for v in result.violations if v.rule == "range")
    assert warn.severity == "warning" and warn.message == "suspiciously old"


def test_disabled_check_is_skipped():
    result = run_rules(pd.DataFrame({"a": [None]}), {"columns": {"a": {"not_null": False}}})
    assert result.checks == [] and result.violations == []


def test_dataset_rules_and_progress():
    df = pd.DataFrame({"a": [1, 1], "b": [2, 2]})
    seen = []
    result = run_rules(df, {"dataset": {"row_count": {"min": 5},
                                        "unique_together": {"columns": ["a", "b"]}}},
                       on_progress=seen.append)
    assert {v.rule for v in result.violations} == {"row_count", "unique_together"}
    assert seen[-1] == 1.0
    assert result.summary(2)["quarantine_rows"] == 2


def test_failed_rows_are_capped_but_counted(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "max_failed_rows_per_violation", 3)
    result = run_rules(pd.DataFrame({"a": [None] * 10}), {"columns": {"a": {"not_null": {}}}})
    v = result.violations[0]
    assert v.failed_count == 10 and len(v.failed_rows) == 3
    assert len(result.row_issues) == 10
