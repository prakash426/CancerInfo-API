"""Source text is published only while exact text, quote and citation stay reviewed."""
import copy
from datetime import datetime
from hashlib import sha256
import json

import pytest
from test_public_contract import db_session  # noqa: F401
from test_publication_gates import gate_data, assert_withheld
from app.repositories.publication import PublicEvidence
from scripts.publish_reviewed_excerpts import publish


def approve_excerpt(db, data):
    doc, rec, fact, link, citation, version = data
    rec.content_type = 'SOURCE_CONTENT'
    doc.approved_publication_content_types = ['SOURCE_CONTENT']
    doc.derived_summary_allowed = False
    doc.publication_record_reviews = {rec.id: {
        'mode': 'UNCHANGED_EXCERPT', 'sha256': sha256(rec.content.encode()).hexdigest(),
        'quote_sha256': sha256((link.quote_snippet or '').encode()).hexdigest(),
        'source_url': link.source_url, 'copied_at': link.retrieved_at.isoformat()}}
    db.flush()


def test_exact_excerpt_and_no_derived_consensus(client, db_session, gate_data):
    approve_excerpt(db_session, gate_data)
    result = client.get('/v1/cancers/gate-cancer/symptoms').json()['data']
    assert len(result['records']) == 1
    assert not result['items']
    assert client.get('/v1/coverage?cancer=gate-cancer').json()['data']['total_content_records'] == 1


@pytest.mark.parametrize('damage', ['text', 'quote', 'url', 'copied', 'missing', 'malformed', 'wrong_mode', 'revoke'])
def test_excerpt_revokes_immediately_if_review_no_longer_matches(client, db_session, gate_data, damage):
    approve_excerpt(db_session, gate_data)
    doc, rec, _, link, *_ = gate_data
    if damage == 'text': rec.content += ' unreviewed change'
    elif damage == 'quote': link.quote_snippet = 'unreviewed quotation'
    elif damage == 'url': link.source_url += '/unreviewed'
    elif damage == 'copied': link.retrieved_at = datetime(2000,1,1)
    elif damage == 'missing': doc.publication_record_reviews = None
    elif damage == 'malformed': doc.publication_record_reviews = ['not a review']
    elif damage == 'wrong_mode':
        review = copy.deepcopy(doc.publication_record_reviews)
        review[rec.id]['mode'] = 'ADAPTED'
        doc.publication_record_reviews = review
    else: doc.publication_status = 'REVIEW_REQUIRED'
    db_session.flush()
    assert_withheld(client)


def test_source_content_history_requires_matching_review(client, db_session, gate_data):
    approve_excerpt(db_session, gate_data)
    version = gate_data[-1]
    snapshot = json.loads(version.change_reason)
    snapshot['content_type'] = 'SOURCE_CONTENT'
    version.change_reason = json.dumps(snapshot)
    db_session.flush()
    history=client.get('/v1/cancers/gate-cancer/versions').json()['data']
    assert len(history) == 1
    assert history[0]['sources'][0]['attribution_text']==gate_data[0].attribution_text
    assert history[0]['sources'][0]['url']==gate_data[3].source_url
    version.content = 'unreviewed historical text'
    db_session.flush()
    assert client.get('/v1/cancers/gate-cancer/versions').json()['data'] == []


def test_portal_and_openapi_publish_required_notices(client):
    portal = client.get('/').text
    spec = client.get('/openapi.json').json()['info']['description']
    for text in (portal, spec):
        assert 'Open Government Licence v3.0' in text
        assert 'no specific charge' in text or 'specific charge' in text
        assert 'no charge' in text
        assert 'United States Government' in text


def make_plan(data):
    doc, original, _, link, *_ = data
    rid = 'synthetic-reviewed-copy'
    record = dict(id=rid, canonical_cancer_id=original.canonical_cancer_id,
        category=original.category, subcategory='reviewed-copy', content=original.content,
        content_type='SOURCE_CONTENT', country_code=original.country_code, region_code=None,
        jurisdiction_scope=original.jurisdiction_scope, language=original.language,
        audience=original.audience, active=True)
    citation = dict(id='synthetic-reviewed-citation', source_id=link.source_id,
        source_document_id=doc.id, source_url=link.source_url,
        retrieved_at=link.retrieved_at.isoformat(), quote_snippet=None)
    updates = {'approved_publication_content_types':['SOURCE_CONTENT'], 'publication_record_reviews':{
        rid:{'mode':'UNCHANGED_EXCERPT','sha256':sha256(original.content.encode()).hexdigest(),
             'quote_sha256':sha256(b'').hexdigest(),'source_url':link.source_url,
             'copied_at':link.retrieved_at.isoformat()}}}
    policy = {'review':'Synthetic only', 'expected_public_records':[rid], 'documents':[{
        'id':doc.id,'source_id':doc.source_id,'original_url':doc.original_url,'content_hash':doc.content_hash,
        'before':{k:getattr(doc,k) for k in updates},'updates':updates}]}
    return {'policy':policy,'excerpts':[{'original_id':original.id,
        'original_sha256':sha256(original.content.encode()).hexdigest(),'record':record,'citation':citation}]}


def test_append_plan_preserves_originals_and_is_repeat_safe(db_session, gate_data):
    from app.models import ContentRecord, ContentSource, ContentVersion
    doc, original, _, link, *_ = gate_data
    before = (original.content,original.content_type,original.active,link.quote_snippet,link.source_url)
    plan = make_plan(gate_data)
    publish(db_session,plan)
    assert db_session.get(ContentRecord,'synthetic-reviewed-copy').content == original.content
    assert (original.content,original.content_type,original.active,link.quote_snippet,link.source_url)==before
    count=db_session.query(ContentVersion).count()
    assert publish(db_session,plan)['changed_fields']==0
    assert db_session.query(ContentVersion).count()==count
    db_session.get(ContentSource,'synthetic-reviewed-citation').quote_snippet='changed'
    with pytest.raises(ValueError,match='citation changed'):publish(db_session,plan)


def test_invalid_public_manifest_rolls_back_appended_excerpt(db_session, gate_data):
    from app.models import ContentRecord
    plan=make_plan(gate_data)
    plan['policy']['expected_public_records']=[]
    with pytest.raises(ValueError):
        with db_session.begin_nested():publish(db_session,plan)
    assert db_session.get(ContentRecord,'synthetic-reviewed-copy') is None


def test_search_does_not_truncate_reviewed_excerpts(client, db_session, gate_data):
    gate_data[1].content = 'gatedneedle ' + ('Synthetic qualification retained. ' * 15)
    approve_excerpt(db_session, gate_data)
    response = client.get('/v1/search?q=gatedneedle').json()['data']['results']
    item = next(r for r in response if r.get('record'))
    assert item['snippet'] == gate_data[1].content
    assert item['record']['content'] == item['snippet']
