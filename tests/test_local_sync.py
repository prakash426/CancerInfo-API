"""A complete source snapshot updates a migrated local copy without data loss."""
import os
import sqlite3
import json
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import Session

from app.database.local_sync import sync_local_database
from app.database.migration_check import get_alembic_config,set_alembic_url_safe,verify_database_schema_at_head
from app.ingestion.seed import seed_database
from app.models import Cancer, SourceDocument, ContentRecord, WhoFactProvenance


@pytest.fixture
def source_pg():
    if not os.environ.get('POSTGRES_TEST_URL'):
        pytest.skip('Dedicated local PostgreSQL URL not supplied')
    from db_support import disposable_postgres
    with disposable_postgres(os.environ['POSTGRES_TEST_URL']) as url:
        engine=create_engine(url)
        cfg=get_alembic_config();set_alembic_url_safe(cfg,url)
        command.upgrade(cfg,'0005_record_publication')
        with Session(engine) as db:
            seed_database(db)
            record=db.query(ContentRecord).first()
            db.add(WhoFactProvenance(content_record_id=record.id,heading_path='Preserved WHO locator'))
            for doc in db.query(SourceDocument).filter_by(source_id='who-global'):
                doc.publication_status='ELIGIBLE'
                doc.noncommercial_redistribution_allowed=True
                doc.approved_publication_content_types=['STRUCTURED_EXTRACTION']
                doc.third_party_permission_status='SUBMITTED'
            db.commit()
        with engine.begin() as conn:
            conn.execute(text('CREATE TABLE cancer_content (id BIGINT PRIMARY KEY, content TEXT)'))
            conn.execute(text("INSERT INTO cancer_content VALUES (1, 'Preserved legacy content')"))
        try:yield engine
        finally:engine.dispose()


def legacy_local(path):
    engine=create_engine('sqlite:///'+str(path))
    cfg=get_alembic_config();set_alembic_url_safe(cfg,str(engine.url));command.upgrade(cfg,'0003_who_provenance')
    with engine.begin() as db:
        db.execute(text("INSERT INTO cancers (id,slug,canonical_name,taxonomy_codes) VALUES ('local-only','local-only','Local-only research','{}')"))
        db.execute(text('CREATE TABLE private_research (id INTEGER PRIMARY KEY, notes TEXT)'))
        db.execute(text("INSERT INTO private_research VALUES (1,'Keep this research')"))
    engine.dispose()


def test_source_and_local_data_preserved_across_sync(source_pg,tmp_path):
    local=tmp_path/'local.db';backup=tmp_path/'before.db';legacy_local(local)
    with sqlite3.connect(local) as db:
        before='\n'.join(db.iterdump())
    result=sync_local_database(source_pg,local,backup)
    assert result['verified']
    assert result['local_only_rows_preserved']['cancers']==1
    with sqlite3.connect(backup) as db:
        assert '\n'.join(db.iterdump())==before
    target=create_engine('sqlite:///'+str(local))
    try:
        assert verify_database_schema_at_head(target)
        with Session(target) as db:
            assert db.get(Cancer,'local-only')
            doc=db.query(SourceDocument).filter_by(source_id='who-global').first()
            assert doc.noncommercial_redistribution_allowed is True
            assert doc.approved_publication_content_types==['STRUCTURED_EXTRACTION']
            assert doc.third_party_permission_status=='SUBMITTED'
            assert db.query(WhoFactProvenance).count()==1
        with target.connect() as db:
            assert db.execute(text('SELECT notes FROM private_research')).scalar_one()=='Keep this research'
            assert db.execute(text('SELECT content FROM cancer_content')).scalar_one()=='Preserved legacy content'
        # Repeated sync remains safe and retains source rows and local-only work.
        again=sync_local_database(source_pg,local,tmp_path/'second-backup.db')
        assert again['source_counts']==result['source_counts']
        assert again['local_only_rows_preserved']['cancers']==1
    finally:target.dispose()


def test_failed_preparation_never_changes_local_database(source_pg,tmp_path):
    local=tmp_path/'local.db';legacy_local(local)
    with sqlite3.connect(local) as db:
        # A conflicting table shape cannot silently replace private work.
        db.execute('CREATE TABLE cancer_content (id INTEGER PRIMARY KEY, private_notes TEXT)')
        db.execute("INSERT INTO cancer_content VALUES (99,'Original private notes')")
        db.commit();before='\n'.join(db.iterdump())
    with pytest.raises(ValueError,match='incompatible columns'):
        sync_local_database(source_pg,local,tmp_path/'before.db')
    with sqlite3.connect(local) as db:
        assert '\n'.join(db.iterdump())==before


def test_intervening_local_edit_is_not_overwritten(source_pg,tmp_path,monkeypatch):
    import app.database.local_sync as sync_module
    local=tmp_path/'local.db';legacy_local(local)
    original_capture=sync_module.capture_live_rows
    def capture_then_edit(engine):
        result=original_capture(engine)
        with sqlite3.connect(local) as db:
            db.execute("UPDATE private_research SET notes='New work during sync' WHERE id=1")
            db.commit()
        return result
    monkeypatch.setattr(sync_module,'capture_live_rows',capture_then_edit)
    with pytest.raises(ValueError,match='changed during preparation'):
        sync_module.sync_local_database(source_pg,local,tmp_path/'before.db')
    with sqlite3.connect(local) as db:
        assert db.execute('SELECT notes FROM private_research').fetchone()[0]=='New work during sync'
        assert 'noncommercial_redistribution_allowed' not in {r[1] for r in db.execute('PRAGMA table_info(source_documents)')}


def test_plan_records_exact_requested_values():
    plan=json.loads(Path('policies/who-noncommercial-20261103.json').read_text())
    assert len(plan['documents'])==48
    assert len({d['id'] for d in plan['documents']})==48
    assert sum(d['updates'].get('third_party_permission_status')=='SUBMITTED' for d in plan['documents'])==16
    for d in plan['documents']:
        u=d['updates']
        assert u['publication_status']=='ELIGIBLE'
        assert u['redistribution_allowed'] is True
        assert u['noncommercial_redistribution_allowed'] is True
        assert u['commercial_redistribution_allowed'] is False
        assert u['approved_publication_content_types']==['STRUCTURED_EXTRACTION']
        assert u['permissible_use']=='Confirmed, Non-commercial research and educational use only under CC BY-NC-SA 3.0 IGO;'
        assert 'attribution_text' not in u and 'rights_evidence_url' not in u


def test_followup_clears_exact_sixteen_pending_reviews_only():
    original=json.loads(Path('policies/who-noncommercial-20261103.json').read_text())
    followup=json.loads(Path('policies/who-text-only-20261103.json').read_text())
    expected={d['id'] for d in original['documents'] if d['updates'].get('third_party_permission_status')=='SUBMITTED'}
    assert len(followup['documents'])==16
    assert {d['id'] for d in followup['documents']}==expected
    assert followup['expected_public_records']==original['expected_public_records']
    assert len(followup['expected_noncommercial_public_records'])==324
    for d in followup['documents']:
        assert d['before']['third_party_permission_status']=='SUBMITTED'
        assert d['updates']=={'third_party_permission_status':'NOT_APPLICABLE','third_party_permission_notes':'Owner confirmed that only WHO-owned text is used and third-party components are excluded.'}
