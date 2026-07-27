"""POST /datasets/validate-sample — file + rules YAML -> violations on first N rows."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.config import settings
from app.models.schemas import ValidateSampleResponse, ValidationSummary, Violation
from app.parsers import load_dataframe
from app.services.yaml_generator import parse_rules_yaml
from app.validators.rule_engine import run_rules

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _summarize(violations: list[Violation]) -> ValidationSummary:
    return ValidationSummary(
        total_violations=len(violations),
        rules_failed=sorted({v.rule for v in violations}),
        columns_flagged=sorted({v.column for v in violations}),
    )


@router.post("/validate-sample", response_model=ValidateSampleResponse)
async def validate_sample(file: UploadFile = File(...), rules_yaml: str = Form(...)):
    raw = await file.read()
    df = load_dataframe(file.filename, raw, nrows=settings.sample_rows)  # sample only
    rules = parse_rules_yaml(rules_yaml)

    violations = run_rules(df, rules)
    violations = violations[: settings.max_violations_stored]  # cap what we return
    return ValidateSampleResponse(
        sample_rows=len(df),
        violations=violations,
        summary=_summarize(violations),
    )