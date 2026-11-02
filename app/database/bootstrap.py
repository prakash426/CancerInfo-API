"""
Controlled Database Bootstrap Module (CIAPI-L003)

Executes an explicit, non-silent, transactional baseline data bootstrap operation.
Enforces:
1. Deliberate CLI invocation (no automatic execution during API startup).
2. Refusal on already-populated current-model databases by default.
3. Strict isolation and non-modification of legacy tables ('cancer_content').
4. Single-transaction atomicity with complete rollback on failure.
5. Non-mutating validation mode (--validate-only / --dry-run).
6. Application commit and dataset version reporting.
7. Exact row count auditing before and after execution.
"""
import os
import subprocess
from typing import Any, Dict, Optional
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.legacy_audit import audit_legacy_cancer_content, compare_legacy_audits
from app.database.migration_check import get_current_revision, get_head_revision
from app.ingestion.seed import seed_database
from app.models import (
    Cancer,
    CancerAlias,
    ConsensusFact,
    ConsensusFactSource,
    ContentRecord,
    ContentSource,
    ContentVersion,
    IngestionJob,
    Source,
    SourceDocument,
    SourceHealth,
)

DATASET_VERSION = "1.0.0"

CURRENT_MODEL_TABLES = [
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
]


def get_application_commit() -> str:
    """Retrieve the current Git commit hash or environment fallback."""
    env_commit = os.getenv("GIT_COMMIT") or os.getenv("COMMIT_SHA") or os.getenv("RENDER_GIT_COMMIT")
    if env_commit:
        return env_commit[:12]

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return commit[:12]
    except Exception:
        return "unspecified_commit"


def inspect_database_state(engine: Engine) -> Dict[str, Any]:
    """
    Inspects database tables, row counts, and migration status without mutating data.
    Separates legacy 'cancer_content' from current-model tables.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    current_rev = get_current_revision(engine)
    head_rev = get_head_revision()

    # Legacy table inspection
    legacy_found = "cancer_content" in existing_tables
    legacy_rows = 0
    if legacy_found:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM cancer_content"))
            legacy_rows = result.scalar() or 0

    # Current model table inspection
    current_counts: Dict[str, int] = {}
    total_current_rows = 0

    with engine.connect() as conn:
        for tbl in CURRENT_MODEL_TABLES:
            if tbl in existing_tables:
                res = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
                cnt = res.scalar() or 0
                current_counts[tbl] = cnt
                total_current_rows += cnt
            else:
                current_counts[tbl] = 0

    return {
        "existing_tables": sorted(list(existing_tables)),
        "current_revision": current_rev,
        "head_revision": head_rev,
        "is_at_head": (current_rev == head_rev) and (head_rev is not None),
        "legacy_table_found": legacy_found,
        "legacy_rows": legacy_rows,
        "current_model_counts": current_counts,
        "total_current_model_rows": total_current_rows,
        "is_current_model_populated": total_current_rows > 0,
    }


def execute_bootstrap(
    engine: Engine,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Executes controlled bootstrap operation.
    Returns audit dictionary detailing actions taken and row count metrics.
    Refusal on already-populated databases is absolute to prevent data corruption.
    """
    app_commit = get_application_commit()

    # 1. Inspect state
    state = inspect_database_state(engine)

    # 2. Verify schema revision
    if not state["is_at_head"]:
        raise RuntimeError(
            f"Cannot bootstrap database: Schema revision '{state['current_revision']}' "
            f"is not at Alembic head '{state['head_revision']}'. "
            f"Run 'alembic upgrade head' before running bootstrap."
        )

    # 3. Refuse if already populated
    if state["is_current_model_populated"]:
        raise RuntimeError(
            f"Refusing to bootstrap: Current-model database is already populated "
            f"(found {state['total_current_model_rows']} existing records across current-model tables). "
            f"Bootstrap requires an unpopulated current-model database to avoid duplicate rows or silent overwrites. "
            f"Use --validate-only to inspect without modifying."
        )

    # 4. Handle dry-run / validate-only mode
    if dry_run:
        return {
            "status": "VALIDATED_NO_MUTATION",
            "application_commit": app_commit,
            "dataset_version": DATASET_VERSION,
            "legacy_table_found": state["legacy_table_found"],
            "legacy_rows": state["legacy_rows"],
            "pre_counts": state["current_model_counts"],
            "planned_baseline_records": 203,
            "message": "Database is verified and ready for bootstrap. No mutation performed.",
        }

    # 5. Capture pre-execution legacy audit and execute seeding within a single atomic transaction
    pre_legacy_audit = audit_legacy_cancer_content(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Pass commit=False to ensure caller controls the atomic transaction boundary
        seed_database(session, commit=False)
        session.commit()
    except Exception as exc:
        session.rollback()
        raise RuntimeError(
            f"Bootstrap transaction failed and was completely rolled back. Error: {exc}"
        ) from exc
    finally:
        session.close()

    # 6. Verify post-bootstrap state
    post_state = inspect_database_state(engine)

    # 7. Verify legacy table was 100% untouched across all 22 columns, PKs, hashes, and tuples
    if state["legacy_table_found"]:
        post_legacy_audit = audit_legacy_cancer_content(engine)
        compare_legacy_audits(pre_legacy_audit, post_legacy_audit)

    return {
        "status": "SUCCESS",
        "application_commit": app_commit,
        "dataset_version": DATASET_VERSION,
        "legacy_table_found": post_state["legacy_table_found"],
        "legacy_rows": post_state["legacy_rows"],
        "pre_counts": state["current_model_counts"],
        "post_counts": post_state["current_model_counts"],
        "total_records_created": post_state["total_current_model_rows"] - state["total_current_model_rows"],
        "message": "Bootstrap completed successfully in one atomic transaction.",
    }
