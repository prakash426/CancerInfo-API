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
