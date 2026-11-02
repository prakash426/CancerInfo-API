"""
Application Configuration
"""
from typing import List, Union
from pydantic import field_validator, model_validator
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

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = ["*"]

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v  # type: ignore
        return ["*"]

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
