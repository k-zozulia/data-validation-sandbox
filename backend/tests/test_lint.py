from app.services.yaml_generator import attach_lines, parse_rules_yaml, yaml_line
from app.validators.lint import compile_rules
from app.validators.types import catalog


def _issues(yaml_text, columns=None):
    checks, issues = compile_rules(parse_rules_yaml(yaml_text), columns)
    return checks, attach_lines(yaml_text, issues)


def test_valid_rules_compile():
    checks, issues = _issues("columns:\n  age:\n    not_null: {}\n    range: {min: 0}\n")
    assert len(checks) == 2 and issues == []


def test_unknown_param_and_bad_type():
    _, issues = _issues("columns:\n  age:\n    range: {min: zero, step: 1}\n")
    messages = " ".join(i.message for i in issues)
    assert "Unknown parameter" in messages and "min" in messages
    assert all(i.line == 3 for i in issues)


def test_min_greater_than_max():
    _, issues = _issues("columns:\n  a:\n    length: {min: 5, max: 2}\n")
    assert "greater than max" in issues[0].message


def test_invalid_regex_reported():
    _, issues = _issues("columns:\n  a:\n    regex: {pattern: '(unclosed'}\n")
    assert issues[0].path == ["columns", "a", "regex", "pattern"]


def test_unknown_column_is_a_warning():
    checks, issues = _issues("columns:\n  ghost:\n    not_null: {}\n", columns=["a"])
    assert len(checks) == 1
    assert issues[0].severity == "warning" and issues[0].line == 2


def test_dataset_rule_in_wrong_place():
    _, issues = _issues("columns:\n  a:\n    row_count: {min: 1}\n")
    assert "dataset-level" in issues[0].message


def test_yaml_line_lookup():
    text = "columns:\n  a:\n    not_null: {}\n  b:\n    unique: {}\n"
    assert yaml_line(text, ["columns", "b", "unique"]) == 5


def test_catalog_describes_params():
    by_name = {r["name"]: r for r in catalog()}
    assert {"not_null", "compare", "allowed_values", "unique_together"} <= set(by_name)
    compare = {p["name"]: p for p in by_name["compare"]["params"]}
    assert compare["column"]["kind"] == "column" and compare["op"]["required"]
    assert compare["severity"]["common"] is True
