"""
CIAPI-L004 Document Reuse Rights and Quarantine Resolution Test Suite

Tests:
1. Current seed inventory resolves all 32 distinct launch-candidate URLs.
2. Existing 20 normal source documents remain represented.
3. The 12 consensus-only URLs also obtain document-level records.
4. Every ContentSource used by the current seed resolves to a SourceDocument.
5. Every ConsensusFactSource resolves to a SourceDocument.
6. Consensus source URL, quote snippet and attribution are preserved.
7. Repeated citations to the same exact document do not create duplicate SourceDocument rows.
8. A new/unreviewed document is not publication eligible by default (fail-closed).
9. Source-level APPROVED does not automatically make a SourceDocument eligible.
10. Missing required evidence/reviewer information prevents an eligible decision.
11. WHO unresolved material remains non-eligible unless exact permission/license evidence exists.
12. Cancer Australia unresolved material remains non-eligible unless exact permission/license evidence exists.
13. CDC current item remains review-required unless exact item evidence exists.
14. Rights inventory includes consensus citation URLs, quotes and attribution.
15. Quarantine/publication decisions are machine-queryable for use by a future publication gate.
16. Document-level attribution/redistribution information maps into consumer provenance schema.
17. The new Alembic migration upgrades successfully from the L003 revision.
18. The L004 migration downgrade works for the L004 delta.
19. Existing L003 migration/bootstrap behavior remains intact.
20. Existing application tests continue to pass.
"""
from datetime import datetime
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.database.session import get_db

from app.core.constants import LicenseStatus, PublicationStatus, ThirdPartyPermissionStatus, TrustTier
from app.core.rights_validation import (
    PublicationEligibilityError,
    assert_publication_eligible,
    evaluate_publication_eligibility,
    verify_source_cannot_grant_eligibility,
)
from app.database.bootstrap import execute_bootstrap
from app.database.migration_check import get_alembic_config, get_current_revision, set_alembic_url_safe
from app.ingestion.rights_inventory import (
    DocumentRightsDecision,
    RIGHTS_INVENTORY,
    audit_candidate_acceptance,
    export_rights_audit_report,
    extract_candidate_urls_from_markdown,
    get_rights_inventory_entry,
    list_rights_inventory,
    record_owner_rights_review,
)
from app.ingestion.seed import seed_database
from app.main import app
from app.models import (
    Cancer,
    ConsensusFact,
    ConsensusFactSource,
    ContentRecord,
    ContentSource,
    Source,
    SourceDocument,
)


@pytest.fixture
def test_db_session(tmp_path):
    """Provides a fully migrated and bootstrapped test session."""
    db_file = tmp_path / "l004_test.db"
    db_url = f"sqlite:///{db_file}"
    cfg = get_alembic_config()
    set_alembic_url_safe(cfg, db_url)
    command.upgrade(cfg, "head")

    engine = create_engine(db_url)
    execute_bootstrap(engine, dry_run=False)

    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_inventory_resolves_all_32_distinct_candidate_urls():
    """Requirement 1: Current seed inventory resolves all 32 distinct launch-candidate URLs."""
    inventory_urls = set(RIGHTS_INVENTORY.keys())
    assert len(inventory_urls) == 32, f"Expected 32 distinct URLs, found {len(inventory_urls)}"

    # Check breakdown by source
    by_source = {}
    for d in list_rights_inventory():
        by_source.setdefault(d.source_id, []).append(d.url)

    assert len(by_source["nci-us"]) == 14
    assert len(by_source["nhs-uk"]) == 9
    assert len(by_source["who-global"]) == 4
    assert len(by_source["cancer-australia"]) == 4
    assert len(by_source["cdc-us"]) == 1
    assert sum(len(urls) for urls in by_source.values()) == 32


def test_seeded_database_has_32_source_documents(test_db_session):
    """Requirement 2 & 3: 20 normal content URLs and 12 consensus-only URLs are all represented in SourceDocument."""
    docs = test_db_session.query(SourceDocument).all()
    assert len(docs) == 32

    urls_in_db = {d.original_url for d in docs}
    assert urls_in_db == set(RIGHTS_INVENTORY.keys())

    # Check normal content URLs (20 distinct)
    cs_urls = {cs.source_url for cs in test_db_session.query(ContentSource).all()}
    assert len(cs_urls) == 20

    # Check consensus citation URLs (20 distinct)
    cfs_urls = {cfs.source_url for cfs in test_db_session.query(ConsensusFactSource).all()}
    assert len(cfs_urls) == 20

    # Check overlap (8) and consensus-only (12)
    overlap = cs_urls.intersection(cfs_urls)
    assert len(overlap) == 8

    consensus_only = cfs_urls - cs_urls
    assert len(consensus_only) == 12

    # Verify each consensus-only URL has a SourceDocument row
    for u in consensus_only:
        doc = test_db_session.query(SourceDocument).filter(SourceDocument.original_url == u).first()
        assert doc is not None, f"Consensus-only URL {u} lacks a SourceDocument!"


def test_all_content_and_consensus_sources_resolve_to_source_document(test_db_session):
    """Requirement 4 & 5: Every ContentSource and ConsensusFactSource links to an exact SourceDocument."""
    content_sources = test_db_session.query(ContentSource).all()
    assert len(content_sources) == 21
    for cs in content_sources:
        assert cs.source_document_id is not None
        assert cs.source_document is not None
        assert cs.source_document.original_url == cs.source_url

    consensus_sources = test_db_session.query(ConsensusFactSource).all()
    assert len(consensus_sources) == 48
    for cfs in consensus_sources:
        assert cfs.source_document_id is not None
        assert cfs.source_document is not None
        assert cfs.source_document.original_url == cfs.source_url


def test_consensus_citation_fields_preserved(test_db_session):
    """Requirement 6: Consensus citation metadata (quote snippet, attribution, URL, country) is preserved."""
    consensus_sources = test_db_session.query(ConsensusFactSource).all()
    for cfs in consensus_sources:
        assert cfs.source_url.startswith("https://")
        assert cfs.quote_snippet is not None and len(cfs.quote_snippet) > 0
        assert cfs.attribution_text is not None and len(cfs.attribution_text) > 0
        assert cfs.country_code in {"US", "GB", "AU", "GLOBAL"}


