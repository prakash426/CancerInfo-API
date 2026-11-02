"""
Application Configuration
"""
import json
from typing import List, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "CancerInfo API"
    APP_DESCRIPTION: str = (
        "A free, structured, global, source-transparent public REST API aggregating "
        "normalized cancer knowledge with fact-level provenance from authoritative health organizations."
    )
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/v1"
    ENVIRONMENT: str = "development"

    # Database configuration (PostgreSQL / Neon / SQLite)
    DATABASE_URL: str = "sqlite:///./cancerinfo.db"
    CHECK_MIGRATIONS_ON_STARTUP: bool = False

    # Connection pooling settings (sized conservatively for Neon hosted limits)
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Security & Admin
    ADMIN_API_KEY: str = "dev-admin-secret-key"
    RATE_LIMIT_PER_MINUTE: int = 120

    # Keys are issued only after reviewing the downstream application and use.
    # Store SHA-256 digests, never plaintext keys, in deployment secrets.
    NONCOMMERCIAL_API_KEY_SHA256: List[str] = Field(default_factory=list, repr=False)

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = False

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @field_validator("NONCOMMERCIAL_API_KEY_SHA256")
    @classmethod
    def validate_noncommercial_keys(cls, values):
        import re
        if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in values):
            raise ValueError("Noncommercial approvals require lowercase SHA-256 key digests.")
        return values

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = json.loads(v) if v.strip().startswith("[") else v.split(",")
        if not isinstance(v, list) or not all(isinstance(origin, str) for origin in v):
            raise ValueError("CORS_ORIGINS must be a list or comma-separated origins.")
        return [origin.strip() for origin in v if origin.strip()]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            # Normalize legacy postgres:// and bare postgresql:// to postgresql+psycopg2://
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+psycopg2://", 1)
            elif v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.CORS_ALLOW_CREDENTIALS and "*" in self.CORS_ORIGINS:
            raise ValueError("Credentialed CORS requires explicit origins; wildcard origins are forbidden.")
        if self.is_production:
            if not self.DATABASE_URL or self.DATABASE_URL.strip() == "":
                raise ValueError(
                    "Production configuration error: DATABASE_URL must be explicitly supplied. "
                    "A missing or empty database URL is strictly forbidden in production."
                )
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError(
                    "Production configuration error: SQLite is strictly forbidden in production. "
                    "Production requires a valid PostgreSQL connection URL."
                )
            if not (self.DATABASE_URL.startswith("postgresql://") or self.DATABASE_URL.startswith("postgresql+")):
                raise ValueError(
                    "Production configuration error: DATABASE_URL must be a PostgreSQL connection URL "
                    "(starting with postgresql:// or postgresql+psycopg2://). "
                    "The supplied connection scheme is not supported."
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")


settings = Settings()
