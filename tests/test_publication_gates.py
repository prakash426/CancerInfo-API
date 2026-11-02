"""Public rights regressions on SQLite and the migrated PostgreSQL schema."""
import json

import pytest

from test_public_contract import db_session  # noqa: F401: parametrized database fixture
from publication_support import add_public_document
from app.models import (Cancer, ContentRecord, ContentSource, ContentVersion,
                        ConsensusFact, ConsensusFactSource)
from app.normalization.hash import compute_content_hash


@pytest.fixture
def gate_data(db_session):
    cancer = Cancer(id="gate-cancer", slug="gate-cancer", canonical_name="Synthetic Gate Cancer")
    db_session.add(cancer)
    doc = add_public_document(db_session, "nci-us", "https://example.invalid/gate", "US")
    record = ContentRecord(id="gate-record", canonical_cancer_id=cancer.id,
                           category="symptoms", content="gatedneedle synthetic record",
                           country_code="US", jurisdiction_scope="COUNTRY", audience="patient")
    fact = ConsensusFact(id="gate-fact", cancer_id=cancer.id, category="symptoms",
                         fact_key="gate-fact", title="gatedneedle synthetic consensus",
                         clinical_detail="Fixture only")
    db_session.add_all([record, fact])
    db_session.flush()
    link = ContentSource(content_record_id=record.id, source_id=doc.source_id,
                         source_url=doc.original_url, source_document=doc)
    citation = ConsensusFactSource(consensus_fact_id=fact.id, source_id=doc.source_id,
                                   source_url=doc.original_url, source_document=doc)
    snapshot = json.dumps({"document_id": doc.id, "source_id": doc.source_id,
                           "url": doc.original_url,
                           "previous_provenance": {"quote": "INTERNAL_WITHDRAWN_QUOTE"}})
    version = ContentVersion(content_record_id=record.id, version_number=1,
                             content=record.content, content_hash=compute_content_hash(record.content),
                             change_reason=snapshot)
    db_session.add_all([link, citation, version])
    db_session.flush()
    yield doc, record, fact, link, citation, version
    db_session.rollback()


def assert_withheld(client):
    category = client.get("/v1/cancers/gate-cancer/symptoms").json()
    assert category["data"]["records"] == []
    assert not category["data"]["items"]
    assert category["pagination"]["total_records"] == 0
    search = client.get("/v1/search?q=gatedneedle&limit=1").json()
    assert search["data"]["results"] == []
    assert search["pagination"]["total_records"] == 0
    assert client.get("/v1/cancers/gate-cancer/versions").json()["data"] == []
    assert client.get("/v1/cancers/gate-cancer/sections").json()["data"] == []
    assert client.get("/v1/cancers/gate-cancer/sources").json()["data"] == []
    assert client.get("/v1/cancers/gate-cancer").json()["data"]["available_categories"] == []
    coverage = client.get("/v1/coverage?cancer=gate-cancer").json()["data"]
    assert coverage["total_content_records"] == 0
    assert coverage["total_sources"] == 0
    assert coverage["total_source_documents"] == 0
    assert coverage["categories_available"] == []
    assert coverage["countries_represented"] == []
    assert coverage["cancers"][0]["supporting_sources"] == []
    assert coverage["cancers"][0]["last_verified_at"] is None


def test_eligible_evidence_is_public_and_internal_history_is_sanitized(client, gate_data):
    result = client.get("/v1/cancers/gate-cancer/symptoms").json()["data"]
    assert len(result["records"]) == len(result["items"]) == 1
    search = client.get("/v1/search?q=gatedneedle&limit=1").json()
    assert search["pagination"]["total_records"] == 2
    assert len(search["data"]["results"]) == 1
    history = client.get("/v1/cancers/gate-cancer/versions")
    assert len(history.json()["data"]) == 1
    assert "INTERNAL_WITHDRAWN_QUOTE" not in history.text
    coverage = client.get("/v1/coverage?cancer=gate-cancer").json()["data"]
    assert coverage["total_content_records"] == 1
    assert coverage["total_source_documents"] == 1


