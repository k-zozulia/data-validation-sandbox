import io

from fastapi.testclient import TestClient

from app.main import app

CSV = b"name,age,email\nAnna,30,a@x.com\nBohdan,200,a@x.com\nOlha,40,c@x.com\n"


def _file(content=CSV, name="data.csv"):
    return {"file": (name, io.BytesIO(content), "text/csv")}


def test_health_ok_or_degraded():
    # Works with or without Redis: 200 if up, 503 if down — never crashes.
    with TestClient(app) as c:
        assert c.get("/health").status_code in (200, 503)


def test_profile_endpoint():
    with TestClient(app) as c:
        r = c.post("/datasets/profile", files=_file())
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["row_count"] == 3
    assert "age" in body["profile"]["columns"]
    assert "columns:" in body["starter_rules_yaml"]


def test_validate_sample_flags_violations():
    rules_yaml = "columns:\n  age:\n    range:\n      min: 0\n      max: 120\n"
    with TestClient(app) as c:
        r = c.post("/datasets/validate-sample",
                   files=_file(), data={"rules_yaml": rules_yaml})
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["total_violations"] == 1     # age=200 out of range
    assert body["summary"]["rules_failed"] == ["range"]


def test_unsupported_format_returns_clean_4xx():
    with TestClient(app) as c:
        r = c.post("/datasets/profile", files=_file(name="data.txt"))
    assert r.status_code == 415
    assert r.json()["error"] == "unsupported_format"


def test_invalid_yaml_returns_clean_4xx():
    with TestClient(app) as c:
        r = c.post("/datasets/validate-sample",
                   files=_file(), data={"rules_yaml": "columns: [broken"})
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_yaml"