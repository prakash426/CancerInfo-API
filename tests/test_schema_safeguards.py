"""The WHO provenance table participates in every schema and data safeguard."""
import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from test_migrations import test_db_url, alembic_cfg  # noqa: F401: dialect fixtures
from app.database.adoption import verify_schema_parity, adopt_existing_schema, SchemaParityError
from app.database.manifest import (CURRENT_MODEL_TABLES, capture_current_model_manifest,
                                   compare_current_model_manifests, verify_foreign_key_integrity)
from app.database.bootstrap import inspect_database_state, execute_bootstrap
from app.database.migration_check import verify_database_schema_at_head, get_current_revision
from app.database.session import Base
from app.models import Cancer, ContentRecord, WhoFactProvenance


@pytest.mark.parametrize("damage", ["missing", "missing_column", "missing_index"])
def test_incomplete_provenance_schema_cannot_be_adopted(test_db_url, damage):
    engine = create_engine(test_db_url)
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            if damage == "missing":
                conn.execute(text("DROP TABLE who_fact_provenance"))
            elif damage == "missing_column":
                conn.execute(text("ALTER TABLE who_fact_provenance DROP COLUMN heading_path"))
            else:
                conn.execute(text("DROP INDEX ix_who_fact_provenance_content_record_id"))
        with pytest.raises(SchemaParityError):
            verify_schema_parity(engine)
        with pytest.raises(SchemaParityError):
            adopt_existing_schema(engine)
        assert get_current_revision(engine) is None
    finally:
        engine.dispose()


def test_stamped_but_incomplete_schema_cannot_start(test_db_url, alembic_cfg):
    engine = create_engine(test_db_url)
    try:
        command.upgrade(alembic_cfg, "head")
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE who_fact_provenance"))
        with pytest.raises(RuntimeError, match="schema validation failed"):
            verify_database_schema_at_head(engine)
    finally:
        engine.dispose()


def test_provenance_rows_are_in_manifests_counts_and_integrity(test_db_url, alembic_cfg):
    engine = create_engine(test_db_url)
    try:
        command.upgrade(alembic_cfg, "head")
        assert set(CURRENT_MODEL_TABLES) == set(Base.metadata.tables)
        with Session(engine) as db:
            cancer = Cancer(slug="schema-fixture", canonical_name="Synthetic schema fixture")
            db.add(cancer)
            db.flush()
            record = ContentRecord(canonical_cancer_id=cancer.id, category="statistics", content="Synthetic")
            db.add(record)
            db.flush()
            row = WhoFactProvenance(content_record_id=record.id, heading_path="Synthetic heading")
            db.add(row)
            db.commit()
            row_id = row.id
        baseline = capture_current_model_manifest(engine)
        assert baseline["row_counts"]["who_fact_provenance"] == 1
        assert inspect_database_state(engine)["current_model_counts"]["who_fact_provenance"] == 1
        assert verify_schema_parity(engine)["tables_verified"] == len(Base.metadata.tables)
        with engine.begin() as conn:
            conn.execute(text("UPDATE who_fact_provenance SET heading_path='changed' WHERE id=:id"), {"id": row_id})
        with pytest.raises(AssertionError, match="who_fact_provenance"):
            compare_current_model_manifests(baseline, capture_current_model_manifest(engine))
        assert verify_foreign_key_integrity(engine)["violations"] == 0
        # Only SQLite permits deliberately constructing an orphan with FK checks
        # off. PostgreSQL enforces this FK at the database level.
        if engine.dialect.name == "sqlite":
            with engine.begin() as conn:
                conn.execute(text("PRAGMA foreign_keys=OFF"))
                conn.execute(text("UPDATE who_fact_provenance SET content_record_id='missing' WHERE id=:id"), {"id": row_id})
            with pytest.raises(AssertionError, match="who_fact_provenance"):
                verify_foreign_key_integrity(engine)
    finally:
        engine.dispose()


def test_provenance_only_database_is_not_considered_empty(tmp_path):
    from app.database.migration_check import get_alembic_config, set_alembic_url_safe
    url = f"sqlite:///{tmp_path / 'provenance-only.db'}"
    cfg = get_alembic_config()
    set_alembic_url_safe(cfg, url)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    try:
        # Deliberately damaged legacy SQLite database with only a provenance row.
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO who_fact_provenance (id, content_record_id) VALUES ('orphan', 'missing')"))
        state = inspect_database_state(engine)
        assert state["total_current_model_rows"] == 1
        assert state["is_current_model_populated"]
        with pytest.raises(RuntimeError, match="already populated"):
            execute_bootstrap(engine)
        assert inspect_database_state(engine)["current_model_counts"]["who_fact_provenance"] == 1
    finally:
        engine.dispose()
