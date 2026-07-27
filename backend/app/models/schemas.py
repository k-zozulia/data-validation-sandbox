from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    redis: str


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class Violation(BaseModel):
    """A single broken rule, produced by the rule engine."""
    column: str
    rule: str
    message: str
    failed_count: int = 0
    failed_rows: list[int] = Field(default_factory=list)


class ColumnProfile(BaseModel):
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    min: float | None = None
    max: float | None = None


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    duplicate_rows: int
    columns: dict[str, ColumnProfile]


class ProfileResponse(BaseModel):
    profile: DatasetProfile
    starter_rules_yaml: str


class ValidationSummary(BaseModel):
    total_violations: int
    rules_failed: list[str]
    columns_flagged: list[str]


class ValidateSampleResponse(BaseModel):
    sample_rows: int
    violations: list[Violation]
    summary: ValidationSummary

class JobCreatedResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str                       # queued | running | done | error
    result: dict | None = None
    error: dict | None = None


class AppException(Exception):
    """Errors that should surface to the client as a clean 4xx.

    Defined here (not in main.py) so routers/services can raise it without a
    circular import. E.g. raise AppException(413, 'file_too_large', 'File exceeds limit').
    """
    def __init__(self, status_code: int, error: str, detail: str | None = None):
        self.status_code = status_code
        self.error = error
        self.detail = detail
        super().__init__(detail or error)