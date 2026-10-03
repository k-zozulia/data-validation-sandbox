"""Test setup: an isolated SQLite DB + storage dir, and jobs run inline (no Redis)."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="dvs-tests-")
# Never the dev database: tests drop and recreate all tables. CI can point
# TEST_DATABASE_URL at a throwaway Postgres to run the suite there too.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_tmp}/test.db"
os.environ["STORAGE_DIR"] = f"{_tmp}/storage"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["INLINE_JOBS"] = "true"

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import orm  # noqa: E402,F401
from app.validators.types import RULES, CheckContext  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def run_check(rule: str, data, column: str = "c", df: pd.DataFrame | None = None, **params):
    """Run a single registered check on a series (or a full frame)."""
    if df is None:
        df = pd.DataFrame({column: data})
    spec = RULES[rule]
    return spec.check(CheckContext(df=df, column=column if spec.scope == "column" else None),
                      spec.params.model_validate(params))
