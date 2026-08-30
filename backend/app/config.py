from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Single source of truth for settings and the app's "magic numbers"."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    s3_bucket: str = "dvs-local"

    # --- Ingestion limits ---
    max_file_size_mb: int = 50
    max_columns: int = 500              # reject pathologically wide files early
    max_rows_full_run: int = 1_000_000
    max_json_depth: int = 5             # matches the "one level of arrays" scope

    # --- Sandbox sample check ---
    sample_rows: int = 500              # representative vs the <2s feedback target

    # --- Ephemeral state ---
    # Keep this equal to the S3 lifecycle window so nothing outlives its pair.
    job_ttl_seconds: int = 24 * 3600
    # Redis is not a blob store: cap detailed violations kept there; the full
    # clean/quarantine output goes to S3 (referenced by violations_ref).
    max_violations_stored: int = 10_000

    # Comma-separated list of allowed origins (overridable via env CORS_ORIGINS).
    cors_origins_raw: str = Field(
    default="http://localhost:5173,http://localhost:3000",
    alias="CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


settings = Settings()