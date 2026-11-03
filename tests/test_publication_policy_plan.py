"""Exact reviewed plans cannot silently overwrite later decisions or content."""
import copy
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.session import Base
from app.models import SourceDocument
from publication_support import add_public_document
from app.ingestion.seed import seed_database
from scripts.apply_publication_policy import apply_plan


@pytest.fixture
def plan_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_database(db)
        doc = add_public_document(db, 'nci-us', 'https://example.invalid/exact-plan')
        db.commit()
        plan = {'review': 'Synthetic only', 'documents': [{
            'id': doc.id, 'source_id': doc.source_id, 'original_url': doc.original_url,
            'content_hash': doc.content_hash, 'before': {'noncommercial_redistribution_allowed': None},
            'updates': {'noncommercial_redistribution_allowed': True}}], 'expected_public_records': []}
        yield db, doc.id, plan
    engine.dispose()


def test_plan_is_dry_run_compatible_and_repeat_safe(plan_db):
    db, doc_id, plan = plan_db
    assert apply_plan(db, plan)['changed_fields'] == 1
    db.rollback()
    assert db.get(SourceDocument, doc_id).noncommercial_redistribution_allowed is None
    apply_plan(db, plan)
    db.commit()
    assert apply_plan(db, plan)['changed_fields'] == 0


@pytest.mark.parametrize('damage', ['hash', 'identity', 'later_review', 'unsupported', 'duplicate', 'manifest'])
def test_plan_refuses_unreviewed_changes(plan_db, damage):
    db, doc_id, original = plan_db
    plan = copy.deepcopy(original)
    item = plan['documents'][0]
    if damage == 'hash': item['content_hash'] = 'changed'
    if damage == 'identity': item['original_url'] += '/unrelated'
    if damage == 'later_review': db.get(SourceDocument, doc_id).noncommercial_redistribution_allowed = False
    if damage == 'unsupported': item['updates']['title'] = 'overwritten'
    if damage == 'duplicate': plan['documents'].append(copy.deepcopy(item))
    if damage == 'manifest': plan['expected_public_records'] = ['not-reviewed']
    with pytest.raises(ValueError): apply_plan(db, plan)
    db.rollback()


def test_submitted_is_valid_but_not_a_third_party_grant(plan_db):
    from app.core.rights_validation import evaluate_publication_eligibility
    db, doc_id, original = plan_db
    plan = copy.deepcopy(original)
    plan['documents'][0]['before'] = {'third_party_permission_status': db.get(SourceDocument, doc_id).third_party_permission_status}
    plan['documents'][0]['updates'] = {'third_party_permission_status': 'SUBMITTED'}
    plan['expected_noncommercial_public_records'] = []
    apply_plan(db, plan)
    doc = db.get(SourceDocument, doc_id)
    assert doc.third_party_permission_status == 'SUBMITTED'
    allowed, reasons = evaluate_publication_eligibility(doc, content_type='STRUCTURED_EXTRACTION', publication_use='NONCOMMERCIAL')
    assert not allowed
    assert any('SUBMITTED' in reason and 'only NOT_APPLICABLE or GRANTED' in reason for reason in reasons)
    db.rollback()


def test_noncommercial_manifest_is_verified_separately_and_scope_restored(plan_db):
    from app.core.publication_access import publication_use
    db, doc_id, plan = plan_db
    plan['expected_noncommercial_public_records'] = ['unexpected']
    token = publication_use.set('NONCOMMERCIAL')
    try:
        with pytest.raises(ValueError, match='NONCOMMERCIAL public record manifest'):
            apply_plan(db, plan)
        assert publication_use.get() == 'NONCOMMERCIAL'
    finally:
        publication_use.reset(token)
        db.rollback()


def test_invalid_third_party_status_is_rejected(plan_db):
    db, doc_id, plan = plan_db
    plan['documents'][0]['before'] = {'third_party_permission_status': db.get(SourceDocument, doc_id).third_party_permission_status}
    plan['documents'][0]['updates'] = {'third_party_permission_status': 'TYPO'}
    with pytest.raises(ValueError):
        apply_plan(db, plan)
    db.rollback()