def test_repeated_citations_do_not_create_duplicate_documents(test_db_session):
    """Requirement 7: Repeated citations to the same exact document share a single SourceDocument row."""
    # "https://www.cancer.gov/types/breast/symptoms" is cited by 3 consensus facts and 1 normal record
    breast_sym_url = "https://www.cancer.gov/types/breast/symptoms"
    docs = test_db_session.query(SourceDocument).filter(SourceDocument.original_url == breast_sym_url).all()
    assert len(docs) == 1, f"Expected exactly 1 SourceDocument for {breast_sym_url}, found {len(docs)}"

    doc = docs[0]
    # Check that multiple consensus citations point to this exact document
    cfs_links = test_db_session.query(ConsensusFactSource).filter(
        ConsensusFactSource.source_document_id == doc.id
    ).all()
    assert len(cfs_links) == 3

    # Check that the normal content record also points to this exact document
    cs_links = test_db_session.query(ContentSource).filter(
        ContentSource.source_document_id == doc.id
    ).all()
    assert len(cs_links) == 1


def test_new_or_unreviewed_document_not_eligible_by_default():
    """Requirement 8: Newly discovered or unreviewed documents default fail-closed to non-eligible."""
    new_doc = SourceDocument(
        id="test-new-doc",
        source_id="nci-us",
        original_url="https://www.cancer.gov/types/new-cancer",
        title="New Cancer Overview",
        country_code="US",
        content_hash="abc123hash",
    )
    # Default is REVIEW_REQUIRED
    assert new_doc.publication_status == PublicationStatus.REVIEW_REQUIRED.value
    assert new_doc.is_publication_eligible() is False

    with pytest.raises(PublicationEligibilityError) as exc_info:
        new_doc.assert_publication_eligible()
    assert "NOT publication eligible" in str(exc_info.value)


def test_source_level_approved_does_not_clear_source_document():
    """Requirement 9: Parent Source being APPROVED, Tier 1, or active does NOT confer eligibility."""
    approved_source = Source(
        id="mock-gov",
        organization_name="Mock Government Health Org",
        source_name="Mock Health Info",
        base_url="https://mockhealth.gov",
        country_code="US",
        source_type="government_agency",
        trust_tier=TrustTier.TIER_1.value,
        authority_type="National Health Authority",
        license_type="Public Domain",
        license_status=LicenseStatus.APPROVED.value,
        active=True,
    )
    doc = SourceDocument(
        id="doc-001",
        source_id="mock-gov",
        original_url="https://mockhealth.gov/info",
        title="Mock Doc",
        country_code="US",
        content_hash="hash123",
        publication_status=PublicationStatus.REVIEW_REQUIRED.value,
    )
    is_eligible, reasons = evaluate_publication_eligibility(doc, source=approved_source)
    assert is_eligible is False
    assert any("must be 'ELIGIBLE'" in r for r in reasons)
    verify_source_cannot_grant_eligibility(doc, approved_source)


def test_missing_required_evidence_prevents_eligible_decision():
    """Requirement 10: Missing required evidence or reviewer fields prevents eligibility."""
    # Start with a doc marked ELIGIBLE but missing required review fields
    doc = SourceDocument(
        id="test-doc",
        source_id="nci-us",
        original_url="https://example.gov/page",
        title="Example",
        country_code="US",
        content_hash="hash",
        publication_status=PublicationStatus.ELIGIBLE.value,
        # Missing rights_evidence_url, rights_reviewed_at, rights_reviewer, etc.
    )
    is_eligible, reasons = evaluate_publication_eligibility(doc)
    assert is_eligible is False
    assert any("Missing required rights evidence URL" in r for r in reasons)
    assert any("Missing required rights review timestamp" in r for r in reasons)
    assert any("Missing required rights reviewer" in r for r in reasons)
    assert any("redistribution is not allowed" in r for r in reasons)

    # Supply evidence fields but keep quarantine reason
    doc.rights_evidence_url = "https://example.gov/policy"
    doc.rights_reviewed_at = datetime.utcnow()
    doc.rights_reviewer = "Reviewer Name"
    doc.permissible_use = "U.S. Federal Government public domain"
    doc.redistribution_allowed = True
    doc.commercial_redistribution_allowed = True
    doc.full_text_storage_allowed = True
    doc.derived_summary_allowed = True
    doc.attribution_required = False
    doc.quarantine_reason = "Pending third-party media clearance"
    assert doc.is_publication_eligible() is False

    # Clear quarantine reason -> now eligible
    doc.quarantine_reason = None
    doc.third_party_permission_status = "NOT_APPLICABLE"
    assert doc.is_publication_eligible() is True


def test_who_unresolved_material_is_quarantined_or_permission_pending(test_db_session):
    """Requirement 11: WHO documents remain non-publication-eligible due to commercial/API restriction."""
    who_docs = test_db_session.query(SourceDocument).filter(SourceDocument.source_id == "who-global").all()
    assert len(who_docs) == 4
    for doc in who_docs:
        assert doc.publication_status == PublicationStatus.PERMISSION_PENDING.value
        assert doc.is_publication_eligible() is False
        assert doc.commercial_redistribution_allowed is False
        assert "CC BY-NC-SA 3.0 IGO" in doc.quarantine_reason
        assert doc.third_party_permission_status == ThirdPartyPermissionStatus.REQUIRED_NOT_SUBMITTED.value
        assert "no request has yet been submitted" in doc.third_party_permission_notes.lower() or "not yet been submitted" in doc.third_party_permission_notes.lower()


def test_cancer_australia_unresolved_material_is_review_required(test_db_session):
    """Requirement 12: Cancer Australia documents remain non-publication-eligible awaiting item audit."""
    au_docs = test_db_session.query(SourceDocument).filter(SourceDocument.source_id == "cancer-australia").all()
    assert len(au_docs) == 4
    for doc in au_docs:
        assert doc.publication_status == PublicationStatus.REVIEW_REQUIRED.value
        assert doc.is_publication_eligible() is False
        assert doc.commercial_redistribution_allowed is False
        assert "Crown copyright" in doc.quarantine_reason or "CC BY 4.0" in doc.quarantine_reason


def test_cdc_current_item_is_review_required(test_db_session):
    """Requirement 13: CDC document remains non-publication-eligible awaiting third-party audit."""
    cdc_docs = test_db_session.query(SourceDocument).filter(SourceDocument.source_id == "cdc-us").all()
    assert len(cdc_docs) == 1
    doc = cdc_docs[0]
    assert doc.publication_status == PublicationStatus.REVIEW_REQUIRED.value
    assert doc.is_publication_eligible() is False
    assert doc.commercial_redistribution_allowed is False
    assert "third-party" in doc.quarantine_reason.lower()


