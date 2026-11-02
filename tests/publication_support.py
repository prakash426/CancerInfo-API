"""Rights decisions for disposable fixtures only, never a source clearance."""
from datetime import datetime

from app.models import SourceDocument


def approve_test_document(doc):
    doc.publication_status = "ELIGIBLE"
    doc.rights_evidence_url = "https://example.invalid/test-only-rights"
    doc.rights_reviewed_at = datetime(2026, 11, 2)
    doc.rights_reviewer = "Synthetic test fixture"
    doc.permissible_use = "Synthetic regression testing only"
    doc.redistribution_allowed = True
    doc.commercial_redistribution_allowed = True
    doc.full_text_storage_allowed = True
    doc.derived_summary_allowed = True
    doc.attribution_required = True
    doc.attribution_text = "Synthetic document attribution"
    doc.third_party_permission_status = "NOT_APPLICABLE"
    doc.third_party_permission_notes = None
    doc.quarantine_reason = None
    return doc


def add_public_document(db, source_id, url, country="GLOBAL"):
    doc = approve_test_document(SourceDocument(
        source_id=source_id, original_url=url, canonical_url=url,
        title="Synthetic public evidence", country_code=country,
        content_hash="0" * 64,
    ))
    db.add(doc)
    db.flush()
    return doc
