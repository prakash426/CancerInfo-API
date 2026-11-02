"""The authoritative inventory of application-managed tables.

Unmanaged legacy tables and Alembic's revision table are deliberately excluded.
"""
from app.database.session import Base
import app.models  # noqa: F401: populate the complete model registry

CURRENT_MODEL_TABLES = tuple(sorted(Base.metadata.tables))
