import pandas as pd

from app.services.profiler import profile_dataframe
from app.services.yaml_generator import generate_rules, rules_to_yaml, parse_rules_yaml
from app.validators.rule_engine import run_rules


def test_profile_basic_stats():
    df = pd.DataFrame({"age": [10, 20, None, 20], "id": [1, 2, 3, 4]})
    p = profile_dataframe(df)
    assert p.row_count == 4
    assert p.columns["age"].null_count == 1
    assert p.columns["age"].null_pct == 25.0
    assert p.columns["age"].min == 10.0 and p.columns["age"].max == 20.0
    assert p.columns["id"].unique_count == 4


def test_nullable_int_becomes_numeric_not_int():
    # age has a null -> pandas makes it float64 -> generator must emit 'numeric'
    df = pd.DataFrame({"age": [10, 20, None]})
    rules = generate_rules(profile_dataframe(df))
    assert rules["columns"]["age"]["dtype"]["expected"] == "numeric"


def test_generated_rules_pass_on_source_data():
    # Starter rules generated from a dataset should not flag that same dataset.
    df = pd.DataFrame({"age": [10, 20, 30], "email": ["a@x", "b@x", "c@x"]})
    rules = generate_rules(profile_dataframe(df))
    assert run_rules(df, rules) == []


def test_yaml_roundtrip():
    rules = {"columns": {"age": {"not_null": {}, "range": {"min": 0, "max": 120}}}}
    assert parse_rules_yaml(rules_to_yaml(rules)) == rules


def test_parse_invalid_yaml_raises():
    from app.models.schemas import AppException
    import pytest
    with pytest.raises(AppException):
        parse_rules_yaml("columns: [unclosed")