def test_rights_inventory_includes_consensus_citations_and_quotes(test_db_session):
    """Requirement 14 & 15: Rights audit export includes consensus citations, quotes, and attributions."""
    report = export_rights_audit_report(test_db_session)
    assert len(report) == 32

    # Check a document with consensus citations
    breast_sym_entry = next(e for e in report if e["url"] == "https://www.cancer.gov/types/breast/symptoms")
    assert len(breast_sym_entry["linked_consensus_citations"]) == 3
    for cit in breast_sym_entry["linked_consensus_citations"]:
        assert "fact_key" in cit
        assert "quote_snippet" in cit
        assert len(cit["quote_snippet"]) > 0
        assert "attribution_text" in cit


def test_consumer_provenance_schema_mapping(test_db_session):
    """Requirement 16: Document-level attribution and rights metadata maps into API responses."""
    app.dependency_overrides[get_db] = lambda: test_db_session
    try:
        client = TestClient(app)
        response = client.get("/v1/cancers/breast-cancer/symptoms")
        assert response.status_code == 200
        data = response.json()["data"]

        # Verify consensus item corroborating source has document-level rights fields
        items = data.get("items")
        assert items and len(items) > 0
        first_item = items[0]
        corrob_sources = first_item.get("corroborated_by", [])
        assert len(corrob_sources) > 0
        first_corrob = corrob_sources[0]
        assert "document_title" in first_corrob
        assert "publication_status" in first_corrob
        assert "reuse_conditions" in first_corrob
        assert "commercial_redistribution_allowed" in first_corrob
        assert "rights_evidence_url" in first_corrob

        # Verify raw records provenance source has document-level rights fields
        records = data.get("records")
        assert records and len(records) > 0
        first_rec = records[0]
        sources = first_rec.get("sources", [])
        assert len(sources) > 0
        first_src = sources[0]
        assert "document_title" in first_src
        assert "publication_status" in first_src
        assert "reuse_conditions" in first_src
        assert "commercial_redistribution_allowed" in first_src
        assert "rights_evidence_url" in first_src
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_l004_migration_upgrade_and_downgrade(tmp_path):
    """Requirement 17 & 18: Alembic migration upgrades from L003 and downgrades cleanly for L004 delta."""
    db_file = tmp_path / "migration_delta.db"
    db_url = f"sqlite:///{db_file}"
    cfg = get_alembic_config()
    set_alembic_url_safe(cfg, db_url)

    # 1. Upgrade to L003 initial schema
    command.upgrade(cfg, "0001_initial_schema")
    engine = create_engine(db_url)
    assert get_current_revision(engine) == "0001_initial_schema"

    # Insert baseline L003 SourceDocument using raw SQL (pre-L004 schema)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO sources (id, organization_name, source_name, base_url, country_code, "
            "source_type, trust_tier, authority_type, license_type, license_status, active) "
            "VALUES ('test-src', 'Test Org', 'Test', 'https://example.org', 'US', 'government', "
            "'Tier 1', 'Authority', 'Public Domain', 'APPROVED', 1)"
        ))
        conn.execute(text(
            "INSERT INTO source_documents (id, source_id, original_url, title, language, "
            "country_code, jurisdiction_scope, retrieved_at, last_verified_at, content_hash, "
            "parser_version, processing_status, license_status) "
            "VALUES ('doc-pre-l004', 'test-src', 'https://example.org/test', 'Pre-L004 Doc', "
            "'en', 'US', 'COUNTRY', '2026-09-27 00:00:00', '2026-09-27 00:00:00', 'pre_hash', "
            "'1.0.0', 'PROCESSED', 'REVIEW_REQUIRED')"
        ))
        conn.commit()

    # 2. Upgrade to L004 head (0002_document_rights)
    command.upgrade(cfg, "head")
    assert get_current_revision(engine) == "0002_document_rights"

    # Verify existing document received fail-closed server_default 'REVIEW_REQUIRED'
    with sessionmaker(bind=engine)() as s:
        migrated_doc = s.query(SourceDocument).filter_by(id="doc-pre-l004").one()
        assert migrated_doc.publication_status == "REVIEW_REQUIRED"
        assert migrated_doc.is_publication_eligible() is False

    # 3. Downgrade back to L003
    command.downgrade(cfg, "0001_initial_schema")
    assert get_current_revision(engine) == "0001_initial_schema"

    # Verify L004 columns were removed
    inspector = inspect(engine)
    sd_cols = {c["name"] for c in inspector.get_columns("source_documents")}
    assert "publication_status" not in sd_cols
    assert "rights_evidence_url" not in sd_cols
    cfs_cols = {c["name"] for c in inspector.get_columns("consensus_fact_sources")}
    assert "source_document_id" not in cfs_cols

    # 4. Re-upgrade to head
    command.upgrade(cfg, "head")
    assert get_current_revision(engine) == "0002_document_rights"
    inspector = inspect(engine)
    sd_cols = {c["name"] for c in inspector.get_columns("source_documents")}
    assert "publication_status" in sd_cols
    engine.dispose()


def test_documented_candidate_urls_match_registry_and_seed(test_db_session):
    """
    Mithra acceptance correction: Handoff and candidate report URL sets
    must not diverge from the registry or seeded candidate set.
    Asserts: set(documented_candidate_urls) == set(RIGHTS_INVENTORY.keys()) == set(seed_candidate_urls)
    """
    inv_urls = set(RIGHTS_INVENTORY.keys())
    seed_urls = {d.original_url for d in test_db_session.query(SourceDocument).all()}

    with open("docs/HANDOFF_TO_MITHRA.md") as f:
        handoff_urls = extract_candidate_urls_from_markdown(f.read())

    with open("candidate_report_CIAPI-L004.md") as f:
        report_urls = extract_candidate_urls_from_markdown(f.read())

    assert len(inv_urls) == 32
    assert len(seed_urls) == 32
    assert len(handoff_urls) == 32
    assert len(report_urls) == 32

    assert handoff_urls == inv_urls
    assert report_urls == inv_urls
    assert seed_urls == inv_urls


def test_acceptance_validation_reports_missing_owner_review_as_blocker(test_db_session):
    """
    Mithra acceptance correction: Acceptance validation must truthfully report
    missing rights_reviewed_at and rights_reviewer as OPEN blockers.
    """
    report = audit_candidate_acceptance(db=test_db_session)

    assert report["total_candidate_documents"] == 32
    assert report["with_rights_evidence"] == 32
    assert report["with_permissible_use"] == 32
    assert report["with_attribution_decision"] == 32
    assert report["with_publication_decision"] == 32

    # Truthful check: Owner review has NOT yet occurred
    assert report["with_review_date"] == 0
    assert report["with_decision_owner"] == 0
    assert report["owner_review_completed"] is False
    assert report["l004_acceptance_satisfied"] is False

    # Blockers must be explicitly reported
    assert len(report["blockers"]) >= 2
    assert any("missing formal owner review timestamp" in b.lower() for b in report["blockers"])
    assert any("missing formal owner decision reviewer" in b.lower() for b in report["blockers"])
    assert any("who candidate documents" in b.lower() for b in report["blockers"])

    assert len(report["documents_missing_review_date"]) == 32
    assert len(report["documents_missing_decision_owner"]) == 32


