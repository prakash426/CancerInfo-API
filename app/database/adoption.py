"""Fail-closed adoption of the unversioned L003 baseline, never an upgrade."""
from typing import Any, Dict

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.database.manifest import CURRENT_MODEL_TABLES
from app.database.migration_check import (
    get_alembic_config, get_current_revision, get_head_revision,
    set_alembic_url_safe,
)
from app.database.session import Base
import app.models  # noqa: F401

BASELINE_REVISION = "0002_document_rights"


class SchemaParityError(Exception):
    """The target cannot safely be stamped as the baseline."""


def verify_schema_parity(engine: Engine) -> Dict[str, Any]:
    """Compare schema with Alembic's dialect-aware type and default checks.

    Python defaults are not server defaults. Unmanaged tables (including
    cancer_content) are deliberately excluded, never dropped or altered.
    """
    inspector = inspect(engine)
    missing = set(CURRENT_MODEL_TABLES) - set(inspector.get_table_names())
    if missing:
        raise SchemaParityError(f"Missing required tables: {sorted(missing)}")
    discrepancies = []
    for name in CURRENT_MODEL_TABLES:
        table = Base.metadata.tables[name]
        actual = {c["name"] for c in inspector.get_columns(name)}
        expected = set(table.columns.keys())
        if expected - actual:
            discrepancies.append(f"{name}: missing expected columns")
        if actual - expected:
            discrepancies.append(f"{name}: unexpected extra columns")
        pk = inspector.get_pk_constraint(name)["constrained_columns"]
        if pk != [c.name for c in table.primary_key.columns]:
            discrepancies.append(f"{name}: primary key mismatch")

    def include_object(obj, name, kind, reflected, compare_to):
        return kind != "table" or name in CURRENT_MODEL_TABLES

    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={
            "compare_type": True,
            "compare_server_default": True,
            "include_object": include_object,
        })
        differences = compare_metadata(context, Base.metadata)
    if discrepancies or differences:
        # Do not print a URL, stored data, or possibly sensitive server defaults.
        raise SchemaParityError(
            "Schema parity verification failed (type mismatch, nullability mismatch, "
            "default, key or index drift). " + "; ".join(discrepancies)
            + f"; dialect-aware differences: {len(differences)}"
        )
    return {"parity_verified": True, "tables_verified": len(CURRENT_MODEL_TABLES)}


def adopt_existing_schema(engine: Engine, dry_run: bool = False) -> Dict[str, Any]:
    if get_current_revision(engine) is not None:
        raise SchemaParityError("Adoption rejected: Database is already managed by Alembic")
    # Do not compare future model definitions then stamp a historical revision.
    if get_head_revision() != BASELINE_REVISION:
        raise SchemaParityError("Adoption baseline requires review for the new migration head")
    parity = verify_schema_parity(engine)
    if dry_run:
        return {
            "status": "PARITY_VERIFIED_DRY_RUN", "current_revision": None,
            "target_baseline_revision": BASELINE_REVISION,
            "tables_verified": parity["tables_verified"],
            "message": "Baseline schema verified; no changes made.",
        }
    cfg = get_alembic_config()
    set_alembic_url_safe(cfg, engine.url.render_as_string(hide_password=False))
    command.stamp(cfg, BASELINE_REVISION)
    if get_current_revision(engine) != BASELINE_REVISION:
        raise RuntimeError("Baseline adoption did not persist the expected revision")
    return {
        "status": "SUCCESSFULLY_ADOPTED", "adopted_revision": BASELINE_REVISION,
        "tables_verified": parity["tables_verified"],
        "message": "Verified unversioned baseline adopted without rewriting data.",
    }
