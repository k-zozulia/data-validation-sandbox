from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single source of truth for settings and the app's "magic numbers".

    Every field can be overridden with an environment variable of the same name
    (case-insensitive), e.g. DATABASE_URL, STORAGE_BACKEND, MAX_FILE_SIZE_MB.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Infrastructure -----------------------------------------------------
    # SQLite works out of the box; docker-compose points this at Postgres.
    database_url: str = "sqlite:///./data/dvs.db"
    redis_url: str = "redis://localhost:6379/0"

    # Run validation jobs in the API process instead of a Celery worker.
    # Handy for tests and for a quick start without Redis.
    inline_jobs: bool = False

    # Object storage for uploaded files and job artifacts: "local" | "s3".
    storage_backend: str = "local"
    storage_dir: Path = Path("./data/storage")
    s3_bucket: str = "dvs-local"
    s3_endpoint_url: str | None = None      # e.g. http://minio:9000 for MinIO

    # --- Ingestion limits ---------------------------------------------------
    max_file_size_mb: int = 100
    max_columns: int = 500              # reject pathologically wide files early
    max_rows: int = 2_000_000
    max_json_depth: int = 5             # matches the "one level of arrays" scope

    # --- Validation ---------------------------------------------------------
    sample_rows: int = 1_000            # random sample size for the quick check
    sample_seed: int = 42               # deterministic sample => comparable results
    keep_sample_jobs: int = 10          # per dataset; older sample jobs are pruned
    max_failed_rows_per_violation: int = 200   # stored for display; full list -> storage
    regex_timeout_sec: float = 1.0      # per-value ReDoS guard
    job_soft_time_limit: int = 600
    dataset_cache_size: int = 4         # parsed DataFrames kept in memory per process

    # Comma-separated list of allowed origins (overridable via env CORS_ORIGINS).
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://localhost:3000,http://localhost:8080",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()