def test_third_party_permission_state_distinguishes_not_requested_from_submitted():
    """
    Mithra acceptance correction: Third-party permission state must distinguish
    'not requested' (REQUIRED_NOT_SUBMITTED) from 'submitted and awaiting response'.
    """
    doc = SourceDocument(
        id="test-doc-tp",
        source_id="who-global",
        original_url="https://example.org/who",
        title="WHO Test",
        country_code="GLOBAL",
        content_hash="hash",
        publication_status=PublicationStatus.PERMISSION_PENDING.value,
        rights_evidence_url="https://example.org/rights",
        rights_reviewed_at=datetime.utcnow(),
        rights_reviewer="Auditor",
        permissible_use="WHO Open Access Policy",
        redistribution_allowed=True,
        commercial_redistribution_allowed=True,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=False,
        third_party_permission_status=ThirdPartyPermissionStatus.REQUIRED_NOT_SUBMITTED.value,
    )
    is_eligible, reasons = evaluate_publication_eligibility(doc)
    assert is_eligible is False
    assert any("REQUIRED_NOT_SUBMITTED" in r for r in reasons)

    # Change to REQUESTED_AWAITING_RESPONSE -> still not eligible while response pending
    doc.third_party_permission_status = ThirdPartyPermissionStatus.REQUESTED_AWAITING_RESPONSE.value
    is_eligible, reasons = evaluate_publication_eligibility(doc)
    assert is_eligible is False
    assert any("REQUESTED_AWAITING_RESPONSE" in r for r in reasons)

    # Change to GRANTED without supporting notes -> not eligible (requires supporting evidence)
    doc.third_party_permission_status = ThirdPartyPermissionStatus.GRANTED.value
    doc.publication_status = PublicationStatus.ELIGIBLE.value
    doc.third_party_permission_notes = None
    is_eligible, reasons = evaluate_publication_eligibility(doc)
    assert is_eligible is False
    assert any("third-party permission is GRANTED but supporting evidence" in r for r in reasons)

    # Supply supporting evidence reference -> now eligible
    doc.third_party_permission_notes = "WHO Permission Committee written waiver ref #WHO-2026-001"
    is_eligible, reasons = evaluate_publication_eligibility(doc)
    assert is_eligible is True


def test_owner_review_workflow_truthful_recording(test_db_session):
    """
    Verifies that the owner review workflow API record_owner_rights_review
    truthfully records review date and reviewer without fabricating data.
    """
    with pytest.raises(ValueError):
        record_owner_rights_review(
            "https://www.cancer.gov/types/breast",
            reviewer="",
            db=test_db_session,
        )

    res = record_owner_rights_review(
        "https://www.cancer.gov/types/breast",
        reviewer="Jaya Prakash Merepala",
        reviewed_at=datetime.utcnow(),
        db=test_db_session,
    )
    assert res["status"] == "RECORDED"
    assert res["rights_reviewer"] == "Jaya Prakash Merepala"

    # Verify updated in database
    doc = test_db_session.query(SourceDocument).filter_by(
        original_url="https://www.cancer.gov/types/breast"
    ).one()
    assert doc.rights_reviewer == "Jaya Prakash Merepala"
    assert doc.rights_reviewed_at is not None


def test_consolidated_publication_eligibility_rejects_unknown_missing_and_inconsistent():
    """
    Issue 3 & 4: Proves publication eligibility rejects unknown or missing third-party decisions,
    missing permissible-use evidence, missing storage/derivative/attribution decisions,
    and inconsistent evidence fail-closed.
    """
    doc = SourceDocument(
        id="test-doc-audit",
        source_id="nci-us",
        original_url="https://example.gov/doc",
        title="Test Doc",
        country_code="US",
        content_hash="hash",
        publication_status=PublicationStatus.ELIGIBLE.value,
        rights_evidence_url="https://example.gov/rights",
        rights_reviewed_at=datetime.utcnow(),
        rights_reviewer="Reviewer",
        permissible_use="U.S. Federal Government work in public domain",
        redistribution_allowed=True,
        commercial_redistribution_allowed=True,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=False,
        third_party_permission_status=ThirdPartyPermissionStatus.NOT_APPLICABLE.value,
    )
    # Valid baseline
    assert doc.is_publication_eligible() is True

    # 1. Missing third party decision
    doc.third_party_permission_status = None
    assert doc.is_publication_eligible() is False
    doc.third_party_permission_status = ""
    assert doc.is_publication_eligible() is False

    # 2. Unknown third party decision
    doc.third_party_permission_status = "UNKNOWN_CUSTOM_DECISION"
    assert doc.is_publication_eligible() is False

    # 3. Inconsistent evidence: commercial allowed while general redistribution disallowed
    doc.third_party_permission_status = "NOT_APPLICABLE"
    doc.redistribution_allowed = False
    doc.commercial_redistribution_allowed = True
    assert doc.is_publication_eligible() is False

    # 4. Inconsistent evidence: ELIGIBLE with quarantine reason
    doc.redistribution_allowed = True
    doc.commercial_redistribution_allowed = True
    doc.quarantine_reason = "Quarantined for audit"
    assert doc.is_publication_eligible() is False
    doc.quarantine_reason = None

    # 5. Invalid evidence URL (not http/https)
    doc.rights_evidence_url = "ftp://invalid-scheme.gov/rights"
    assert doc.is_publication_eligible() is False
    doc.rights_evidence_url = "https://example.gov/rights"

    # 6. Missing permissible_use evidence
    doc.permissible_use = ""
    assert doc.is_publication_eligible() is False
    doc.permissible_use = None
    assert doc.is_publication_eligible() is False
    doc.permissible_use = "U.S. Federal Government public domain"
    assert doc.is_publication_eligible() is True

    # 7. Explicit storage decision required
    doc.full_text_storage_allowed = None
    assert doc.is_publication_eligible() is False
    doc.full_text_storage_allowed = False
    assert doc.is_publication_eligible() is False
    doc.full_text_storage_allowed = True
    assert doc.is_publication_eligible() is True

    # 8. Explicit derivative summary decision required
    doc.derived_summary_allowed = None
    assert doc.is_publication_eligible() is False
    doc.derived_summary_allowed = False
    assert doc.is_publication_eligible() is False
    doc.derived_summary_allowed = True
    assert doc.is_publication_eligible() is True

    # 9. Explicit attribution decision and consistency
    doc.attribution_required = None
    assert doc.is_publication_eligible() is False
    doc.attribution_required = True
    doc.attribution_text = ""
    assert doc.is_publication_eligible() is False
    doc.attribution_text = "Source: NCI"
    assert doc.is_publication_eligible() is True

    # 10. Supporting evidence for GRANTED third-party permission
    doc.third_party_permission_status = "GRANTED"
    doc.third_party_permission_notes = None
    assert doc.is_publication_eligible() is False
    doc.third_party_permission_notes = "License agreement #2026-NCI"
    assert doc.is_publication_eligible() is True


