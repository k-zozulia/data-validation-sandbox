import io

import pandas as pd

CSV = (b"id,age,email,country\n"
       b"1,30,a@x.com,UA\n"
       b"2,200,b@x.com,UA\n"
       b"3,40,,PL\n"
       b"4,25,d@x.com,XX\n")
RULES = """
columns:
  age:
    range: {min: 0, max: 120}
  email:
    not_null: {}
  country:
    allowed_values: {values: [UA, PL], severity: warning}
"""


def _full_job(client):
    ds = client.post("/api/datasets", files={"file": ("p.csv", io.BytesIO(CSV), "text/csv")})
    job = client.post("/api/jobs", json={"dataset_id": ds.json()["id"], "rules_yaml": RULES,
                                         "mode": "full"})
    assert job.status_code == 201
    return client.get(f"/api/jobs/{job.json()['id']}").json()


def test_clean_and_quarantine_split(client):
    job = _full_job(client)
    assert job["status"] == "succeeded"
    s = job["summary"]
    assert (s["clean_rows"], s["quarantine_rows"], s["warning_rows"]) == (2, 2, 1)

    clean = pd.read_csv(io.BytesIO(client.get(f"/api/jobs/{job['id']}/export/clean").content))
    assert list(clean["id"]) == [1, 4]                     # warning row 4 stays clean

    r = client.get(f"/api/jobs/{job['id']}/export/quarantine")
    q = pd.read_csv(io.BytesIO(r.content))
    assert list(q["id"]) == [2, 3] and list(q["_row"]) == [1, 2]
    assert q["_issues"].tolist() == ["age: range", "email: not_null"]


def test_annotated_export_formats(client):
    job = _full_job(client)
    r = client.get(f"/api/jobs/{job['id']}/export/annotated?format=json")
    rows = r.json()
    assert [x["_status"] for x in rows] == ["valid", "invalid", "invalid", "warning"]
    for fmt in ("parquet", "xlsx"):
        r = client.get(f"/api/jobs/{job['id']}/export/annotated?format={fmt}")
        assert r.status_code == 200 and len(r.content) > 100


def test_rows_filters(client):
    job = _full_job(client)
    base = f"/api/jobs/{job['id']}/rows"
    assert client.get(base, params={"filter": "issues"}).json()["total"] == 3
    assert client.get(base, params={"filter": "errors"}).json()["total"] == 2
    assert client.get(base, params={"filter": "warnings"}).json()["total"] == 1
    assert client.get(base, params={"filter": "clean"}).json()["total"] == 2
    assert client.get(base, params={"filter": "all"}).json()["total"] == 4
    page = client.get(base, params={"filter": "issues", "column": "age"}).json()
    assert page["total"] == 1
    row = page["rows"][0]
    assert row["_row"] == 1 and row["values"]["age"] == 200
    assert row["issues"] == [{"column": "age", "rule": "range", "severity": "error"}]


def test_bad_export_kind(client):
    job = _full_job(client)
    assert client.get(f"/api/jobs/{job['id']}/export/everything").status_code == 400
