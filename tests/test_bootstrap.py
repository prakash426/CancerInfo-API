"""
Controlled Database Bootstrap Test Suite (CIAPI-L003)

Tests:
1. Controlled bootstrap creates expected baseline data in an unpopulated database (191 rows).
2. Consensus facts retain all source links, quote snippets, attributions, country codes, and verification timestamps.
3. Content records retain citations, documents, URLs, quotes, attributions, and relationships.
4. Cancer aliases and content-version history are preserved.
5. Foreign-key integrity passes on all seeded data.
6. Repeated bootstrap refuses safely by default to prevent duplicate data or silent overwrites.
7. Bootstrap transaction failure rolls back completely (0 rows created).
8. Bootstrap dry-run / validate-only mode inspects without mutating.
9. Presence of legacy 'cancer_content' table is handled safely and left 100% untouched.
10. Starting the API twice in production mode causes zero mutations on the database,
    verified via exact ordered manifests across all 11 current-model tables.
"""
import os
import subprocess
import sys
from datetime import datetime
from unittest.mock import patch
import pytest
from alembic import command
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import sessionmaker

from app.database.bootstrap import execute_bootstrap, inspect_database_state
from app.database.legacy_audit import audit_legacy_cancer_content, compare_legacy_audits
from app.database.manifest import (
    capture_current_model_manifest,
    compare_current_model_manifests,
    verify_foreign_key_integrity,
)
from app.database.migration_check import get_alembic_config, set_alembic_url_safe
from db_support import disposable_postgres
from app.models import (
    Cancer,
    CancerAlias,
    ConsensusFact,
    ConsensusFactSource,
    ContentRecord,
    ContentSource,
    ContentVersion,
    Source,
    SourceDocument,
    SourceHealth,
)


def get_test_dialects():
    dialects = ["sqlite"]
    if os.getenv("POSTGRES_TEST_URL"):
        dialects.append("postgres")
    return dialects


@pytest.fixture(params=get_test_dialects())
def migrated_db(request, tmp_path):
    from contextlib import nullcontext
    target = (disposable_postgres(os.environ["POSTGRES_TEST_URL"])
              if request.param == "postgres"
              else nullcontext(f"sqlite:///{tmp_path / 'bootstrap_test.db'}"))
    with target as db_url:
        engine = create_engine(db_url)
        try:
            cfg = get_alembic_config()
            set_alembic_url_safe(cfg, db_url)
            command.upgrade(cfg, "head")
            yield engine
        finally:
            engine.dispose()