def test_audit_candidate_acceptance_submitted_permissions_do_not_produce_acceptance():
    """
    Issue 4: Submitted-but-unresolved permissions must not produce false acceptance.
    Distinguishes owner-approved eligible corpus from unresolved decisions.
    """
    report = audit_candidate_acceptance()
    assert report["total_candidate_documents"] == 32
    assert report["owner_approved_eligible_corpus_count"] == 0
    assert report["unresolved_candidate_decisions_count"] == 28
    assert report["unresolved_permission_decisions_count"] == 4
    assert report["l004_acceptance_satisfied"] is False
    assert any("REQUIRED_NOT_SUBMITTED" in b for b in report["blockers"])

    # Simulate submitting WHO permissions (REQUESTED_AWAITING_RESPONSE)
    simulated_docs = []
    for d in list_rights_inventory():
        d_dict = d.to_dict()
        if d_dict["third_party_permission_status"] == "REQUIRED_NOT_SUBMITTED":
            d_dict["third_party_permission_status"] = "REQUESTED_AWAITING_RESPONSE"
        # Simulate populated review dates and reviewers
        d_dict["rights_reviewed_at"] = datetime.utcnow()
        d_dict["rights_reviewer"] = "Jaya Prakash Merepala"
        simulated_docs.append(DocumentRightsDecision(**d_dict))

    sim_report = audit_candidate_acceptance(records=simulated_docs)
    assert sim_report["permission_requests_submitted"] == 4
    assert sim_report["permission_required_not_submitted"] == 0
    # Must STILL be rejected with open blocker!
    assert sim_report["l004_acceptance_satisfied"] is False
    assert any("REQUESTED_AWAITING_RESPONSE" in b for b in sim_report["blockers"])


def test_owner_review_records_durable_and_auditable(test_db_session):
    """
    Issue 5: Make owner review records durable and auditable.
    Reject unknown targets, document transaction persistence, and support exact references.
    """
    # 1. Reject unknown target
    with pytest.raises(ValueError, match="Unknown target document URL"):
        record_owner_rights_review(
            "https://random-unknown-domain.org/nonexistent",
            reviewer="Prakash",
            db=test_db_session,
        )

    # 2. Reject invalid rights evidence URL
    with pytest.raises(ValueError, match="Invalid rights evidence URL"):
        record_owner_rights_review(
            "https://www.cancer.gov/types/breast",
            reviewer="Prakash",
            rights_evidence_url="not-a-valid-url",
            db=test_db_session,
        )

    # 3. Test in-memory only (without db) reports transient status
    res_mem = record_owner_rights_review(
        "https://www.cancer.gov/types/breast",
        reviewer="Prakash",
        db=None,
    )
    assert res_mem["persisted_to_database"] is False
    assert res_mem["persistence_status"] == "TRANSIENT_MEMORY_ONLY"
    assert "Review recorded in-memory only" in res_mem["persistence_warning"]

    # 4. Test database transaction persistence with exact permission reference
    res_db = record_owner_rights_review(
        "https://www.cancer.gov/types/breast",
        reviewer="Jaya Prakash Merepala",
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        permission_reference="NCI-REUSE-AUDIT-2026-001",
        third_party_permission_notes="Verified no external illustrations",
        db=test_db_session,
        commit=True,
    )
    assert res_db["persisted_to_database"] is True
    assert res_db["persistence_status"] == "COMMITTED_TO_DATABASE"
    assert res_db["permission_reference"] == "NCI-REUSE-AUDIT-2026-001"

    # Verify db record has combined permission reference notes
    db_doc = test_db_session.query(SourceDocument).filter_by(
        original_url="https://www.cancer.gov/types/breast"
    ).one()
    assert "NCI-REUSE-AUDIT-2026-001" in db_doc.third_party_permission_notes


