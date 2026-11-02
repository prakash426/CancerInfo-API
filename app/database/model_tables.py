"""The authoritative inventory of application-managed tables.

Unmanaged legacy tables and Alembic's revision table are deliberately excluded.
"""
from app.database.session import Base
import app.models  # noqa: F401: populate the complete model registry

CURRENT_MODEL_TABLES = tuple(sorted(Base.metadata.tables))

# Request accounting is managed and schema-verified, but is not part of the corpus.
OPERATIONAL_MODEL_TABLES = ("rate_limit_buckets",)
CORPUS_MODEL_TABLES = tuple(t for t in CURRENT_MODEL_TABLES if t not in OPERATIONAL_MODEL_TABLES)
