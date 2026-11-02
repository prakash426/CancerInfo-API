import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.core.config import settings
from app.database.session import Base
# Import all models so Base.metadata is fully populated
import app.models  # noqa: F401

config = context.config

if config.config_file_name is not None and config.file_config.has_section("loggers"):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Determine database URL: prioritize explicitly configured URL, then env var, then settings
url_from_config = config.get_main_option("sqlalchemy.url")
if not url_from_config or "driver://user:pass@localhost/dbname" in url_from_config:
    database_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL
else:
    database_url = url_from_config

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)

config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))


def include_object(object, name, type_, reflected, compare_to):
    """
    Ensure Alembic completely ignores the legacy `cancer_content` table
    present in the production Neon database.
    """
    if type_ == "table" and name == "cancer_content":
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