def test_populated_l003_database_upgrade_and_transition(tmp_path):
    """
    Issue 2: Controlled, transactional, repeat-safe transition for populated L003 databases.
    Populates document rights records and consensus citation links without reseeding or overwriting
    existing quotes, attribution, history or content. Tests populated upgrades.
    """
    from alembic import command
    from app.database.migration_check import get_alembic_config, get_current_revision
    from app.database.transition import transition_populated_l003_database
    from app.models import Cancer, ConsensusFact, ConsensusFactSource, ContentRecord, Source, SourceDocument

    db_path = tmp_path / "populated_l003.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)

    cfg = get_alembic_config()
    cfg.set_main_option("sqlalchemy.url", db_url)

    # 1. Upgrade to L003 schema (0001_initial_schema)
    command.upgrade(cfg, "0001_initial_schema")
    assert get_current_revision(engine) == "0001_initial_schema"

    # 2. Populate realistic L003 data using raw SQL (pre-L004 schema)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO sources (id, organization_name, source_name, base_url, country_code, "
            "source_type, trust_tier, authority_type, license_type, license_status, active) "
            "VALUES ('nci-us', 'National Cancer Institute', 'NCI', 'https://www.cancer.gov', 'US', 'government', "
            "'Tier 1 - Primary Authoritative', 'GOVERNMENT', 'U.S. Public Domain', 'APPROVED', 1)"
        ))
        conn.execute(text(
            "INSERT INTO cancers (id, canonical_name, slug) VALUES ('cancer-breast', 'Breast Cancer', 'breast-cancer')"
        ))
        conn.execute(text(
            "INSERT INTO source_documents (id, source_id, original_url, title, language, country_code, "
            "jurisdiction_scope, content_hash, processing_status, canonical_cancer_id) "
            "VALUES ('doc-existing-l003', 'nci-us', 'https://www.cancer.gov/types/breast', "
            "'Breast Cancer Overview - NCI', 'en', 'US', 'COUNTRY', 'sha256-original-content-l003', "
            "'PROCESSED', 'cancer-breast')"
        ))
        conn.execute(text(
            "INSERT INTO content_records (id, canonical_cancer_id, category, content) "
            "VALUES ('cr-existing-l003', 'cancer-breast', 'symptoms', "
            "'Original raw clinical text that must remain intact.')"
        ))
        conn.execute(text(
            "INSERT INTO consensus_facts (id, cancer_id, category, fact_key, title, clinical_detail, active) "
            "VALUES ('fact-breast-1', 'cancer-breast', 'symptoms', 'lump_in_breast', 'Lump in breast', "
            "'New lump in the breast or underarm is a primary symptom.', 1)"
        ))
        conn.execute(text(
            "INSERT INTO consensus_fact_sources (id, consensus_fact_id, source_id, country_code, "
            "quote_snippet, attribution_text, source_url) "
            "VALUES ('cfs-breast-1', 'fact-breast-1', 'nci-us', 'US', "
            "'Lump or swelling in the breast or armpit.', 'Quoted from NCI Breast Cancer page 2026.', "
            "'https://www.cancer.gov/types/breast')"
        ))
        conn.commit()

    # 3. Upgrade schema to L004 (0002_document_rights)
    command.upgrade(cfg, "head")
    assert get_current_revision(engine) == "0002_document_rights"

    # Verify consensus citation source_document_id is currently null
    with sessionmaker(bind=engine)() as s:
        cfs_check = s.query(ConsensusFactSource).filter_by(id="cfs-breast-1").one()
        assert cfs_check.source_document_id is None

    # 4. Execute transition in DRY-RUN mode
    dry_result = transition_populated_l003_database(engine, dry_run=True)
    assert dry_result["status"] == "VALIDATED_NO_MUTATION"
    assert dry_result["mode"] == "DRY_RUN"
    assert dry_result["citations_to_link"] == 1
    # Verify no mutation was applied in dry run
    with sessionmaker(bind=engine)() as s:
        cfs_check = s.query(ConsensusFactSource).filter_by(id="cfs-breast-1").one()
        assert cfs_check.source_document_id is None

    # 5. Apply transition in single transaction
    apply_result = transition_populated_l003_database(engine, dry_run=False)
    assert apply_result["status"] == "SUCCESS"
    assert apply_result["mode"] == "APPLY"
    assert apply_result["citations_linked"] == 1

    # 6. Verify data integrity and preservation
    with sessionmaker(bind=engine)() as s:
        doc_check = s.query(SourceDocument).filter_by(original_url="https://www.cancer.gov/types/breast").one()
        # Rights fields populated
        assert doc_check.rights_evidence_url == "https://www.cancer.gov/policies/copyright-reuse"
        assert doc_check.publication_status == "REVIEW_REQUIRED"
        # Original content and quote strictly preserved
        assert doc_check.content_hash == "sha256-original-content-l003"

        cfs_check = s.query(ConsensusFactSource).filter_by(id="cfs-breast-1").one()
        assert cfs_check.source_document_id == doc_check.id
        assert cfs_check.quote_snippet == "Lump or swelling in the breast or armpit."
        assert cfs_check.attribution_text == "Quoted from NCI Breast Cancer page 2026."

        cr_check = s.query(ContentRecord).filter_by(id="cr-existing-l003").one()
        assert cr_check.content == "Original raw clinical text that must remain intact."

    # 7. Repeat-safe execution (idempotency test)
    repeat_result = transition_populated_l003_database(engine, dry_run=False)
    assert repeat_result["status"] == "SUCCESS"
    assert repeat_result["citations_linked"] == 0
    assert repeat_result["citations_already_linked"] == 1
    engine.dispose()


def test_populated_transition_preserves_owner_reviews_and_permission_references(tmp_path):
    """
    Issue 3: Populated transition must preserve existing owner reviews, evidence,
    attribution, and permission references across restarts and repeated executions.
    """
    from alembic import command
    from app.database.migration_check import get_alembic_config
    from app.database.transition import transition_populated_l003_database

    db_path = tmp_path / "preserve_reviews.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    cfg = get_alembic_config()
    cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(cfg, "head")

    # Initial transition
    res1 = transition_populated_l003_database(engine, dry_run=False)
    assert res1["status"] == "SUCCESS"

    # Now record an owner review with specific reviewer, timestamp, and permission reference
    review_dt = datetime(2026, 9, 27, 12, 0, 0)
    with sessionmaker(bind=engine)() as s:
        record_owner_rights_review(
            url="https://www.cancer.gov/types/breast",
            reviewer="Jaya Prakash Merepala",
            reviewed_at=review_dt,
            publication_status=PublicationStatus.ELIGIBLE,
            rights_evidence_url="https://www.cancer.gov/policies/custom-evidence",
            permissible_use="U.S. Federal Government text verified clear",
            commercial_redistribution_allowed=True,
            redistribution_allowed=True,
            quarantine_reason=None,
            third_party_permission_status=ThirdPartyPermissionStatus.NOT_APPLICABLE,
            permission_reference="AUDIT-TICKET-2026-NCI",
            db=s,
            commit=True,
        )

    # Re-run transition (simulating process restart and repeat run)
    res2 = transition_populated_l003_database(engine, dry_run=False)
    assert res2["status"] == "SUCCESS"

    # Verify that the owner review fields were NOT overwritten by RIGHTS_INVENTORY unreviewed defaults
    with sessionmaker(bind=engine)() as s:
        doc = s.query(SourceDocument).filter_by(original_url="https://www.cancer.gov/types/breast").one()
        assert doc.rights_reviewer == "Jaya Prakash Merepala"
        assert doc.rights_reviewed_at == review_dt
        assert doc.publication_status == "ELIGIBLE"
        assert doc.rights_evidence_url == "https://www.cancer.gov/policies/custom-evidence"
        assert doc.permissible_use == "U.S. Federal Government text verified clear"
        assert "AUDIT-TICKET-2026-NCI" in (doc.third_party_permission_notes or "")

    engine.dispose()


