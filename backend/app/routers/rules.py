"""Rule tooling for the editor: catalog of rule types and live linting."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppException
from app.models.schemas import LintResponse, RulesText
from app.services import datasets as ds_service
from app.services.yaml_generator import attach_lines, parse_rules_yaml
from app.validators.lint import compile_rules
from app.validators.types import catalog

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/catalog")
def rule_catalog() -> list[dict]:
    return catalog()


@router.post("/lint", response_model=LintResponse)
def lint(body: RulesText, db: Session = Depends(get_db)):
    columns = None
    if body.dataset_id:
        ds = ds_service.get_dataset(db, body.dataset_id)
        columns = list(ds.profile.get("columns", {}))
    try:
        rules = parse_rules_yaml(body.rules_yaml)
    except AppException as exc:
        return LintResponse(valid=False, checks=0, issues=exc.extra.get("issues", []))
    checks, issues = compile_rules(rules, columns)
    issues = attach_lines(body.rules_yaml, issues)
    return LintResponse(valid=not any(i.severity == "error" for i in issues),
                        checks=len(checks), issues=[i.model_dump() for i in issues])