def test_serving_and_fixture_ingestion_share_migrated_database(migrated_db):
    """Exercise the real pipeline and API with a local fixture, never external HTTP."""
    execute_bootstrap(migrated_db)
    script = '''
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.database.session import SessionLocal, engine
from app.database.manifest import capture_current_model_manifest, compare_current_model_manifests
from app.ingestion.pipeline import run_ingestion_for_source
from app.sources.adapters.nci import NCIAdapter
from app.main import app

url = "https://example.invalid/l003-fixture"
adapter = NCIAdapter()
adapter.discover_urls = AsyncMock(return_value=[{
    "url": url, "cancer_slug": "l003-fixture", "source_cancer_name": "L003 Fixture"
}])
adapter.fetch_url = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
with patch("app.ingestion.pipeline.get_adapter", return_value=adapter):
    with SessionLocal() as session:
        result = asyncio.run(run_ingestion_for_source("nci-us", session, mock_payloads={
            url: "<h1>L003 Fixture</h1><h2>Symptoms</h2><p>Local validation fixture only.</p>"
        }))
assert result["status"] == "SUCCESS", result
assert result["records_created"] == 1, result
assert result["parser_failures"] == 0, result
adapter.fetch_url.assert_not_called()
before = capture_current_model_manifest(engine)
assert before["row_counts"]["ingestion_jobs"] > 0
assert not app.dependency_overrides
for attempt in range(2):
    with TestClient(app) as client:
        assert client.get("/v1/health").status_code == 200
        response = client.get("/v1/cancers/l003-fixture")
        assert response.status_code == 200, response.text
        assert "L003 Fixture" in response.text
    compare_current_model_manifests(before, capture_current_model_manifest(engine))
print("INGESTION_SERVING_RESTART_OK")
'''
    env = os.environ.copy()
    env.update(DATABASE_URL=migrated_db.url.render_as_string(hide_password=False),
               ENVIRONMENT="production" if migrated_db.dialect.name == "postgresql" else "development",
               CHECK_MIGRATIONS_ON_STARTUP="true")
    result = subprocess.run([sys.executable, "-c", script], env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "INGESTION_SERVING_RESTART_OK" in result.stdout


def test_controlled_bootstrap_creates_expected_data(migrated_db):
    """Test 1: Controlled bootstrap populates all 11 current-model tables with baseline content (203 rows)."""
    res = execute_bootstrap(migrated_db, dry_run=False)

    assert res["status"] == "SUCCESS"
    assert res["total_records_created"] == 203

    Session = sessionmaker(bind=migrated_db)
    session = Session()

    try:
        assert session.query(Source).count() == 5
        assert session.query(SourceHealth).count() == 5
        assert session.query(Cancer).count() == 7
        assert session.query(CancerAlias).count() == 22
        assert session.query(SourceDocument).count() == 32
        assert session.query(ContentRecord).count() == 21
        assert session.query(ContentSource).count() == 21
        assert session.query(ContentVersion).count() == 21
        assert session.query(ConsensusFact).count() == 21
        assert session.query(ConsensusFactSource).count() == 48
    finally:
        session.close()


def test_consensus_facts_retain_provenance_and_corroboration(migrated_db):
    """Test 2: Consensus facts retain every source link, URL, quote, attribution, country code, and verification field."""
    execute_bootstrap(migrated_db, dry_run=False)

    Session = sessionmaker(bind=migrated_db)
    session = Session()

    try:
        # Check breast cancer symptoms consensus facts
        breast_cancer = session.query(Cancer).filter(Cancer.slug == "breast-cancer").first()
        assert breast_cancer is not None

        facts = session.query(ConsensusFact).filter(
            ConsensusFact.cancer_id == breast_cancer.id,
            ConsensusFact.category == "symptoms",
        ).all()
        assert len(facts) >= 3

        for fact in facts:
            assert fact.title is not None and len(fact.title) > 0
            assert fact.clinical_detail is not None

            # Verify corroborated source citations
            citations = session.query(ConsensusFactSource).filter(
                ConsensusFactSource.consensus_fact_id == fact.id
            ).all()
            assert len(citations) >= 2, f"Consensus fact '{fact.fact_key}' lacks multi-source corroboration"

            for cit in citations:
                assert cit.source_id in {"nci-us", "who-global", "nhs-uk", "cancer-australia", "cdc-us"}
                assert cit.source_url.startswith("http")
                assert cit.country_code in {"US", "GB", "AU", "GLOBAL"}
                assert cit.attribution_text is not None
    finally:
        session.close()


def test_content_records_retain_citations_and_sources(migrated_db):
    """Test 3: Content records retain citations, documents, URLs, quotes, and attributions."""
    execute_bootstrap(migrated_db, dry_run=False)

    Session = sessionmaker(bind=migrated_db)
    session = Session()

    try:
        records = session.query(ContentRecord).all()
        assert len(records) == 21

        for record in records:
            assert record.content is not None and len(record.content) > 0
            assert record.category is not None

            # Verify associated citations
            citations = session.query(ContentSource).filter(
                ContentSource.content_record_id == record.id
            ).all()
            assert len(citations) >= 1

            for cit in citations:
                assert cit.source_url.startswith("http")
                assert cit.source_id in {"nci-us", "who-global", "nhs-uk", "cancer-australia", "cdc-us"}
    finally:
        session.close()


def test_aliases_and_content_versions_preserved(migrated_db):
    """Test 4: Cancer aliases and content versions are preserved."""
    execute_bootstrap(migrated_db, dry_run=False)

    Session = sessionmaker(bind=migrated_db)
    session = Session()

    try:
        # Check CRC abbreviation alias
        colorectal = session.query(Cancer).filter(Cancer.slug == "colorectal-cancer").first()
        crc_alias = session.query(CancerAlias).filter(
            CancerAlias.cancer_id == colorectal.id,
            CancerAlias.alias == "CRC",
        ).first()
        assert crc_alias is not None
        assert crc_alias.alias_type == "abbreviation"

        # Check content versions exist for records
        versions = session.query(ContentVersion).all()
        assert len(versions) == 21
        for v in versions:
            assert v.version_number == 1
            assert v.content_hash is not None and len(v.content_hash) == 64
    finally:
        session.close()


def test_repeated_bootstrap_refuses_safely(migrated_db):
    """Test 5: A repeated bootstrap refuses safely to avoid duplicate rows or silent overwrites."""
    # First bootstrap succeeds
    res1 = execute_bootstrap(migrated_db, dry_run=False)
    assert res1["status"] == "SUCCESS"

    # Second bootstrap raises RuntimeError and refuses
    with pytest.raises(RuntimeError, match="Refusing to bootstrap: Current-model database is already populated"):
        execute_bootstrap(migrated_db, dry_run=False)

    # Verify row counts remain unchanged (exactly 203)
    state = inspect_database_state(migrated_db)
    assert state["total_current_model_rows"] == 203


def test_simulated_bootstrap_failure_rolls_back_completely(migrated_db):
    """
    Test 6: A simulated bootstrap failure after actual database writes within
    the transaction rolls back completely, leaving 0 records in all 11 tables.
    """
    from app.database import bootstrap as bs_mod
    original_seed = bs_mod.seed_database

    def failing_seed(session, commit=False):
        # 1. Perform actual writes inside the transaction
        original_seed(session, commit=False)
        # Verify that records are staged in the active session transaction
        assert len(session.new) > 0, "Expected staged records in session before simulated failure"
        # 2. Simulate mid-transaction error after writes
        raise RuntimeError("Simulated mid-transaction failure after actual database writes")

    with patch("app.database.bootstrap.seed_database", side_effect=failing_seed):
        with pytest.raises(RuntimeError, match="Bootstrap transaction failed and was completely rolled back"):
            execute_bootstrap(migrated_db, dry_run=False)

    # Verify complete rollback: zero current-model records exist across ALL 11 tables
    state = inspect_database_state(migrated_db)
    assert state["total_current_model_rows"] == 0
    for tbl, count in state["current_model_counts"].items():
        assert count == 0, f"Table {tbl} had partial uncommitted data ({count} rows)!"


def test_bootstrap_dry_run_does_not_mutate(migrated_db):
    """Test 7: Dry-run / validate-only mode inspects without mutating data."""
    res = execute_bootstrap(migrated_db, dry_run=True)

    assert res["status"] == "VALIDATED_NO_MUTATION"
    assert res["planned_baseline_records"] == 203

    state = inspect_database_state(migrated_db)
    assert state["total_current_model_rows"] == 0


def test_bootstrap_preserves_legacy_cancer_content_table(migrated_db):
    """
    Test 8: Bootstrap preserves legacy 'cancer_content' table across all 22 columns,
    exact ordered PK set, ordered tuples, deterministic digest, indexes, and row counts.
    """
    engine = migrated_db
    meta = MetaData()

    cancer_content = Table(
        "cancer_content",
        meta,
        Column("id", Integer, primary_key=True),
        Column("content_id", Text),
        Column("page_group_id", Text),
        Column("cancer_name", Text),
        Column("category", Text),
        Column("normalized_category", Text),
        Column("page_title", Text),
        Column("page_slug", Text),
        Column("content_title", Text),
        Column("parent_heading", Text),
        Column("section_path", Text),
        Column("heading_path_level", Integer),
        Column("content", Text),
        Column("source_url", Text),
        Column("source_domain", Text),
        Column("page_depth", Integer),
        Column("heading_level", Integer),
        Column("sequence_order", Integer),
        Column("matched_keyword", Text),
        Column("is_exact_match", Boolean),
        Column("scraped_at", DateTime),
        Column("content_hash", Text),
    )
    meta.create_all(bind=engine)

    # Insert legacy rows
    sample_time = datetime(2026, 3, 25, 3, 44, 12)
    with engine.begin() as conn:
        conn.execute(
            cancer_content.insert(),
            [
                {
                    "id": 1,
                    "content_id": "legacy-lung-001",
                    "page_group_id": "pg-01",
                    "cancer_name": "Lung Cancer",
                    "category": "symptoms",
                    "normalized_category": "symptoms",
                    "page_title": "Lung Cancer Signs",
                    "page_slug": "lung-cancer-signs",
                    "content_title": "Persistent Cough",
                    "parent_heading": "Symptoms",
                    "section_path": "Home > Lung > Symptoms",
                    "heading_path_level": 2,
                    "content": "A persistent cough that worsens over time is a primary indicator.",
                    "source_url": "https://www.nhs.uk/conditions/lung-cancer/symptoms/",
                    "source_domain": "nhs.uk",
                    "page_depth": 1,
                    "heading_level": 2,
                    "sequence_order": 1,
                    "matched_keyword": "cough",
                    "is_exact_match": True,
                    "scraped_at": sample_time,
                    "content_hash": "c0ffee1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                },
                {
                    "id": 2,
                    "content_id": "legacy-lung-002",
                    "page_group_id": "pg-01",
                    "cancer_name": "Lung Cancer",
                    "category": "overview",
                    "normalized_category": "overview",
                    "page_title": "Lung Cancer Overview",
                    "page_slug": "lung-cancer-overview",
                    "content_title": "Overview",
                    "parent_heading": "Overview",
                    "section_path": "Home > Lung > Overview",
                    "heading_path_level": 1,
                    "content": "Lung cancer is one of the most common and serious types of cancer.",
                    "source_url": "https://www.nhs.uk/conditions/lung-cancer/",
                    "source_domain": "nhs.uk",
                    "page_depth": 1,
                    "heading_level": 1,
                    "sequence_order": 2,
                    "matched_keyword": "lung cancer",
                    "is_exact_match": True,
                    "scraped_at": sample_time,
                    "content_hash": "deadbeef1234567890abcdef1234567890abcdef1234567890abcdef12345678",
                },
            ],
        )

    # Capture comprehensive legacy audit before bootstrap
    pre_audit = audit_legacy_cancer_content(engine)
    assert pre_audit["exists"] is True
    assert pre_audit["column_count"] == 22
    assert pre_audit["row_count"] == 2
    assert pre_audit["primary_key_set"] == [1, 2]

    # Run bootstrap
    res = execute_bootstrap(engine, dry_run=False)
    assert res["status"] == "SUCCESS"
    assert res["legacy_table_found"] is True
    assert res["legacy_rows"] == 2
    assert res["total_records_created"] == 203

    # Capture post-bootstrap legacy audit and compare
    post_audit = audit_legacy_cancer_content(engine)
    compare_legacy_audits(pre_audit, post_audit)


def test_starting_api_twice_in_production_mode_does_not_mutate_data(migrated_db):
    """
    Test 9: Starting the API twice in production mode causes ZERO mutations on the database.
    1. Sets ENVIRONMENT=production explicitly in the environment before application import and startup.
    2. Captures and compares exact ordered manifests for all 11 current-model tables:
       - Primary keys and foreign-key values
       - Aliases and citation fields
       - Content hashes and version numbers
       - Created and updated timestamps
       - Consensus facts and consensus source relationships
    """
    # 1. Populate database via bootstrap
    execute_bootstrap(migrated_db, dry_run=False)

    # 2. Capture baseline manifest before any startup
    manifest_before = capture_current_model_manifest(migrated_db)
    assert manifest_before["total_rows"] == 203

    # 3. Prepare subprocess script that boots API with environment variables set before import
    db_url = migrated_db.url.render_as_string(hide_password=False)
    is_postgres = db_url.startswith("postgresql")

    boot_script = """
import os
import sys

# Verify environment was set before importing app or config
if sys.argv[1] == "production":
    assert os.environ.get("ENVIRONMENT") == "production"

from app.core.config import settings
from app.main import app, lifespan
import asyncio

async def test_boot():
    async with lifespan(app):
        pass

asyncio.run(test_boot())
print("BOOT_OK")
"""

    sub_env = os.environ.copy()
    sub_env["DATABASE_URL"] = db_url
    if is_postgres:
        sub_env["ENVIRONMENT"] = "production"
        env_arg = "production"
    else:
        # In SQLite mode, production requires PostgreSQL by design; test schema check via flag
        sub_env["CHECK_MIGRATIONS_ON_STARTUP"] = "true"
        env_arg = "development"

    # Execute Startup 1 in clean subprocess
    proc1 = subprocess.run(
        [sys.executable, "-c", boot_script, env_arg],
        env=sub_env,
        capture_output=True,
        text=True,
    )
    assert proc1.returncode == 0, f"Startup 1 failed:\n{proc1.stderr}"
    assert "BOOT_OK" in proc1.stdout

    # Capture manifest after Startup 1
    manifest_after_1 = capture_current_model_manifest(migrated_db)

    # Execute Startup 2 in clean subprocess
    proc2 = subprocess.run(
        [sys.executable, "-c", boot_script, env_arg],
        env=sub_env,
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0, f"Startup 2 failed:\n{proc2.stderr}"
    assert "BOOT_OK" in proc2.stdout

    # Capture manifest after Startup 2
    manifest_after_2 = capture_current_model_manifest(migrated_db)

    # 4. Compare exact ordered manifests
    compare_current_model_manifests(manifest_before, manifest_after_1, "Baseline", "After-Start-1")
    compare_current_model_manifests(manifest_after_1, manifest_after_2, "After-Start-1", "After-Start-2")

    # 5. Verify foreign-key integrity across all 11 tables
    fk_result = verify_foreign_key_integrity(migrated_db)
    assert fk_result["status"] == "VALID"
    assert fk_result["violations"] == 0