def test_transition_fails_and_rolls_back_on_unresolved_links(tmp_path):
    """
    Issue 3: Verify citation linkage postconditions before commit;
    do not report SUCCESS with unresolved links. Roll back atomically on failure.
    """
    from alembic import command
    from app.database.migration_check import get_alembic_config
    from app.database.transition import TransitionError, transition_populated_l003_database

    db_path = tmp_path / "rollback_unresolved.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    cfg = get_alembic_config()
    cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(cfg, "head")

    # Populate Source and Cancer
    with sessionmaker(bind=engine)() as s:
        src = Source(
            id="src-test",
            organization_name="Test Org",
            source_name="Test",
            base_url="https://example.org",
            country_code="US",
            source_type="government",
            trust_tier="Tier 1",
            authority_type="GOVERNMENT",
            license_type="Public Domain",
            license_status="APPROVED",
        )
        s.add(src)
        cancer = Cancer(id="cancer-test", canonical_name="Test Cancer", slug="test-cancer")
        s.add(cancer)
        fact = ConsensusFact(
            id="fact-orphan-1",
            cancer_id="cancer-test",
            category="symptoms",
            fact_key="orphan_key",
            title="Orphan Fact",
            clinical_detail="Clinical detail",
            active=True,
        )
        s.add(fact)
        # Add consensus citation pointing to an unknown source_url not in candidate SourceDocuments
        orphan_cfs = ConsensusFactSource(
            id="cfs-orphan-1",
            consensus_fact_id="fact-orphan-1",
            source_id="src-test",
            country_code="US",
            quote_snippet="Unlinked quote snippet",
            attribution_text="Unlinked attribution",
            source_url="https://completely-unmatched-external-source.org/fact",
        )
        s.add(orphan_cfs)
        s.commit()

    # Attempt transition: must fail postcondition because orphan_cfs cannot be linked
    with pytest.raises(TransitionError) as exc_info:
        transition_populated_l003_database(engine, dry_run=False)

    assert "postcondition failed" in str(exc_info.value).lower()
    assert "remain unlinked" in str(exc_info.value).lower()

    # Verify session was rolled back and no candidate docs were committed
    with sessionmaker(bind=engine)() as s:
        orphan_check = s.query(ConsensusFactSource).filter_by(id="cfs-orphan-1").one()
        assert orphan_check.source_document_id is None

    engine.dispose()


def test_transition_enforces_supported_schema_revision(tmp_path):
    """
    Issue 3: Transition must strictly enforce the supported schema revision (0002_document_rights).
    Fails fast if database is at 0001_initial_schema or unmigrated.
    """
    from alembic import command
    from app.database.migration_check import get_alembic_config
    from app.database.transition import TransitionError, inspect_transition_readiness, transition_populated_l003_database

    db_path = tmp_path / "schema_check.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    cfg = get_alembic_config()
    cfg.set_main_option("sqlalchemy.url", db_url)

    # 1. At 0001_initial_schema (outdated revision)
    command.upgrade(cfg, "0001_initial_schema")

    with pytest.raises(TransitionError) as exc_info:
        inspect_transition_readiness(engine)
    assert "not at supported head revision" in str(exc_info.value)

    with pytest.raises(TransitionError) as exc_info:
        transition_populated_l003_database(engine, dry_run=False)
    assert "not at supported head revision" in str(exc_info.value)

    engine.dispose()


def test_acceptance_evaluation_rejects_inconsistent_eligible_and_requires_owner_corpus_decision(test_db_session):
    """
    Issue 3: Replace the invented two-document acceptance threshold with an explicit
    owner-approved corpus decision. Until Prakash supplies that decision, report it as pending.
    Do not claim cross-source approval based only on document count.
    """
    # 1. Baseline unreviewed audit: reports pending owner corpus decision
    report = audit_candidate_acceptance(db=test_db_session)
    assert report["l004_acceptance_satisfied"] is False
    assert report["owner_corpus_decision"] == "PENDING"
    assert report["owner_corpus_approved"] is False
    assert len(report["unresolved_candidate_decisions"]) == 28
    assert len(report["unresolved_permission_decisions"]) == 4
    assert len(report["owner_approved_eligible_corpus"]) == 0
    assert any("Owner-approved corpus decision is pending" in b for b in report["blockers"])

    # 2. Inconsistent ELIGIBLE record (marked ELIGIBLE but missing required review fields)
    doc = test_db_session.query(SourceDocument).filter_by(
        original_url="https://www.cancer.gov/types/breast"
    ).one()
    doc.publication_status = "ELIGIBLE"
    # Do not set rights_reviewed_at or rights_reviewer -> inconsistent!
    test_db_session.flush()

    report_inconsistent = audit_candidate_acceptance(db=test_db_session)
    assert "https://www.cancer.gov/types/breast" in report_inconsistent["inconsistent_eligible_records"]
    assert report_inconsistent["l004_acceptance_satisfied"] is False
    assert any("inconsistent" in b.lower() or "fail publication eligibility" in b.lower() for b in report_inconsistent["blockers"])

    # 3. Documents marked eligible without explicit owner corpus decision remain pending and cannot claim acceptance
    record_owner_rights_review(
        url="https://www.cancer.gov/types/breast",
        reviewer="Jaya Prakash Merepala",
        reviewed_at=datetime.utcnow(),
        publication_status=PublicationStatus.ELIGIBLE,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        permissible_use="U.S. Public Domain",
        commercial_redistribution_allowed=True,
        redistribution_allowed=True,
        quarantine_reason=None,
        third_party_permission_status=ThirdPartyPermissionStatus.NOT_APPLICABLE,
        db=test_db_session,
        commit=True,
    )
    doc.full_text_storage_allowed = True
    doc.derived_summary_allowed = True
    doc.attribution_required = False
    test_db_session.commit()

    report_pending_corpus = audit_candidate_acceptance(db=test_db_session)
    assert len(report_pending_corpus["owner_approved_eligible_corpus"]) == 1
    assert report_pending_corpus["owner_corpus_decision"] == "PENDING"
    assert report_pending_corpus["l004_acceptance_satisfied"] is False
    assert any("Owner-approved corpus decision is pending" in b for b in report_pending_corpus["blockers"])

    # 4. Even multiple eligible documents cannot claim cross-source approval based only on document count
    record_owner_rights_review(
        url="https://www.cancer.gov/types/breast/screening",
        reviewer="Jaya Prakash Merepala",
        reviewed_at=datetime.utcnow(),
        publication_status=PublicationStatus.ELIGIBLE,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        permissible_use="U.S. Public Domain",
        commercial_redistribution_allowed=True,
        redistribution_allowed=True,
        quarantine_reason=None,
        third_party_permission_status=ThirdPartyPermissionStatus.NOT_APPLICABLE,
        db=test_db_session,
        commit=True,
    )
    doc2 = test_db_session.query(SourceDocument).filter_by(
        original_url="https://www.cancer.gov/types/breast/screening"
    ).one()
    doc2.full_text_storage_allowed = True
    doc2.derived_summary_allowed = True
    doc2.attribution_required = False
    test_db_session.commit()

    report_two_docs = audit_candidate_acceptance(db=test_db_session)
    assert len(report_two_docs["owner_approved_eligible_corpus"]) == 2
    # Document count of 2 does NOT automatically grant acceptance; owner corpus decision is still pending!
    assert report_two_docs["owner_corpus_decision"] == "PENDING"
    assert report_two_docs["l004_acceptance_satisfied"] is False
    assert any("Owner-approved corpus decision is pending" in b for b in report_two_docs["blockers"])


