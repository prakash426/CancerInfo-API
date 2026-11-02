"""Use-specific approvals cannot be inferred from status or source identity."""
import hashlib
from types import SimpleNamespace

import pytest

from publication_support import approve_test_document
from app.core.rights_validation import evaluate_publication_eligibility
from app.core.config import settings
from app.core.publication_access import approved_use, publication_use
from test_publication_gates import gate_data, assert_withheld
from test_public_contract import db_session  # noqa: F401

KEY = "synthetic-noncommercial-key-for-tests-only"


def review(doc):
    doc.commercial_redistribution_allowed = False
    doc.full_text_storage_allowed = False
    doc.noncommercial_redistribution_allowed = True
    doc.approved_publication_content_types = ["STRUCTURED_EXTRACTION", "DERIVED_SUMMARY"]
    return doc


def test_noncommercial_summary_does_not_need_full_text_storage():
    doc = review(approve_test_document(SimpleNamespace()))
    for kind in doc.approved_publication_content_types:
        assert evaluate_publication_eligibility(doc, content_type=kind, publication_use="NONCOMMERCIAL")[0]
    assert not evaluate_publication_eligibility(doc, content_type="SOURCE_CONTENT", publication_use="NONCOMMERCIAL")[0]
    assert not evaluate_publication_eligibility(doc, content_type="DERIVED_SUMMARY")[0]


@pytest.mark.parametrize("field,value", [
    ("redistribution_allowed", False), ("noncommercial_redistribution_allowed", None),
    ("noncommercial_redistribution_allowed", False), ("approved_publication_content_types", None),
    ("approved_publication_content_types", []), ("approved_publication_content_types", "DERIVED_SUMMARY"),
    ("approved_publication_content_types", ["DERIVED_SUMMARY", "UNKNOWN"]),
    ("derived_summary_allowed", False), ("third_party_permission_status", "REQUIRED_NOT_SUBMITTED"),
    ("rights_reviewer", None), ("publication_status", "REVIEW_REQUIRED"),
])
def test_noncommercial_approval_still_fails_closed(field, value):
    doc = review(approve_test_document(SimpleNamespace()))
    setattr(doc, field, value)
    assert not evaluate_publication_eligibility(doc, content_type="DERIVED_SUMMARY", publication_use="NONCOMMERCIAL")[0]


@pytest.mark.parametrize("kind", [None, "UNKNOWN", "TRANSLATION", "SOURCE_CONTENT", [], {}])
def test_output_must_match_exact_reviewed_type(kind):
    doc = review(approve_test_document(SimpleNamespace()))
    assert not evaluate_publication_eligibility(doc, content_type=kind, publication_use="NONCOMMERCIAL")[0]
    assert not evaluate_publication_eligibility(doc, content_type="DERIVED_SUMMARY", publication_use="UNKNOWN")[0]


def test_access_cannot_be_self_declared(monkeypatch):
    monkeypatch.setattr(settings, "NONCOMMERCIAL_API_KEY_SHA256", [hashlib.sha256(KEY.encode()).hexdigest()])
    assert approved_use(KEY) == "NONCOMMERCIAL"
    for value in (None, "NONCOMMERCIAL", "paid-app", KEY + "wrong"):
        assert approved_use(value) == "COMMERCIAL"


def test_noncommercial_access_and_revocation_across_public_surfaces(client, db_session, gate_data, monkeypatch):
    doc, record, fact, link, citation, version = gate_data
    review(doc)
    # Synthetic WHO provenance, never a review of a real WHO page.
    doc.source_id = link.source_id = citation.source_id = "who-global"
    db_session.flush()
    monkeypatch.setattr(settings, "NONCOMMERCIAL_API_KEY_SHA256", [hashlib.sha256(KEY.encode()).hexdigest()])
    assert_withheld(client)
    client.headers["X-API-Key"] = KEY
    result = client.get("/v1/cancers/gate-cancer/symptoms")
    assert len(result.json()["data"]["records"]) == len(result.json()["data"]["items"]) == 1
    assert result.headers["Cache-Control"] == "private, no-store"
    assert "X-API-Key" in result.headers["Vary"]
    assert client.get("/v1/search?q=gatedneedle").json()["pagination"]["total_records"] == 2
    assert client.get("/v1/coverage?cancer=gate-cancer").json()["data"]["total_content_records"] == 1
    assert len(client.get("/v1/cancers/gate-cancer/sections").json()["data"]) == 1
    # Historical type was not captured; current summary approval cannot clear it.
    assert client.get("/v1/cancers/gate-cancer/versions").json()["data"] == []
    record.content_type = "SOURCE_CONTENT"
    db_session.flush()
    assert client.get("/v1/cancers/gate-cancer/symptoms").json()["data"]["records"] == []
    record.content_type = "STRUCTURED_EXTRACTION"
    doc.noncommercial_redistribution_allowed = False
    db_session.flush()
    assert_withheld(client)
    assert db_session.get(type(record), record.id).content == record.content
    doc.noncommercial_redistribution_allowed = True
    db_session.flush()
    monkeypatch.setattr(settings, "NONCOMMERCIAL_API_KEY_SHA256", [])
    assert_withheld(client)
    client.headers.pop("X-API-Key")
    assert publication_use.get() == "COMMERCIAL"


def test_commercial_summary_no_longer_requires_storage_rights(client, db_session, gate_data):
    gate_data[0].full_text_storage_allowed = False
    db_session.flush()
    assert len(client.get("/v1/cancers/gate-cancer/symptoms").json()["data"]["records"]) == 1


def test_source_delivery_requires_explicit_type_and_storage_not_summary_permission():
    doc = review(approve_test_document(SimpleNamespace()))
    doc.approved_publication_content_types = ["SOURCE_CONTENT"]
    doc.derived_summary_allowed = False
    assert not evaluate_publication_eligibility(doc, content_type="SOURCE_CONTENT", publication_use="NONCOMMERCIAL")[0]
    doc.full_text_storage_allowed = True
    assert evaluate_publication_eligibility(doc, content_type="SOURCE_CONTENT", publication_use="NONCOMMERCIAL")[0]


def test_restricted_response_does_not_change_next_request_scope(client, db_session, gate_data, monkeypatch):
    review(gate_data[0])
    db_session.flush()
    monkeypatch.setattr(settings, "NONCOMMERCIAL_API_KEY_SHA256", [hashlib.sha256(KEY.encode()).hexdigest()])
    restricted = client.get("/v1/cancers/gate-cancer/symptoms", headers={"X-API-Key": KEY})
    assert len(restricted.json()["data"]["records"]) == 1
    source = restricted.json()["data"]["records"][0]["sources"][0]
    assert source["noncommercial_redistribution_allowed"] is True
    assert source["commercial_redistribution_allowed"] is False
    assert source["approved_publication_content_types"] == ["STRUCTURED_EXTRACTION", "DERIVED_SUMMARY"]
    assert_withheld(client)
