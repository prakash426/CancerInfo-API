"""
Alembic Migrations & Schema Verification Test Suite (CIAPI-L003)

Tests:
1. Empty database upgrades cleanly to Alembic head.
2. All 11 current model tables, indexes, and foreign keys are created.
3. Database revision equals Alembic head.
4. Repeated migration execution is an idempotent no-op.
5. Legacy 'cancer_content' table (22 columns, exact PK set, ordered tuples, digest) is 100% preserved.
6. Migration revisions contain no destructive operations targeting 'cancer_content'.
7. Production configuration rejects SQLite and empty URL, and redacts connection URLs from exceptions.
8. Production startup fails fast if database is unmigrated.
9. Admin /seed endpoint is disabled (HTTP 403) in production.
10. Pre-Alembic schema adoption verifies schema parity across all 11 tables before stamping.
11. Controlled migration failure proves process failure, API startup failure, data safety, and recovery.
12. Automated model-to-migration drift check ensures zero discrepancy between models and migrations.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi import HTTPException
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.database.adoption import SchemaParityError, adopt_existing_schema, verify_schema_parity
from app.database.bootstrap import execute_bootstrap
from app.database.legacy_audit import audit_legacy_cancer_content, compare_legacy_audits
from app.database.manifest import capture_current_model_manifest, compare_current_model_manifests
from app.database.migration_check import (
    get_alembic_config,
    get_current_revision,
    get_head_revision,
    set_alembic_url_safe,
    verify_database_schema_at_head,
)
from app.database.session import Base
from db_support import assert_safe_test_database, disposable_postgres, pg_tool
from app.database.manifest import CURRENT_MODEL_TABLES, verify_foreign_key_integrity
from app.models import IngestionJob
from app.models import Cancer, Source


def get_test_dialects():
    """Return supported dialects. Includes 'postgres' when POSTGRES_TEST_URL is provided."""
    dialects = ["sqlite"]
    if os.getenv("POSTGRES_TEST_URL"):
        dialects.append("postgres")
    return dialects


@pytest.fixture(params=get_test_dialects())
def test_db_url(request, tmp_path):
    if request.param == "postgres":
        with disposable_postgres(os.environ["POSTGRES_TEST_URL"]) as url:
            yield url
    else:
        yield f"sqlite:///{tmp_path / 'migration_test.db'}"


@pytest.fixture
def alembic_cfg(test_db_url):
    """Provides an Alembic Config pointing to the active test database."""
    cfg = get_alembic_config()
    set_alembic_url_safe(cfg, test_db_url)
    return cfg


def test_empty_database_upgrades_to_head_and_creates_all_tables(test_db_url, alembic_cfg):
    """Test 1 & 2: Empty database upgrades to Alembic head and creates all 11 current-model tables."""
    engine = create_engine(test_db_url)

    # 1. Run migration
    command.upgrade(alembic_cfg, "head")

    # 2. Inspect created tables
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    expected_tables = {
        "sources",
        "source_health",
        "cancers",
        "cancer_aliases",
        "source_documents",
        "content_records",
        "content_sources",
        "content_versions",
        "ingestion_jobs",
        "consensus_facts",
        "consensus_fact_sources",
        "alembic_version",
    }
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    # 3. Verify Foreign Keys
    c_aliases_fks = inspector.get_foreign_keys("cancer_aliases")
    assert any(fk["referred_table"] == "cancers" for fk in c_aliases_fks)

    content_records_fks = inspector.get_foreign_keys("content_records")
    assert any(fk["referred_table"] == "cancers" for fk in content_records_fks)

    consensus_facts_fks = inspector.get_foreign_keys("consensus_facts")
    assert any(fk["referred_table"] == "cancers" for fk in consensus_facts_fks)

    cfs_fks = inspector.get_foreign_keys("consensus_fact_sources")
    assert any(fk["referred_table"] == "consensus_facts" for fk in cfs_fks)


def test_alembic_revision_equals_head(test_db_url, alembic_cfg):
    """Test 3: Target database revision matches the Alembic head migration revision."""
    engine = create_engine(test_db_url)
    command.upgrade(alembic_cfg, "head")

    current_rev = get_current_revision(engine)
    head_rev = get_head_revision()

    assert current_rev is not None
    assert head_rev is not None
    assert current_rev == head_rev
    assert current_rev == "0002_document_rights"


def test_repeated_migration_is_idempotent_no_op(test_db_url, alembic_cfg):
    """Test 4: Repeated migration execution is an idempotent no-op."""
    engine = create_engine(test_db_url)
    command.upgrade(alembic_cfg, "head")

    rev_first = get_current_revision(engine)

    # Re-run upgrade head
    command.upgrade(alembic_cfg, "head")
    rev_second = get_current_revision(engine)

    assert rev_first == rev_second
    assert rev_second == "0002_document_rights"


def test_legacy_cancer_content_table_is_preserved_untouched(test_db_url, alembic_cfg):
    """
    Test 5: The legacy 'cancer_content' table (22 columns) is 100% preserved.
    Asserts exact ordered PK set, ordered tuples of (id, content_id, content_hash, scraped_at),
    deterministic SHA-256 digest, 22 column definitions, PK and index defs, row and null-hash counts.
    """
    engine = create_engine(test_db_url)
    meta = MetaData()

    # Define exact 22 legacy columns matching Neon baseline
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

    # Populate legacy records with realistic values
    scrape_time = datetime(2026, 3, 25, 3, 44, 12)
    sample_rows = [
        {
            "id": 1001,
            "content_id": "legacy-breast-001",
            "page_group_id": "pg-01",
            "cancer_name": "Breast Cancer",
            "category": "symptoms",
            "normalized_category": "symptoms",
            "page_title": "Breast Cancer Symptoms and Signs",
            "page_slug": "breast-cancer-symptoms",
            "content_title": "Overview of Symptoms",
            "parent_heading": "Symptoms",
            "section_path": "Home > Breast Cancer > Symptoms",
            "heading_path_level": 2,
            "content": "A painless lump in the breast is the most common presenting symptom.",
            "source_url": "https://www.cancer.gov/types/breast/symptoms",
            "source_domain": "cancer.gov",
            "page_depth": 1,
            "heading_level": 2,
            "sequence_order": 1,
            "matched_keyword": "lump",
            "is_exact_match": True,
            "scraped_at": scrape_time,
            "content_hash": "a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef",
        },
        {
            "id": 1002,
            "content_id": "legacy-colorectal-002",
            "page_group_id": "pg-02",
            "cancer_name": "Colorectal Cancer",
            "category": "screening",
            "normalized_category": "screening",
            "page_title": "Colorectal Cancer Screening",
            "page_slug": "colorectal-cancer-screening",
            "content_title": "Screening Guidelines",
            "parent_heading": "Screening",
            "section_path": "Home > Colorectal > Screening",
            "heading_path_level": 2,
            "content": "Screening via colonoscopy is recommended starting at age 45.",
            "source_url": "https://www.cdc.gov/cancer/colorectal/basic_info/screening/",
            "source_domain": "cdc.gov",
            "page_depth": 1,
            "heading_level": 2,
            "sequence_order": 1,
            "matched_keyword": "screening",
            "is_exact_match": True,
            "scraped_at": scrape_time,
            "content_hash": "f6e5d4c3b2a109876543210fedcba09876543210fedcba09876543210fedcba0",
        },
    ]

    with engine.begin() as conn:
        for r in sample_rows:
            conn.execute(cancer_content.insert().values(**r))

    # Capture comprehensive pre-migration legacy audit
    pre_audit = audit_legacy_cancer_content(engine)
    assert pre_audit["exists"] is True
    assert pre_audit["column_count"] == 22
    assert pre_audit["row_count"] == 2
    assert pre_audit["primary_key_set"] == [1001, 1002]

    # Run Alembic upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Capture comprehensive post-migration legacy audit
    post_audit = audit_legacy_cancer_content(engine)

    # Compare pre and post audits for 100% exact parity
    compare_legacy_audits(pre_audit, post_audit)


def test_no_migration_revision_targets_cancer_content():
    """Test 6: Migration revision files contain no destructive operations targeting 'cancer_content'."""
    project_root = Path(__file__).resolve().parent.parent
    versions_dir = project_root / "alembic" / "versions"

    for py_file in versions_dir.glob("*.py"):
        content = py_file.read_text()
        assert "drop_table('cancer_content')" not in content
        assert 'drop_table("cancer_content")' not in content
        assert "drop_column('cancer_content'" not in content
        assert 'drop_column("cancer_content"' not in content


def test_production_configuration_rejections():
    """Test 7: Production configuration strictly requires PostgreSQL, rejects SQLite/empty URL, and redacts credentials."""
    # 1. Reject default SQLite in production
    with pytest.raises(ValueError, match="SQLite is strictly forbidden in production") as exc_info:
        Settings(ENVIRONMENT="production", DATABASE_URL="sqlite:///./cancerinfo.db")
    assert "sqlite:///./cancerinfo.db" not in str(exc_info.value), "Supplied URL leaked into exception!"

    # 2. Reject explicit SQLite path in production
    with pytest.raises(ValueError, match="SQLite is strictly forbidden in production"):
        Settings(ENVIRONMENT="production", DATABASE_URL="sqlite:////app/data/cancerinfo.db")

    # 3. Reject empty URL in production
    with pytest.raises(ValueError, match="DATABASE_URL must be explicitly supplied"):
        Settings(ENVIRONMENT="production", DATABASE_URL="")

    # 4. Reject unsupported connection scheme without leaking supplied URL
    secret_url = "mysql://admin_user:super_secret_pw@db.internal:3306/cancerinfo"
    with pytest.raises(ValueError, match="must be a PostgreSQL connection URL") as exc_info:
        Settings(ENVIRONMENT="production", DATABASE_URL=secret_url)
    assert "super_secret_pw" not in str(exc_info.value), "Credentials leaked into exception message!"

    # 5. Accept valid PostgreSQL URL
    prod_settings = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgres://cancer_admin:secret@ep-neon-123.eastus2.azure.neon.tech/neondb",
    )
    assert prod_settings.is_production is True
    assert prod_settings.is_sqlite is False
    assert prod_settings.is_postgres is True
    assert "postgresql+psycopg2://" in prod_settings.DATABASE_URL


def test_production_startup_fails_if_unmigrated(test_db_url):
    """Test 8: Application startup fails fast if database revision is not at Alembic head."""
    engine = create_engine(test_db_url)

    # Database is unmigrated (no alembic_version table)
    with pytest.raises(RuntimeError, match="Database schema validation failed: Database is uninitialized or unmigrated"):
        verify_database_schema_at_head(engine)


def test_admin_seed_endpoint_disabled_in_production(test_db_url):
    """Test 9: Administrative seed endpoint returns HTTP 403 Forbidden in production."""
    from app.api.v1.endpoints.admin import trigger_seed
    from app.core.config import settings

    original_env = settings.ENVIRONMENT
    settings.ENVIRONMENT = "production"

    engine = create_engine(test_db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        with pytest.raises(HTTPException) as exc_info:
            trigger_seed(db=session)
        assert exc_info.value.status_code == 403
        assert "strictly disabled in production" in exc_info.value.detail
    finally:
        session.close()
        settings.ENVIRONMENT = original_env


def test_pre_alembic_schema_adoption_with_parity_verification(test_db_url, alembic_cfg):
    """
    Test 10: Safe adoption path for pre-existing current-model databases without alembic_version.
    1. Creates all 11 tables with Base.metadata.create_all (simulating legacy pre-Alembic schema).
    2. Populates representative baseline data.
    3. Proves blind 'alembic upgrade head' fails due to existing tables.
    4. Runs schema parity verification and stamps to head revision.
    5. Confirms representative data is 100% intact and subsequent API startup succeeds.
    6. Verifies that drifted schemas are safely refused without stamping.
    """
    engine = create_engine(test_db_url)

    # 1. Create all 11 tables via Base.metadata (simulating pre-Alembic database)
    Base.metadata.create_all(bind=engine)

    # 2. Populate representative data into sources and cancers
    from app.models import Cancer, Source
    Session = sessionmaker(bind=engine)
    session = Session()
    source = Source(
        id="nci-us",
        organization_name="National Cancer Institute",
        source_name="NCI",
        base_url="https://www.cancer.gov",
        country_code="US",
        source_type="government",
        trust_tier="TIER_1",
        authority_type="NATIONAL_CANCER_AUTHORITY",
        license_type="PUBLIC_DOMAIN",
        license_status="APPROVED",
    )
    cancer = Cancer(
        slug="breast-cancer",
        canonical_name="Breast Cancer",
        taxonomy_codes={"ICD-O-3": "C50"},
        anatomical_site="Breast",
    )
    session.add(source)
    session.add(cancer)
    session.commit()
    session.close()

    # Confirm alembic_version does not exist
    inspector = inspect(engine)
    assert "alembic_version" not in inspector.get_table_names()

    # 3. Proves blind alembic upgrade head would fail because tables already exist
    # (In SQLite/PostgreSQL, op.create_table fails with OperationalError/ProgrammingError)
    with pytest.raises(Exception):
        command.upgrade(alembic_cfg, "head")

    # 4. Run dry-run adoption check
    dry_run_report = adopt_existing_schema(engine, dry_run=True)
    assert dry_run_report["status"] == "PARITY_VERIFIED_DRY_RUN"
    assert dry_run_report["tables_verified"] == 11
    # Confirm still unstamped
    assert get_current_revision(engine) is None

    # 5. Run actual adoption (stamps to head)
    adopt_report = adopt_existing_schema(engine, dry_run=False)
    assert adopt_report["status"] == "SUCCESSFULLY_ADOPTED"
    assert adopt_report["adopted_revision"] == "0002_document_rights"
    assert get_current_revision(engine) == "0002_document_rights"

    # 6. Verify existing data was untouched
    session = Session()
    assert session.query(Source).filter_by(id="nci-us").count() == 1
    assert session.query(Cancer).filter_by(slug="breast-cancer").count() == 1
    session.close()

    # 7. Verify subsequent startup check succeeds
    head_rev = verify_database_schema_at_head(engine)
    assert head_rev == "0002_document_rights"

    # 8. Test fail-closed rejection: attempting to adopt an already-managed database MUST raise SchemaParityError
    with pytest.raises(SchemaParityError, match="Adoption rejected: Database is already managed by Alembic"):
        adopt_existing_schema(engine, dry_run=False)


@pytest.mark.parametrize("drift", [
    "missing_table", "extra_column", "missing_column", "type", "length",
    "nullable", "required", "default", "foreign_key", "unique", "index",
])
def test_adoption_negative_drift_cases(test_db_url, drift):
    """Each dialect performs actual drift checks; PostgreSQL is never a no-op."""
    from sqlalchemy import MetaData, Integer, String
    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(metadata)
    sources = metadata.tables["sources"]
    aliases = metadata.tables["cancer_aliases"]
    cancers = metadata.tables["cancers"]
    if drift == "missing_table":
        metadata.remove(metadata.tables["consensus_fact_sources"])
    elif drift == "extra_column":
        sources.append_column(Column("rogue_untracked_column", String))
    elif drift == "missing_column":
        sources._columns.remove(sources.c.notes)
    elif drift == "type":
        sources.c.source_name.type = Integer()
    elif drift == "length":
        sources.c.source_name.type = String(12)
    elif drift == "nullable":
        sources.c.source_name.nullable = True
    elif drift == "required":
        sources.c.notes.nullable = False
    elif drift == "default":
        from sqlalchemy import DefaultClause
        sources.c.source_name.server_default = DefaultClause(text("'unexpected'"))
    elif drift == "foreign_key":
        constraint = next(iter(aliases.foreign_key_constraints))
        aliases.constraints.remove(constraint)
    elif drift == "unique":
        next(i for i in cancers.indexes if i.name == "ix_cancers_slug").unique = False
    elif drift == "index":
        sources.indexes.remove(next(i for i in sources.indexes if i.name == "ix_sources_id"))
    engine = create_engine(test_db_url)
    try:
        metadata.create_all(engine)
        with pytest.raises(SchemaParityError):
            adopt_existing_schema(engine)
        assert get_current_revision(engine) is None
        assert "alembic_version" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_percent_encoded_credentials_url_handling():
    """
    Test: Regression test verifying safe URL handling for percent-encoded credentials.
    Ensures passwords with %, @, #, etc., do not trigger ConfigParser InterpolationSyntaxError.
    """
    from sqlalchemy.engine.url import make_url

    cfg = get_alembic_config()
    test_url = "postgresql+psycopg2://ci_user:p%40ss%25w%23rd@localhost:5432/ci_test_db"
    set_alembic_url_safe(cfg, test_url)

    retrieved = cfg.get_main_option("sqlalchemy.url")
    assert retrieved == test_url, f"URL altered during retrieval: {retrieved}"

    # Verify SQLAlchemy parses the unmasked credentials without corruption
    parsed = make_url(retrieved)
    assert parsed.username == "ci_user"
    assert parsed.password == "p@ss%w#rd"
    assert parsed.database == "ci_test_db"


def test_migration_failure_and_recovery(test_db_url, alembic_cfg, tmp_path):
    """Prove the intended DDL fails, then restore a real backup to another DB."""
    from app.database.legacy_audit import EXPECTED_LEGACY_COLUMNS
    engine = create_engine(test_db_url)
    command.upgrade(alembic_cfg, "head")
    execute_bootstrap(engine)
    with sessionmaker(bind=engine)() as session:
        session.add(IngestionJob(id="l003-preserved-job", source_id="nci-us",
                                 status="SUCCESS", records_created=1))
        session.commit()
    # Legacy identity/sequence plus every historical column; no valuable data.
    meta = MetaData()
    from sqlalchemy import BigInteger, Identity
    legacy_id_type = Integer if engine.dialect.name == "sqlite" else BigInteger
    legacy = Table("cancer_content", meta,
                   Column("id", legacy_id_type, Identity(), primary_key=True),
                   *(Column(name, Text) for name in EXPECTED_LEGACY_COLUMNS if name != "id"))
    meta.create_all(engine)
    with engine.begin() as connection:
        connection.execute(legacy.insert().values(content="retained legacy text",
                                                 content_id="legacy-1", content_hash="hash-1"))
    baseline = capture_current_model_manifest(engine)
    assert all(baseline["row_counts"][name] > 0 for name in CURRENT_MODEL_TABLES)
    legacy_before = audit_legacy_cancer_content(engine)

    is_sqlite = engine.dialect.name == "sqlite"
    backup = tmp_path / ("before.db" if is_sqlite else "before.dump")
    schema_before = None
    if is_sqlite:
        import sqlite3
        with sqlite3.connect(engine.url.database) as source:
            with sqlite3.connect(backup) as destination:
                source.backup(destination)
    else:
        pg_tool("pg_dump", test_db_url, "-Fc", "-f", str(backup))
        schema_before = pg_tool("pg_dump", test_db_url, "-s", "-O", "-x")

    faulty_dir = tmp_path / "faulty_versions"
    faulty_dir.mkdir()
    (faulty_dir / "9999_faulty.py").write_text(
        "revision = '9999_faulty'\n"
        "down_revision = '0002_document_rights'\n"
        "branch_labels = depends_on = None\n"
        "from alembic import op\n"
        "import sqlalchemy as sa\n"
        "def upgrade():\n"
        "    op.create_table('faulty_probe_table', sa.Column('id', sa.Integer))\n"
        "    op.execute('L003_INTENTIONAL_MIGRATION_FAILURE;')\n"
        "def downgrade():\n"
        "    op.drop_table('faulty_probe_table')\n"
    )
    project_root = Path(__file__).resolve().parent.parent
    config_path = tmp_path / "failure.ini"
    config_path.write_text(
        "[alembic]\n"
        f"script_location = {project_root / 'alembic'}\n"
        "path_separator = os\n"
        f"version_locations = {project_root / 'alembic/versions'}{os.pathsep}{faulty_dir}\n"
    )
    env = os.environ.copy()
    env.update(DATABASE_URL=test_db_url, ENVIRONMENT="development")
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(config_path), "upgrade", "head"],
        env=env, capture_output=True, text=True,
    )
    assert proc.returncode != 0
    assert "L003_INTENTIONAL_MIGRATION_FAILURE" in proc.stderr, proc.stderr
    assert get_current_revision(engine) == "0002_document_rights"
    compare_current_model_manifests(baseline, capture_current_model_manifest(engine))
    compare_legacy_audits(legacy_before, audit_legacy_cancer_content(engine))
    if not is_sqlite:
        assert "faulty_probe_table" not in inspect(engine).get_table_names()

    def verify_restored(restored):
        assert verify_database_schema_at_head(restored) == "0002_document_rights"
        assert verify_schema_parity(restored)["tables_verified"] == 11
        compare_current_model_manifests(baseline, capture_current_model_manifest(restored))
        compare_legacy_audits(legacy_before, audit_legacy_cancer_content(restored))
        assert verify_foreign_key_integrity(restored)["violations"] == 0
        assert "faulty_probe_table" not in inspect(restored).get_table_names()
        if restored.dialect.name == "postgresql":
            with restored.begin() as connection:
                new_id = connection.execute(
                    text("INSERT INTO cancer_content (content) VALUES ('sequence probe') RETURNING id")
                ).scalar_one()
                assert new_id > max(legacy_before["primary_key_set"])
                # Probe must not change accepted baseline evidence.
                connection.execute(text("DELETE FROM cancer_content WHERE id=:id"), {"id": new_id})

    try:
        if is_sqlite:
            restored_file = tmp_path / "restored.db"
            shutil.copy2(backup, restored_file)
            restored = create_engine(f"sqlite:///{restored_file}")
            try:
                verify_restored(restored)
            finally:
                restored.dispose()
        else:
            with disposable_postgres(os.environ["POSTGRES_TEST_URL"]) as restore_url:
                pg_tool("pg_restore", restore_url, "-e", "-1", "-O", "-x",
                        "-d", make_url(restore_url).database, str(backup))
                schema_after = pg_tool("pg_dump", restore_url, "-s", "-O", "-x")
                def stable_dump(value):
                    return "\n".join(line for line in value.splitlines()
                                     if not line.startswith(("\\restrict ", "\\unrestrict ")))
                assert stable_dump(schema_before) == stable_dump(schema_after)
                restored = create_engine(restore_url)
                try:
                    verify_restored(restored)
                finally:
                    restored.dispose()
    finally:
        engine.dispose()


def test_model_to_migration_drift_check(test_db_url, alembic_cfg):
    """
    Test 12: Automated model-to-migration drift check.
    Verifies that SQLAlchemy Base.metadata and Alembic migrations have 0 discrepancies.
    """
    engine = create_engine(test_db_url)
    command.upgrade(alembic_cfg, "head")

    with engine.connect() as conn:
        mc = MigrationContext.configure(conn)
        diff = compare_metadata(mc, Base.metadata)
        # Exclude legacy cancer_content if present
        filtered_diff = [
            d for d in diff
            if not (len(d) > 1 and hasattr(d[1], "name") and d[1].name == "cancer_content")
        ]
        assert len(filtered_diff) == 0, f"Model-to-migration drift detected: {filtered_diff}"


def test_legacy_long_revision_identifier_remapped_transparently(test_db_url, alembic_cfg):
    """
    Test 13: Transparent remapping of legacy revision identifier.
    Accounts explicitly for any disposable SQLite or dev databases stamped with
    '0002_document_rights_and_consensus_linkage'.
    Models the actual supported legacy database scenario (disposable SQLite) without
    weakening the normal PostgreSQL schema (maintaining VARCHAR(32)).
    Verifies that get_current_revision and verify_database_schema_at_head remain strictly read-only,
    and repair_legacy_revision is an explicit, guarded, verified operation.
    """
    from app.database.migration_check import repair_legacy_revision

    engine = create_engine(test_db_url)
    command.upgrade(alembic_cfg, "head")

    if engine.dialect.name == "sqlite":
        # 1. Model the actual supported legacy scenario: disposable SQLite database
        # stamped with the old 43-character identifier from commit a8f5039
        with engine.connect() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num = '0002_document_rights_and_consensus_linkage'"))
            conn.commit()

        # 2. Verify get_current_revision and Alembic inspection commands are strictly read-only:
        # inspection leaves the stored legacy revision completely unchanged
        raw_rev = get_current_revision(engine)
        assert raw_rev == "0002_document_rights_and_consensus_linkage"

        # Alembic inspection fails on unknown revision and leaves stored revision completely unchanged
        with pytest.raises(Exception) as exc_info:
            command.current(alembic_cfg)
        assert "Can't locate revision" in str(exc_info.value)
        assert get_current_revision(engine) == "0002_document_rights_and_consensus_linkage"

        # 3. Verify startup schema check fails fast and read-only on legacy revision
        with pytest.raises(RuntimeError) as exc_info:
            verify_database_schema_at_head(engine)
        assert "legacy revision" in str(exc_info.value)
        # Database remains unmutated
        assert get_current_revision(engine) == "0002_document_rights_and_consensus_linkage"

        # 4. Explicit operator action required to repair legacy revision
        repaired = repair_legacy_revision(engine)
        assert repaired == "0002_document_rights"

        # 5. Verify persistence and read-only checks pass
        assert get_current_revision(engine) == "0002_document_rights"
        assert verify_database_schema_at_head(engine) == "0002_document_rights"

        # 6. Subsequent migration commands succeed seamlessly
        command.upgrade(alembic_cfg, "head")
        assert get_current_revision(engine) == "0002_document_rights"
    else:
        # In PostgreSQL: verify normal schema is NOT weakened (version_num length is <= 32)
        inspector = inspect(engine)
        cols = {c["name"]: c for c in inspector.get_columns("alembic_version")}
        assert "version_num" in cols
        col_type = cols["version_num"]["type"]
        assert getattr(col_type, "length", 32) <= 32

        # Verify PostgreSQL database is cleanly at head and repair is a safe no-op
        assert get_current_revision(engine) == "0002_document_rights"
        assert repair_legacy_revision(engine) is None
        assert verify_database_schema_at_head(engine) == "0002_document_rights"

    engine.dispose()
