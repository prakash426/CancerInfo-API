"""WHO handoff importer tests: transform, rights enforcement, roundtrip."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.ingestion.who_import import build_documents, run_import
from app.ingestion.who_validate import validate_package
from app.main import app
from test_migrations import test_db_url  # noqa: F401: disposable dialect fixture
from app.models import (Cancer, ContentRecord, ContentSource, ContentVersion,
                        Source, SourceDocument, WhoFactProvenance,
                        ConsensusFact, ConsensusFactSource)

URL_A = "https://www.who.int/news-room/fact-sheets/detail/lung-cancer"
URL_B = "https://www.who.int/news-room/fact-sheets/detail/cancer"


def _register():
    register = {}
    for num in range(1, 26):
        cid = "CL%02d" % num
        if cid == "CL01":
            register[cid] = ("Lung cancer", "lung-cancer")
        else:
            register[cid] = ("Cancer %s" % cid, "cancer-%s" % cid.lower())
    return register


def _coverage_row(cid, name, slug, **over):
    row = {"cancer_id": cid, "cancer_slug": slug, "cancer_name": name,
           "status": "no_qualifying_page_found", "dedicated_pages": "0",
           "substantial_sections": "0", "brief_mentions": "0",
           "not_relevant_checked": "0", "reviewed_facts": "0",
           "reviewed_sections": "0", "best_url": "",
           "best_classification": "", "detail": ""}
    row.update(over)
    return row


def _page_row(cid, slug, name, url, relevance, third_party="FALSE",
              title="Title", date="2026-04-16", match="h2",
              page_type="fact_sheet"):
    return {"cancer_id": cid, "cancer_slug": slug, "cancer_name": name,
            "original_url": url, "canonical_url": url, "page_title": title,
            "h1": title, "publisher": "World Health Organization",
            "language": "en", "published_at": date, "updated_at": "",
            "retrieved_at_utc": "2026-11-01T00:00:00Z",
            "page_type": page_type, "match_locations": match,
            "relevance_class": relevance, "relevance_reason": "reason",
            "third_party_content_flag": third_party,
            "rights_review_status": "pending", "review_notes": "notes"}


def _section_row(sid, cid, url, heading="H1 X > H2 Key facts",
                 topic="statistics"):
    return {"section_id": sid, "cancer_id": cid, "canonical_url": url,
            "heading_path": heading, "heading_level": "H2",
            "fragment_or_locator": "", "topic": topic,
            "section_summary": "summary", "content_available": "TRUE",
            "reason_if_withheld": ""}


def _fact_row(url, category="statistics", text="Cases: 10 cases",
              heading="H2 Key facts", date="2026-04-16", period="2022",
              geo="global", pop="all persons", units="cases",
              limits=None, rights="pending"):
    return {"cancer_id": "CL01", "cancer_slug": "lung-cancer",
            "category": category, "subcategory": None, "fact_text": text,
            "fact_type": "summary", "source_url": url,
            "source_locator": heading, "heading_path": heading,
            "source_published_at": date, "source_updated_at": None,
            "retrieved_at_utc": "2026-11-01T00:00:00Z", "geography": geo,
            "population": pop, "reference_period": period, "units": units,
            "limitations": limits, "transformation": "paraphrased_summary",
            "verification_status": "verified_on_page",
            "rights_review_status": rights}


def _mini_package():
    register = _register()
    coverage = [_coverage_row("CL01", "Lung cancer", "lung-cancer",
                              status="found", dedicated_pages="1",
                              brief_mentions="1", reviewed_facts="3",
                              reviewed_sections="2")]
    for cid in sorted(register):
        if cid != "CL01":
            name, slug = register[cid]
            coverage.append(_coverage_row(cid, name, slug))
    pkg = {
        "pages": [
            _page_row("CL01", "lung-cancer", "Lung cancer", URL_A,
                      "dedicated_page", third_party="TRUE"),
            _page_row("CL01", "lung-cancer", "Lung cancer", URL_B,
                      "brief_mention", title="Cancer", date="2026-07-03"),
        ],
        "sections": [
            _section_row("WS001", "CL01", URL_A),
            _section_row("WS002", "CL01", URL_B,
                         heading="H1 Cancer > Key facts list"),
        ],
        "facts": [
            _fact_row(URL_A, text="Cases: 10 cases"),
            _fact_row(URL_A, text="Deaths: 8 deaths"),
            _fact_row(URL_B, text="List cases: 26 cases",
                      heading="Key facts list", date="2026-07-03"),
        ],
        "coverage": coverage,
    }
    return pkg, register


def _decisions(url_b_decision="METADATA_ONLY", signed=True):
    reviewer = "T. Approver" if signed else ""
    reviewed = "2026-11-01" if signed else ""
    base = {"reviewer": reviewer, "reviewed_at": reviewed,
            "permissible_use": "Non-commercial research only",
            "rights_evidence_url": "https://www.who.int/about/policies",
            "notes": ""}
    return {
        URL_A: dict({"canonical_url": URL_A,
                     "decision": "APPROVE_SUMMARIES"}, **base),
        URL_B: dict({"canonical_url": URL_B, "decision": url_b_decision},
                    **base),
    }


@pytest.fixture
def isolated_db(test_db_url):
    from alembic import command
    from app.database.migration_check import get_alembic_config, set_alembic_url_safe
    cfg = get_alembic_config()
    set_alembic_url_safe(cfg, test_db_url)
    command.upgrade(cfg, "head")
    engine = create_engine(test_db_url)
    session = sessionmaker(bind=engine)()
    session.add(Source(
        id="who-global", organization_name="World Health Organization",
        source_name="WHO", base_url="https://www.who.int",
        country_code="GLOBAL", source_type="international_agency",
        trust_tier="TIER_1",
        authority_type="United Nations Specialized International "
                       "Public Health Agency",
        license_type="CC BY-NC-SA 3.0 IGO", license_status="REVIEW_REQUIRED",
        active=True))
    session.add(Cancer(slug="lung-cancer", canonical_name="Lung cancer"))
    session.commit()
    yield session
    session.close()
    engine.dispose()
# --- part 2: behavior tests ---
def test_valid_mini_package_passes_validation():
    pkg, register = _mini_package()
    report = validate_package(pkg, register)
    assert report["errors"] == []
    assert report["stats"]["facts"] == 3


def test_validator_rejects_bad_package():
    pkg, register = _mini_package()
    pkg["facts"][0]["category"] = "not_a_category"
    pkg["facts"][1]["fact_text"] = pkg["facts"][0]["fact_text"]
    pkg["facts"][2]["source_published_at"] = "1999-01-01"
    report = validate_package(pkg, register)
    joined = "\n".join(report["errors"])
    assert "unsupported category" in joined
    assert "duplicate fact text" in joined
    assert "invented date" in joined


def test_build_documents_groups_facts_and_keys():
    pkg, _register = _mini_package()
    documents, provenance, _meta, skipped, _warnings = build_documents(
        pkg, _decisions())
    assert len(documents) == 1
    assert documents[0].cancer_slug == "lung-cancer"
    assert len(documents[0].sections) == 2
    subs = [s.subcategory for s in documents[0].sections]
    assert len(set(subs)) == 2
    assert "Reference period: 2022" in documents[0].sections[0].content
    assert "Geography: global" in documents[0].sections[0].content
    assert documents[0].sections[0].source_locator == "H2 Key facts"
    assert len(provenance) == 2
    assert skipped == []


def test_human_decision_and_date_formats_accepted(tmp_path):
    from app.ingestion.who_import import _parse_date, load_decisions
    assert _parse_date("11/1/26").date().isoformat() == "2026-11-01"
    assert _parse_date("2026-11-01").date().isoformat() == "2026-11-01"
    sheet = tmp_path / "sheet.csv"
    sheet.write_text(
        "canonical_url,page_title,cancers,best_classification,"
        "third_party_content_flag,suggested_decision,suggestion_reason,"
        "decision,reviewer,reviewed_at,permissible_use,"
        "rights_evidence_url,notes\n"
        "%s,T,C,dedicated_page,FALSE,APPROVE_SUMMARIES,r,Approved,R,"
        "11/1/26,u,e,\n" % URL_A, encoding="utf-8")
    decisions = load_decisions(str(sheet))
    assert decisions[URL_A]["decision"] == "APPROVE_SUMMARIES"


def test_keys_stay_unique_across_documents():
    pkg, _register = _mini_package()
    pkg["facts"].append(_fact_row(
        URL_B, text="Other cases: 5 cases", heading="H2 Key facts",
        date="2026-07-03"))
    decisions = _decisions()
    decisions[URL_B]["decision"] = "APPROVE_SUMMARIES"
    documents, _prov, _meta, _skipped, _warnings = build_documents(
        pkg, decisions)
    assert len(documents) == 2
    keys = [(s.category, s.subcategory)
            for doc in documents for s in doc.sections]
    assert len(keys) == 4
    assert len(set(keys)) == 4


def test_run_import_creates_records_and_provenance(isolated_db):
    pkg, _register = _mini_package()
    manifest = run_import(isolated_db, pkg, _decisions())
    isolated_db.commit()
    assert manifest["created"] == 2
    assert manifest["provenance_rows"] == 2
    assert manifest["metadata_docs"] == 1
    docs = isolated_db.query(SourceDocument).all()
    assert len(docs) == 2
    assert {d.publication_status for d in docs} <= {"REVIEW_REQUIRED",
                                                   "QUARANTINED"}
    content_doc = [d for d in docs if d.original_url == URL_A][0]
    assert content_doc.quarantine_reason is None
    assert content_doc.third_party_permission_status == \
        "REQUIRED_NOT_SUBMITTED"
    assert content_doc.rights_reviewer == "T. Approver"
    meta_doc = [d for d in docs if d.original_url == URL_B][0]
    assert meta_doc.publication_status == "QUARANTINED"
    assert meta_doc.processing_status == "METADATA_ONLY"
    rows = isolated_db.query(WhoFactProvenance).all()
    assert len(rows) == 2
    assert rows[0].heading_path == "H2 Key facts"
    assert rows[0].units == "cases"
    versions = isolated_db.query(ContentVersion).all()
    assert len(versions) == 2


def test_unsigned_approval_becomes_metadata_only(isolated_db):
    pkg, _register = _mini_package()
    manifest = run_import(isolated_db, pkg, _decisions(signed=False))
    isolated_db.commit()
    assert manifest["created"] == 0
    assert manifest["metadata_docs"] == 2
    assert manifest["warnings"]
    records = isolated_db.query(ContentRecord).all()
    assert records == []


def test_rejected_url_skipped(isolated_db):
    pkg, _register = _mini_package()
    decisions = _decisions(url_b_decision="REJECT")
    decisions[URL_A]["decision"] = "REJECT"
    manifest = run_import(isolated_db, pkg, decisions)
    isolated_db.commit()
    assert manifest["created"] == 0
    assert manifest["metadata_docs"] == 0
    assert len(manifest["skipped"]) == 2
    assert isolated_db.query(SourceDocument).count() == 0


def test_second_run_updates_and_retires(isolated_db):
    pkg, _register = _mini_package()
    run_import(isolated_db, pkg, _decisions())
    isolated_db.commit()
    pkg["facts"][0]["fact_text"] = "Cases: 11 cases"
    del pkg["facts"][1]
    manifest = run_import(isolated_db, pkg, _decisions())
    isolated_db.commit()
    assert manifest["updated"] == 1
    assert manifest["retired"] == 1
    active = isolated_db.query(ContentRecord).filter(
        ContentRecord.active == True).all()
    assert len(active) == 1
    assert "11 cases" in active[0].content


def test_api_withholds_unreviewed_import(isolated_db):
    pkg, _register = _mini_package()
    run_import(isolated_db, pkg, _decisions())
    isolated_db.commit()

    def override():
        yield isolated_db

    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        resp = client.get("/v1/cancers/lung-cancer/statistics"
                          "?source=who-global")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["data"]["records"] == []
    assert resp.json()["pagination"]["total_records"] == 0
    assert isolated_db.query(ContentRecord).count() == 2
    assert isolated_db.query(SourceDocument).filter_by(publication_status="REVIEW_REQUIRED").count() == 1


@pytest.mark.parametrize("withdrawal", ["METADATA_ONLY", "REJECT", "unsigned", "missing"])
def test_rights_withdrawal_retires_content_and_preserves_history(isolated_db, withdrawal):
    from publication_support import add_public_document
    pkg, _ = _mini_package()
    run_import(isolated_db, pkg, _decisions())
    # Evidence outside this package must remain untouched.
    other_doc = add_public_document(isolated_db, "who-global", "https://example.invalid/unrelated")
    cancer = isolated_db.query(Cancer).one()
    other = ContentRecord(canonical_cancer_id=cancer.id, category="overview", content="Unrelated fixture")
    isolated_db.add(other)
    isolated_db.flush()
    isolated_db.add(ContentSource(content_record_id=other.id, source_id="who-global",
                                 source_url=other_doc.original_url, source_document=other_doc))
    withdrawn_doc = isolated_db.query(SourceDocument).filter_by(original_url=URL_A).one()
    affected = isolated_db.query(ContentRecord).filter(ContentRecord.id != other.id).first()
    # Shared evidence is withheld as a whole; its unrelated contributor and
    # separate record remain intact.
    isolated_db.add(ContentSource(content_record_id=affected.id, source_id="who-global",
                                 source_url=other_doc.original_url, source_document=other_doc))
    fact = ConsensusFact(cancer_id=cancer.id, category="symptoms", fact_key="withdrawn-fact",
                         title="Synthetic shared consensus")
    isolated_db.add(fact)
    isolated_db.flush()
    isolated_db.add_all([
        ConsensusFactSource(consensus_fact_id=fact.id, source_id="who-global",
                            source_url=withdrawn_doc.original_url, source_document=withdrawn_doc),
        ConsensusFactSource(consensus_fact_id=fact.id, source_id="who-global",
                            source_url=other_doc.original_url, source_document=other_doc),
    ])
    isolated_db.commit()
    record_ids = [r.id for r in isolated_db.query(ContentRecord) if r.id != other.id]
    originals = [(v.id, v.content, v.change_reason) for v in isolated_db.query(ContentVersion)]
    provenance = [(p.id, p.content_record_id) for p in isolated_db.query(WhoFactProvenance)]
    links_before = isolated_db.query(ContentSource).count()
    decisions = _decisions()
    if withdrawal == "unsigned":
        decisions[URL_A]["reviewer"] = ""
    elif withdrawal == "missing":
        del decisions[URL_A]
    else:
        decisions[URL_A]["decision"] = withdrawal
    result = run_import(isolated_db, pkg, decisions)
    isolated_db.commit()
    assert result["retired"] == 2
    assert all(not isolated_db.get(ContentRecord, rid).active for rid in record_ids)
    assert other.active
    assert not fact.active
    assert isolated_db.query(ConsensusFactSource).filter_by(consensus_fact_id=fact.id).count() == 2
    assert other_doc.publication_status == "ELIGIBLE"
    assert isolated_db.query(ContentSource).count() == links_before
    assert [(p.id, p.content_record_id) for p in isolated_db.query(WhoFactProvenance)] == provenance
    assert [(v.id, v.content, v.change_reason) for v in isolated_db.query(ContentVersion)
            if v.change_type != "RIGHTS_WITHDRAWN"] == originals
    assert isolated_db.query(ContentVersion).filter_by(change_type="RIGHTS_WITHDRAWN").count() == 2
    doc = isolated_db.query(SourceDocument).filter_by(original_url=URL_A).one()
    assert doc.publication_status == "QUARANTINED"
    assert doc.processing_status == ("REJECTED" if withdrawal == "REJECT" else "METADATA_ONLY")
    repeat = run_import(isolated_db, pkg, decisions)
    isolated_db.commit()
    assert repeat["retired"] == 0
    assert isolated_db.query(ContentVersion).filter_by(change_type="RIGHTS_WITHDRAWN").count() == 2


def test_rights_withdrawal_rolls_back_with_the_caller_transaction(isolated_db, monkeypatch):
    import app.ingestion.who_import as importer
    pkg, _ = _mini_package()
    run_import(isolated_db, pkg, _decisions())
    isolated_db.commit()
    before = [(r.id, r.active, r.version_number) for r in isolated_db.query(ContentRecord)]
    original = importer._withdraw_document

    def fail_after_withdrawal(*args):
        original(*args)
        raise RuntimeError("Synthetic transaction failure")

    monkeypatch.setattr(importer, "_withdraw_document", fail_after_withdrawal)
    decisions = _decisions()
    decisions[URL_A]["decision"] = "REJECT"
    with pytest.raises(RuntimeError, match="Synthetic transaction failure"):
        run_import(isolated_db, pkg, decisions)
    isolated_db.rollback()
    assert [(r.id, r.active, r.version_number) for r in isolated_db.query(ContentRecord)] == before
    assert isolated_db.query(ContentVersion).count() == 2
    assert isolated_db.query(SourceDocument).filter_by(original_url=URL_A).one().publication_status == "REVIEW_REQUIRED"
