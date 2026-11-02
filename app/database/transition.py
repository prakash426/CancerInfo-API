"""
Controlled, Transactional, Repeat-Safe Database Transition Module (CIAPI-L004)

Transitions populated CIAPI-L003 databases to CIAPI-L004 without reseeding, wiping,
or overwriting existing quotes, attributions, content history, or versioned records.

Operations performed:
1. Verifies that schema is at head (0002_document_rights) with L004 columns.
2. Updates or creates candidate SourceDocument records with exact rights metadata
   from the authoritative RIGHTS_INVENTORY without disturbing existing content.
3. Links existing ConsensusFactSource records to their corresponding SourceDocument
   via source_document_id by matching URLs, preserving quote snippets and attribution text.
4. Executes within a single atomic transaction with rollback on failure.
5. Provides repeat-safe, idempotent execution and --dry-run validation mode.
"""
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.migration_check import get_current_revision, get_head_revision
from app.ingestion.rights_inventory import RIGHTS_INVENTORY
from app.models import Cancer, ConsensusFactSource, SourceDocument


class TransitionError(RuntimeError):
    """Raised when database transition prerequisites fail."""
    pass


def inspect_transition_readiness(engine: Engine) -> Dict[str, Any]:
    """
    Inspects target database schema and existing records to determine transition readiness.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    current_rev = get_current_revision(engine)
    head_rev = get_head_revision()

    if "source_documents" not in tables or "consensus_fact_sources" not in tables:
        raise TransitionError("Database does not contain required tables (source_documents, consensus_fact_sources).")

    if current_rev != head_rev:
        raise TransitionError(
            f"Database schema revision '{current_rev}' is not at supported head revision '{head_rev}'. "
            f"Run 'alembic upgrade head' before running transition."
        )

    sd_cols = {c["name"] for c in inspector.get_columns("source_documents")}
    cfs_cols = {c["name"] for c in inspector.get_columns("consensus_fact_sources")}

    required_sd_cols = {"publication_status", "rights_evidence_url", "permissible_use"}
    missing_sd_cols = required_sd_cols - sd_cols
    if missing_sd_cols:
        raise TransitionError(
            f"source_documents is missing L004 rights columns: {sorted(missing_sd_cols)}. "
            f"Run 'alembic upgrade head' before running transition."
        )

    if "source_document_id" not in cfs_cols:
        raise TransitionError(
            "consensus_fact_sources is missing L004 column 'source_document_id'. "
            "Run 'alembic upgrade head' before running transition."
        )

    return {
        "current_revision": current_rev,
        "head_revision": head_rev,
        "is_at_head": True,
        "tables": sorted(list(tables)),
    }


def transition_populated_l003_database(
    engine: Engine,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Executes controlled, repeat-safe transition on a populated L003 database.
    Populates document rights decisions and consensus citation linkages without
    reseeding or overwriting existing quotes, attribution, history, or clinical content.

    Preserves existing owner reviews, evidence, attribution, and permission references
    across process restarts and repeated runs.
    Enforces the supported schema revision and verifies citation linkage postconditions
    before committing. Never reports SUCCESS with unresolved links.
    """
    readiness = inspect_transition_readiness(engine)

    SessionLocal = sessionmaker(bind=engine)
    session: Session = SessionLocal()

    try:
        # Pre-transition audit metrics
        pre_total_docs = session.query(SourceDocument).count()
        pre_total_citations = session.query(ConsensusFactSource).count()
        unlinked_citations = session.query(ConsensusFactSource).filter(
            ConsensusFactSource.source_document_id.is_(None)
        ).count()

        docs_updated = 0
        docs_created = 0
        citations_linked = 0
        citations_already_linked = 0

        # 1. Populate document rights without touching existing quotes/content/versions
        for url, decision in sorted(RIGHTS_INVENTORY.items()):
            doc = session.query(SourceDocument).filter(
                SourceDocument.original_url == url
            ).first()

            if doc:
                # Check whether doc already has an owner review recorded
                has_owner_review = (doc.rights_reviewed_at is not None) or bool(doc.rights_reviewer and str(doc.rights_reviewer).strip())

                if has_owner_review:
                    # PRESERVE existing owner reviews, evidence, attribution, and permission references across restarts and repeated runs
                    # Do NOT overwrite rights_reviewed_at or rights_reviewer with None or defaults
                    if not doc.rights_evidence_url and decision.rights_evidence_url:
                        doc.rights_evidence_url = decision.rights_evidence_url
                    if not doc.permissible_use and decision.permissible_use:
                        doc.permissible_use = decision.permissible_use
                    if not doc.attribution_text and decision.attribution_text:
                        doc.attribution_text = decision.attribution_text
                    if not doc.third_party_permission_notes and decision.third_party_permission_notes:
                        doc.third_party_permission_notes = decision.third_party_permission_notes
                else:
                    # Document has not been owner-reviewed; populate rights metadata from authoritative registry
                    doc.publication_status = decision.publication_status.value if hasattr(decision.publication_status, "value") else str(decision.publication_status)
                    doc.rights_evidence_url = decision.rights_evidence_url
                    doc.rights_reviewed_at = decision.rights_reviewed_at
                    doc.rights_reviewer = decision.rights_reviewer
                    doc.permissible_use = decision.permissible_use
                    doc.redistribution_allowed = decision.redistribution_allowed
                    doc.commercial_redistribution_allowed = decision.commercial_redistribution_allowed
                    doc.full_text_storage_allowed = decision.full_text_storage_allowed
                    doc.derived_summary_allowed = decision.derived_summary_allowed
                    doc.attribution_required = decision.attribution_required
                    doc.attribution_text = decision.attribution_text
                    doc.reuse_restrictions = decision.reuse_restrictions
                    doc.quarantine_reason = decision.quarantine_reason
                    tp_status = decision.third_party_permission_status
                    doc.third_party_permission_status = tp_status.value if hasattr(tp_status, "value") else str(tp_status)
                    doc.third_party_permission_notes = decision.third_party_permission_notes

                docs_updated += 1
            else:
                # Document does not exist in populated database; insert candidate document safely
                cancer_match = session.query(Cancer).filter(Cancer.slug == decision.canonical_cancer_slug).first()
                tp_status = decision.third_party_permission_status
                new_doc = SourceDocument(
                    id=f"doc-{uuid.uuid4().hex[:12]}",
                    source_id=decision.source_id,
                    title=decision.title,
                    original_url=decision.url,
                    canonical_url=decision.url,
                    canonical_cancer_id=cancer_match.id if cancer_match else None,
                    source_cancer_name=cancer_match.canonical_name if cancer_match else None,
                    country_code=decision.country_code,
                    jurisdiction_scope=decision.jurisdiction_scope,
                    content_hash=f"hash-{uuid.uuid4().hex[:16]}",
                    processing_status="PROCESSED",
                    language="en",
                    publication_status=decision.publication_status.value if hasattr(decision.publication_status, "value") else str(decision.publication_status),
                    rights_evidence_url=decision.rights_evidence_url,
                    rights_reviewed_at=decision.rights_reviewed_at,
                    rights_reviewer=decision.rights_reviewer,
                    permissible_use=decision.permissible_use,
                    redistribution_allowed=decision.redistribution_allowed,
                    commercial_redistribution_allowed=decision.commercial_redistribution_allowed,
                    full_text_storage_allowed=decision.full_text_storage_allowed,
                    derived_summary_allowed=decision.derived_summary_allowed,
                    attribution_required=decision.attribution_required,
                    attribution_text=decision.attribution_text,
                    reuse_restrictions=decision.reuse_restrictions,
                    quarantine_reason=decision.quarantine_reason,
                    third_party_permission_status=tp_status.value if hasattr(tp_status, "value") else str(tp_status),
                    third_party_permission_notes=decision.third_party_permission_notes,
                )
                session.add(new_doc)
                docs_created += 1

        session.flush()

        # Build url -> SourceDocument lookup for linkage
        url_to_doc = {
            d.original_url: d
            for d in session.query(SourceDocument).all()
        }

        # 2. Link consensus citations to SourceDocument without touching existing quotes or attribution
        all_citations = session.query(ConsensusFactSource).all()
        for citation in all_citations:
            if citation.source_document_id is not None:
                citations_already_linked += 1
                continue

            target_doc = url_to_doc.get(citation.source_url)
            if target_doc:
                citation.source_document_id = target_doc.id
                citations_linked += 1

        # 3. Verify citation linkage and postconditions BEFORE committing
        remaining_unlinked = [
            c for c in all_citations
            if c.source_document_id is None
        ]
        if remaining_unlinked:
            unlinked_urls = sorted({c.source_url for c in remaining_unlinked})
            raise TransitionError(
                f"Transition postcondition failed: {len(remaining_unlinked)} consensus citations remain unlinked to SourceDocument. "
                f"Unmatched URLs: {unlinked_urls}. Transition aborted."
            )

        # Verify candidate documents postcondition: candidate documents must have rights evidence
        for d in session.query(SourceDocument).all():
            if d.original_url in RIGHTS_INVENTORY:
                if not d.rights_evidence_url:
                    raise TransitionError(
                        f"Transition postcondition failed: candidate document '{d.original_url}' is missing rights_evidence_url."
                    )
                if not d.publication_status:
                    raise TransitionError(
                        f"Transition postcondition failed: candidate document '{d.original_url}' is missing publication_status."
                    )

        if dry_run:
            session.rollback()
            return {
                "status": "VALIDATED_NO_MUTATION",
                "mode": "DRY_RUN",
                "pre_total_documents": pre_total_docs,
                "pre_total_citations": pre_total_citations,
                "pre_unlinked_citations": unlinked_citations,
                "documents_to_update": docs_updated,
                "documents_to_create": docs_created,
                "citations_to_link": citations_linked,
                "citations_already_linked": citations_already_linked,
                "remaining_unlinked_citations": 0,
                "message": "Dry-run validation successful. No mutations applied.",
            }

        session.commit()

        post_total_docs = session.query(SourceDocument).count()
        post_total_citations = session.query(ConsensusFactSource).count()

        return {
            "status": "SUCCESS",
            "mode": "APPLY",
            "documents_updated": docs_updated,
            "documents_created": docs_created,
            "citations_linked": citations_linked,
            "citations_already_linked": citations_already_linked,
            "post_total_documents": post_total_docs,
            "post_total_citations": post_total_citations,
            "remaining_unlinked_citations": 0,
            "message": "Populated L003 database successfully transitioned to L004 in a single atomic transaction.",
        }

    except Exception as exc:
        session.rollback()
        raise TransitionError(f"Database transition failed and was rolled back: {exc}") from exc
    finally:
        session.close()
