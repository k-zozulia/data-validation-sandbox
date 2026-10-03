import pandas as pd

from app.services.profiler import profile_dataframe
from app.services.yaml_generator import generate_rules, parse_rules_yaml, rules_to_yaml
from app.validators.rule_engine import run_rules


def test_profile_basic_stats():
    df = pd.DataFrame({"age": [10, 20, None, 20], "id": [1, 2, 3, 4]})
    p = profile_dataframe(df)
    age = p.columns["age"]
    assert p.row_count == 4 and p.missing_cells == 1
    assert age.null_count == 1 and age.null_pct == 25.0
    assert age.min == 10.0 and age.max == 20.0 and age.inferred_type == "integer"
    assert age.top_values[0].value == "20.0" and age.top_values[0].count == 2
    assert sum(b.count for b in age.histogram) == 3
    assert p.columns["id"].unique_count == 4


def test_semantic_types():
    df = pd.DataFrame({"email": ["a@x.com", "b@y.org"], "d": ["2024-01-01", "2024-02-03"],
                       "name": ["Anna", "Olha"]})
    cols = profile_dataframe(df).columns
    assert cols["email"].semantic_type == "email"
    assert cols["d"].semantic_type == "date"
    assert cols["name"].semantic_type is None and cols["name"].max_length == 4


def test_profiler_handles_list_columns():
    df = pd.DataFrame({"id": [1, 2], "tags": [["a", "b"], ["c"]]})
    p = profile_dataframe(df)
    assert p.columns["tags"].is_array and p.columns["tags"].inferred_type == "array"
    assert p.columns["tags"].min_length == 1 and p.columns["tags"].max_length == 2
    assert p.duplicate_rows == 0


def test_generated_rules_pass_on_source_data():
    df = pd.DataFrame({
        "age": [10.5, 20, 30, None] * 10,
        "email": [f"u{i}@x.com" for i in range(40)],
        "country": ["UA", "PL", "DE", "UA"] * 10,
        "joined": ["2024-01-01", "2024-02-03", "2023-12-31", "2024-05-05"] * 10,
        "tags": [["a"], ["b", "c"], [], ["d"]] * 10,
    })
    rules = generate_rules(profile_dataframe(df))
    cols = rules["columns"]
    assert "allowed_values" in cols["country"]
    assert "regex" in cols["email"] and "unique" in cols["email"]
    assert "date" in cols["joined"]
    assert run_rules(df, rules).violations == []


def test_yaml_roundtrip():
    rules = {"columns": {"age": {"not_null": {}, "range": {"min": 0, "max": 120}}}}
    assert parse_rules_yaml(rules_to_yaml(rules)) == rules


def test_parse_invalid_yaml_raises_with_line():
    import pytest

    from app.errors import AppException
    with pytest.raises(AppException) as exc:
        parse_rules_yaml("columns:\n  a: [unclosed\n")
    assert exc.value.extra["issues"][0]["line"] is not None