@pytest.mark.parametrize("field,value", [
    ("publication_status", "REVIEW_REQUIRED"), ("publication_status", "QUARANTINED"),
    ("rights_evidence_url", None), ("rights_evidence_url", "invalid"),
    ("rights_reviewed_at", None), ("rights_reviewer", " "),
    ("permissible_use", None), ("redistribution_allowed", False),
    ("commercial_redistribution_allowed", False), ("commercial_redistribution_allowed", None),
    ("derived_summary_allowed", False),
    ("attribution_required", None), ("attribution_text", ""),
    ("third_party_permission_status", "REQUIRED_NOT_SUBMITTED"),
    ("third_party_permission_status", "GRANTED"),
    ("third_party_permission_status", "unknown"), ("third_party_permission_status", None),
    ("quarantine_reason", "Withdrawn"),
])
def test_ineligible_evidence_is_withheld_everywhere(client, db_session, gate_data, field, value):
    setattr(gate_data[0], field, value)
    db_session.flush()
    assert_withheld(client)


@pytest.mark.parametrize("mode", ["missing_document", "no_citations", "inactive_source", "source_mismatch", "url_mismatch"])
def test_missing_or_invalid_citation_links_fail_closed(client, db_session, gate_data, mode):
    doc, record, fact, link, citation, _ = gate_data
    if mode == "missing_document":
        link.source_document = citation.source_document = None
    elif mode == "no_citations":
        db_session.delete(link)
        db_session.delete(citation)
    elif mode == "inactive_source":
        doc.source.active = False
    elif mode == "source_mismatch":
        link.source_id = citation.source_id = "who-global"
    else:
        link.source_url = citation.source_url = "https://example.invalid/uncleared"
    db_session.flush()
    assert_withheld(client)


def test_mixed_evidence_cannot_bypass_gate_with_source_filter(client, db_session, gate_data):
    doc, record, fact, *_ = gate_data
    blocked = add_public_document(db_session, "who-global", "https://example.invalid/blocked")
    blocked.publication_status = "QUARANTINED"
    db_session.add_all([
        ContentSource(content_record_id=record.id, source_id="who-global", source_document=blocked,
                      source_url=blocked.original_url),
        ConsensusFactSource(consensus_fact_id=fact.id, source_id="who-global", source_document=blocked,
                            source_url=blocked.original_url),
    ])
    db_session.flush()
    assert_withheld(client)
    result = client.get("/v1/search?q=gatedneedle&source=nci-us").json()
    assert result["pagination"]["total_records"] == 0
    category = client.get("/v1/cancers/gate-cancer/symptoms?source=nci-us").json()["data"]
    assert category["records"] == [] and not category["items"]


@pytest.mark.parametrize("reason", ["legacy free text", "{}", "[]", '{"document_id":"missing"}', '{"document_id":[]}'])
def test_history_without_verifiable_provenance_stays_internal(client, db_session, gate_data, reason):
    gate_data[-1].change_reason = reason
    db_session.flush()
    assert client.get("/v1/cancers/gate-cancer/versions").json()["data"] == []
    assert db_session.query(ContentVersion).filter_by(content_record_id="gate-record").count() == 1


def test_revocation_takes_effect_without_restarting_or_caching(client, db_session, gate_data):
    from app.repositories.content_repo import ContentRepository
    repo = ContentRepository(db_session)
    assert repo.get_records("gate-cancer", "symptoms")[1] == 1
    before = client.get("/v1/sources/nci-us").json()["data"]["records_supported_count"]
    gate_data[0].publication_status = "QUARANTINED"
    db_session.flush()
    assert repo.get_records("gate-cancer", "symptoms")[1] == 0
    assert_withheld(client)
    after = client.get("/v1/sources/nci-us").json()["data"]["records_supported_count"]
    assert after == before - 1


def test_public_coverage_handles_missing_verification_dates(client, db_session, gate_data):
    from sqlalchemy import update
    db_session.execute(update(ContentSource).where(ContentSource.id == gate_data[3].id)
                       .values(last_verified_at=None))
    db_session.expire_all()
    coverage = client.get("/v1/coverage?cancer=gate-cancer")
    assert coverage.status_code == 200
    assert coverage.json()["data"]["total_content_records"] == 1
    assert coverage.json()["data"]["cancers"][0]["last_verified_at"] is None


def test_eligible_canonical_url_survives_a_document_redirect(client, db_session, gate_data):
    gate_data[0].original_url += "/original"
    db_session.flush()
    result = client.get("/v1/cancers/gate-cancer/symptoms").json()["data"]
    assert len(result["records"]) == 1
    assert len(result["items"]) == 1
