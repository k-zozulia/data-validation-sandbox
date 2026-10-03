import io

CSV = b"name,age,email\nAnna,30,a@x.com\nBohdan,200,a@x.com\nOlha,40,c@x.com\n"


def _upload(client, content=CSV, name="data.csv"):
    return client.post("/api/datasets", files={"file": (name, io.BytesIO(content), "text/csv")})


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["database"] == "up" and r.json()["inline_jobs"] is True


def test_upload_profiles_and_drafts_rules(client):
    r = _upload(client)
    assert r.status_code == 201
    body = r.json()
    assert body["row_count"] == 3 and body["format"] == "csv"
    assert "age" in body["profile"]["columns"]
    assert "columns:" in body["rules_yaml"]

    listed = client.get("/api/datasets").json()
    assert [d["id"] for d in listed] == [body["id"]]


def test_dataset_rows_and_update(client):
    ds = _upload(client).json()
    page = client.get(f"/api/datasets/{ds['id']}/rows", params={"limit": 2}).json()
    assert page["total"] == 3 and len(page["rows"]) == 2
    assert page["rows"][1]["values"]["name"] == "Bohdan"

    r = client.patch(f"/api/datasets/{ds['id']}", json={"name": "people", "rules_yaml": "x: 1"})
    assert r.json()["name"] == "people" and r.json()["rules_yaml"] == "x: 1"


def test_sample_job_runs_immediately(client):
    ds = _upload(client).json()
    rules = "columns:\n  age:\n    range: {min: 0, max: 120}\n"
    r = client.post("/api/jobs", json={"dataset_id": ds["id"], "rules_yaml": rules,
                                       "mode": "sample"})
    job = r.json()
    assert job["status"] == "succeeded"
    assert job["summary"]["quarantine_rows"] == 1
    assert job["violations"][0]["rule"] == "range"
    assert job["violations"][0]["sample_values"] == [200]

    last = client.get(f"/api/datasets/{ds['id']}").json()["last_job"]
    assert last["id"] == job["id"] and last["score"] == job["summary"]["score"]


def test_job_uses_dataset_draft_by_default(client):
    ds = _upload(client).json()
    job = client.post("/api/jobs", json={"dataset_id": ds["id"], "mode": "full"}).json()
    assert job["rules_yaml"] == ds["rules_yaml"]
    assert client.get(f"/api/jobs/{job['id']}").json()["status"] == "succeeded"


def test_invalid_rules_rejected_with_issues(client):
    ds = _upload(client).json()
    r = client.post("/api/jobs", json={"dataset_id": ds["id"], "mode": "full",
                                       "rules_yaml": "columns:\n  age:\n    nonsense: {}\n"})
    assert r.status_code == 422
    assert r.json()["error"] == "invalid_rules" and r.json()["issues"]


def test_invalid_yaml_returns_clean_4xx(client):
    ds = _upload(client).json()
    r = client.post("/api/jobs", json={"dataset_id": ds["id"], "rules_yaml": "columns: [broken"})
    assert r.status_code == 400 and r.json()["error"] == "invalid_yaml"


def test_unsupported_format_returns_clean_4xx(client):
    r = _upload(client, name="data.docx")
    assert r.status_code == 415 and r.json()["error"] == "unsupported_format"


def test_lint_endpoint(client):
    ds = _upload(client).json()
    r = client.post("/api/rules/lint", json={"dataset_id": ds["id"],
                                             "rules_yaml": "columns:\n  ghost:\n    unique: {}\n"})
    body = r.json()
    assert body["valid"] is True and body["checks"] == 1
    assert body["issues"][0]["severity"] == "warning" and body["issues"][0]["line"] == 2

    r = client.post("/api/rules/lint", json={"rules_yaml": "columns: [broken"})
    assert r.json()["valid"] is False


def test_catalog(client):
    names = [r["name"] for r in client.get("/api/rules/catalog").json()]
    assert "compare" in names


def test_rule_sets_crud_and_run(client):
    ds = _upload(client).json()
    rs = client.post("/api/rule-sets", json={"name": "people", "rules_yaml":
                                             "columns:\n  email:\n    unique: {}\n"})
    assert rs.status_code == 201
    assert client.post("/api/rule-sets", json={"name": "people",
                                               "rules_yaml": ""}).status_code == 409

    job = client.post("/api/jobs", json={"dataset_id": ds["id"], "mode": "full",
                                         "rule_set_id": rs.json()["id"]}).json()
    job = client.get(f"/api/jobs/{job['id']}").json()
    assert job["violations"][0]["rule"] == "unique"

    r = client.patch(f"/api/rule-sets/{rs.json()['id']}", json={"description": "d"})
    assert r.json()["description"] == "d"
    assert client.delete(f"/api/rule-sets/{rs.json()['id']}").status_code == 204
    assert client.get("/api/rule-sets").json() == []


def test_delete_dataset_cascades(client):
    ds = _upload(client).json()
    job = client.post("/api/jobs", json={"dataset_id": ds["id"], "mode": "sample"}).json()
    assert client.delete(f"/api/datasets/{ds['id']}").status_code == 204
    assert client.get(f"/api/jobs/{job['id']}").status_code == 404
    assert client.get(f"/api/datasets/{ds['id']}").status_code == 404


def test_sample_jobs_are_pruned(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "keep_sample_jobs", 2)
    ds = _upload(client).json()
    for _ in range(4):
        client.post("/api/jobs", json={"dataset_id": ds["id"], "mode": "sample"})
    jobs = client.get(f"/api/datasets/{ds['id']}/jobs").json()
    assert len(jobs) == 2
