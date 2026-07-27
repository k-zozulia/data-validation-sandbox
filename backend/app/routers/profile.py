"""POST /datasets/profile — file -> {profile, starter_rules_yaml} (synchronous)."""
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.models.schemas import ProfileResponse
from app.parsers import load_dataframe
from app.services.profiler import profile_dataframe
from app.services.yaml_generator import generate_rules, rules_to_yaml

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/profile", response_model=ProfileResponse)
async def profile_dataset(file: UploadFile = File(...)):
    raw = await file.read()
    df = load_dataframe(file.filename, raw)          # full file for representative stats
    profile = profile_dataframe(df)
    rules = generate_rules(profile)
    return ProfileResponse(profile=profile, starter_rules_yaml=rules_to_yaml(rules))