def test_populated_postgresql_transition():
    """
    Issue 1: Focused regression coverage for populated transition on PostgreSQL.
    Corrects fixture so every source referenced by inserted documents exists in sources,
    with full foreign-key enforcement retained.
    Runs whenever POSTGRES_TEST_URL is provided (as in GitHub Actions CI).
    """
    import os
    if not os.getenv("POSTGRES_TEST_URL"):
        pytest.skip("POSTGRES_TEST_URL not set; skipping live PostgreSQL transition test")

    from tests.db_support import disposable_postgres
    from alembic import command
    from app.database.migration_check import get_alembic_config, set_alembic_url_safe
    from app.database.transition import transition_populated_l003_database

    with disposable_postgres(os.environ["POSTGRES_TEST_URL"]) as pg_url:
        pg_engine = create_engine(pg_url)
        cfg = get_alembic_config()
        set_alembic_url_safe(cfg, pg_url)

        # 1. Upgrade to L003 schema
        command.upgrade(cfg, "0001_initial_schema")

        # 2. Populate L003 data via raw SQL
        with pg_engine.connect() as conn:
            # Insert all 5 authoritative sources so every candidate document in RIGHTS_INVENTORY
            # has its referenced source present, retaining full foreign-key enforcement
            conn.execute(text(
                "INSERT INTO sources (id, organization_name, source_name, base_url, country_code, "
                "source_type, trust_tier, authority_type, license_type, license_status, active) "
                "VALUES "
                "('nci-us', 'National Cancer Institute', 'NCI', 'https://www.cancer.gov', 'US', 'government', 'Tier 1', 'GOVERNMENT', 'Public Domain', 'APPROVED', true), "
                "('cdc-us', 'Centers for Disease Control and Prevention', 'CDC', 'https://www.cdc.gov', 'US', 'government', 'Tier 1', 'GOVERNMENT', 'Public Domain', 'APPROVED', true), "
                "('who-global', 'World Health Organization', 'WHO', 'https://www.who.int', 'INT', 'international', 'Tier 1', 'INTERGOVERNMENTAL', 'CC BY-NC-SA 3.0 IGO', 'APPROVED', true), "
                "('nhs-uk', 'National Health Service', 'NHS', 'https://www.nhs.uk', 'GB', 'government', 'Tier 1', 'GOVERNMENT', 'Open Government Licence v3.0', 'APPROVED', true), "
                "('cancer-australia', 'Cancer Australia', 'Cancer Australia', 'https://www.canceraustralia.gov.au', 'AU', 'government', 'Tier 1', 'GOVERNMENT', 'CC BY 4.0', 'APPROVED', true)"
            ))
            # Insert canonical cancers referenced by candidate documents
            conn.execute(text(
                "INSERT INTO cancers (id, canonical_name, slug) VALUES "
                "('cancer-breast', 'Breast Cancer', 'breast-cancer'), "
                "('cancer-cervical', 'Cervical Cancer', 'cervical-cancer'), "
                "('cancer-colorectal', 'Colorectal Cancer', 'colorectal-cancer'), "
                "('cancer-lung', 'Lung Cancer', 'lung-cancer'), "
                "('cancer-melanoma', 'Melanoma Skin Cancer', 'melanoma-skin-cancer'), "
                "('cancer-pancreatic', 'Pancreatic Cancer', 'pancreatic-cancer'), "
                "('cancer-prostate', 'Prostate Cancer', 'prostate-cancer')"
            ))
            # Insert existing populated L003 document with foreign key to nci-us and cancer-breast
            conn.execute(text(
                "INSERT INTO source_documents (id, source_id, original_url, title, language, country_code, "
                "jurisdiction_scope, content_hash, processing_status, canonical_cancer_id) "
                "VALUES ('doc-pg-1', 'nci-us', 'https://www.cancer.gov/types/breast', "
                "'Breast Cancer', 'en', 'US', 'COUNTRY', 'sha-hash-1', 'PROCESSED', 'cancer-breast')"
            ))
            conn.execute(text(
                "INSERT INTO consensus_facts (id, cancer_id, category, fact_key, title, clinical_detail, active) "
                "VALUES ('fact-pg-1', 'cancer-breast', 'symptoms', 'breast_lump', 'Lump', 'Clinical detail', true)"
            ))
            conn.execute(text(
                "INSERT INTO consensus_fact_sources (id, consensus_fact_id, source_id, country_code, "
                "quote_snippet, attribution_text, source_url) "
                "VALUES ('cfs-pg-1', 'fact-pg-1', 'nci-us', 'US', "
                "'Lump in breast.', 'Attribution note.', 'https://www.cancer.gov/types/breast')"
            ))
            conn.commit()

        # 3. Upgrade to L004 head
        command.upgrade(cfg, "head")

        # 4. Dry-run transition on PostgreSQL
        dry_res = transition_populated_l003_database(pg_engine, dry_run=True)
        assert dry_res["status"] == "VALIDATED_NO_MUTATION"
        assert dry_res["mode"] == "DRY_RUN"

        # 5. Apply transition on PostgreSQL
        apply_res = transition_populated_l003_database(pg_engine, dry_run=False)
        assert apply_res["status"] == "SUCCESS"
        assert apply_res["mode"] == "APPLY"
        assert apply_res["citations_linked"] == 1
        assert apply_res["remaining_unlinked_citations"] == 0

        # 6. Verify repeat-safe idempotency on PostgreSQL
        repeat_res = transition_populated_l003_database(pg_engine, dry_run=False)
        assert repeat_res["status"] == "SUCCESS"
        assert repeat_res["citations_linked"] == 0

        # 7. Verify postcondition in database: foreign keys valid, all 32 documents exist, citation linked
        with pg_engine.connect() as conn:
            doc_count = conn.execute(text("SELECT COUNT(*) FROM source_documents")).scalar()
            assert doc_count == 32
            linked_count = conn.execute(
                text("SELECT COUNT(*) FROM consensus_fact_sources WHERE source_document_id = 'doc-pg-1'")
            ).scalar()
            assert linked_count == 1
            unlinked = conn.execute(
                text("SELECT COUNT(*) FROM consensus_fact_sources WHERE source_document_id IS NULL")
            ).scalar()
            assert unlinked == 0

        pg_engine.dispose()

