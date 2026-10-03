"""API request/response models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    storage: str
    inline_jobs: bool


# --- profiling ----------------------------------------------------------------

class TopValue(BaseModel):
    value: str
    count: int


class HistogramBin(BaseModel):
    start: float
    end: float
    count: int


class ColumnProfile(BaseModel):
    dtype: str                          # pandas dtype
    inferred_type: str                  # integer | float | boolean | string | datetime
    #                                     | array | mixed | empty
    semantic_type: str | None = None    # email | url | uuid | phone | date
    null_count: int
    null_pct: float
    unique_count: int
    unique_pct: float = 0.0
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    min_length: int | None = None       # text length, or element count for arrays
    max_length: int | None = None
    top_values: list[TopValue] = Field(default_factory=list)
    histogram: list[HistogramBin] = Field(default_factory=list)
    sample_values: list[Any] = Field(default_factory=list)
    is_array: bool = False


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    duplicate_rows: int
    missing_cells: int = 0
    missing_cells_pct: float = 0.0
    memory_bytes: int = 0
    columns: dict[str, ColumnProfile]


# --- datasets -------------------------------------------------------------------

class LastJob(BaseModel):
    id: str
    mode: str
    status: str
    score: float | None = None
    created_at: datetime


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    filename: str
    format: str
    size_bytes: int
    row_count: int
    column_count: int
    created_at: datetime
    updated_at: datetime
    last_job: LastJob | None = None


class DatasetDetail(DatasetOut):
    profile: DatasetProfile
    rules_yaml: str


class DatasetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    rules_yaml: str | None = None


class RowsPage(BaseModel):
    total: int
    offset: int
    limit: int
    columns: list[str]
    rows: list[dict[str, Any]]          # each row: {"_row": int, "values": {...}, "issues": [...]}


# --- rules ----------------------------------------------------------------------

class RulesText(BaseModel):
    rules_yaml: str
    dataset_id: str | None = None       # enables "column not found" warnings


class LintResponse(BaseModel):
    valid: bool
    checks: int
    issues: list[dict[str, Any]]


class SuggestedRules(BaseModel):
    rules_yaml: str


class RuleSetIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    rules_yaml: str


class RuleSetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    rules_yaml: str | None = None


class RuleSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    rules_yaml: str
    created_at: datetime
    updated_at: datetime


# --- validation -----------------------------------------------------------------

class Violation(BaseModel):
    """One failed check, produced by the rule engine."""
    column: str                          # column name, or "(dataset)"
    rule: str
    severity: Literal["error", "warning"] = "error"
    message: str
    failed_count: int = 0
    failed_rows: list[int] = Field(default_factory=list)   # capped for display
    sample_values: list[Any] = Field(default_factory=list)


class JobCreate(BaseModel):
    dataset_id: str
    rules_yaml: str | None = None        # defaults to the dataset's draft rules
    rule_set_id: str | None = None       # or: run a saved rule set
    mode: Literal["sample", "full"] = "full"


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    rule_set_id: str | None
    mode: str
    status: str
    progress: int
    summary: dict[str, Any] | None
    error: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobDetail(JobOut):
    rules_yaml: str
    violations: list[Violation] | None
    dataset_name: str | None = None
