"""Additive approvals preserve populated content and default to no new grants."""
from alembic import command
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from test_migrations import test_db_url, alembic_cfg  # noqa: F401
from app.database.manifest import capture_current_model_manifest
from app.ingestion.seed import seed_database
from app.models import SourceDocument, WhoFactProvenance, ContentRecord

NEW_COLUMNS = ("publication_record_reviews", "noncommercial_redistribution_allowed", "approved_publication_content_types")


def test_populated_approval_upgrade_and_rollback_preserve_data(test_db_url, alembic_cfg):
    engine = create_engine(test_db_url)
    try:
        command.upgrade(alembic_cfg, "head")
        with Session(engine) as db:
            seed_database(db)
            record = db.query(ContentRecord).first()
            db.add(WhoFactProvenance(content_record_id=record.id, heading_path="Preserved locator"))
            db.commit()
        command.downgrade(alembic_cfg, "0003_who_provenance")
        before = capture_current_model_manifest(engine)
        command.upgrade(alembic_cfg, "head")
        with Session(engine) as db:
            assert db.query(SourceDocument).count() > 0
            for doc in db.query(SourceDocument):
                assert doc.noncommercial_redistribution_allowed is None
                assert doc.approved_publication_content_types is None
        after = capture_current_model_manifest(engine)
        assert after["row_counts"] == before["row_counts"]
        for row in after["tables"]["source_documents"]:
            for name in NEW_COLUMNS:
                assert row.pop(name) is None
        assert after["tables"] == before["tables"]
        command.downgrade(alembic_cfg, "0003_who_provenance")
        assert capture_current_model_manifest(engine) == before
    finally:
        engine.dispose()
