"""L010 contract regressions using synthetic, disposable evidence."""
import math
import os
import pytest
from app.models import Cancer, CancerAlias, ContentRecord, ContentSource, ConsensusFact, ConsensusFactSource
from app.main import app
from app.core.errors import generic_exception_handler
from publication_support import add_public_document, approve_test_document


@pytest.fixture(params=["sqlite"] + (["postgresql"] if os.environ.get("POSTGRES_TEST_URL") else []))
def db_session(request):
    """Run the public contract against the actual migrated PostgreSQL schema."""
    if request.param == "sqlite":
        from conftest import TestingSessionLocal
        with TestingSessionLocal() as db:
            yield db
        return
    from alembic import command
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from db_support import disposable_postgres
    from app.database.migration_check import get_alembic_config, set_alembic_url_safe
    from app.ingestion.seed import seed_database
    with disposable_postgres(os.environ["POSTGRES_TEST_URL"]) as url:
        engine = create_engine(url)
        try:
            cfg = get_alembic_config()
            set_alembic_url_safe(cfg, url)
            command.upgrade(cfg, "head")
            with Session(engine) as db:
                seed_database(db)
                yield db
        finally:
            engine.dispose()


@pytest.fixture
def contract_data(db_session):
    db = db_session
    cancer = Cancer(id="contract-cancer", slug="contract-cancer", canonical_name="Contract Cancer")
    other = Cancer(id="contract-other", slug="contract-other", canonical_name="Contract Other")
    db.add_all([cancer, other])
    db.flush()
    db.add_all([
        CancerAlias(cancer_id=cancer.id, alias="contract approved", review_status="APPROVED"),
        CancerAlias(cancer_id=cancer.id, alias="pendingneedle", review_status="PENDING"),
        CancerAlias(cancer_id=cancer.id, alias="contract collision", review_status="APPROVED"),
        CancerAlias(cancer_id=other.id, alias="contract collision", review_status="APPROVED"),
    ])
    for record_id, country in [("contract-global", "GLOBAL"), ("contract-us", "US"), ("contract-gb", "GB")]:
        record = ContentRecord(id=record_id, canonical_cancer_id=cancer.id, category="symptoms",
                               content="contractneedle synthetic fixture", country_code=country,
                               jurisdiction_scope=country, language="en", audience="patient")
        db.add(record)
        db.flush()
        # Two citations from the same source prove joins cannot duplicate totals.
        for i in range(2):
            url = f"https://example.invalid/{record_id}/{i}"
            doc = add_public_document(db, "nci-us", url)
            db.add(ContentSource(content_record_id=record.id, source_id="nci-us",
                                 source_url=url, source_document=doc))

    for i in range(4):
        fact = ConsensusFact(id=f"contract-fact-{i}", cancer_id=cancer.id, category="symptoms",
                             fact_key=f"contract-fact-{i}", title="contractneedle synthetic fact",
                             clinical_detail="Fixture only", corroboration_count=2)
        db.add(fact)
        db.flush()
        # GLOBAL deliberately inserted first to verify country ordering.
        for source_id, country, suffix in [("who-global", "GLOBAL", "global"),
                                           ("nci-us", "US", "us")]:
            url = f"https://example.invalid/{suffix}/{i}"
            doc = add_public_document(db, source_id, url, country)
            db.add(ConsensusFactSource(consensus_fact_id=fact.id, source_id=source_id,
                                       country_code=country, source_url=url,
                                       source_document=doc))

    db.flush()
    yield
    db.rollback()


def test_unknown_category_is_not_overview(client):
    for url in ["/v1/cancers/breast-cancer/not-a-category", "/v1/search?q=lump&category=not-a-category"]:
        response = client.get(url)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "CATEGORY_NOT_FOUND"
    empty = client.get("/v1/cancers/breast-cancer/grading").json()
    assert empty["data"]["records"] == []
    assert empty["pagination"]["total_records"] == 0
    assert client.get("/v1/cancers/breast-cancer/risk-factors").status_code == 200


@pytest.mark.parametrize("identifier", ["contract-cancer", "contract cancer", "Contract Cancer", "contract-approved"])
def test_exact_and_approved_alias_resolution(client, contract_data, identifier):
    assert client.get(f"/v1/cancers/{identifier}").json()["data"]["id"] == "contract-cancer"


def test_alias_review_and_collision(client, contract_data):
    assert client.get("/v1/cancers/pendingneedle").status_code == 404
    ambiguous = client.get("/v1/cancers/contract-collision")
    assert ambiguous.status_code == 409
    assert ambiguous.json()["error"]["code"] == "AMBIGUOUS_CANCER"
    assert client.get("/v1/cancers/contract-other").status_code == 200
    matches = client.get("/v1/search?q=pendingneedle").json()["data"]["results"]
    assert matches == []


def test_category_country_order_and_duplicate_citations(client, contract_data):
    result = client.get("/v1/cancers/contract-cancer/symptoms?country=us&source=nci-us&limit=1").json()
    assert result["data"]["records"][0]["id"] == "contract-us"
    assert result["pagination"]["total_records"] == 2
    page2 = client.get("/v1/cancers/contract-cancer/symptoms?country=US&source=nci-us&limit=1&page=2").json()
    assert page2["data"]["records"][0]["id"] == "contract-global"
    page3 = client.get("/v1/cancers/contract-cancer/symptoms?country=US&limit=1&page=3").json()
    assert page3["data"]["records"] == []
    assert page3["pagination"]["has_next"] is False
    citations = result["data"]["items"][0]["corroborated_by"]
    assert [c["country_code"] for c in citations] == ["US", "GLOBAL"]


def result_key(r):
    detail = r.get("record") or r.get("consensus_item") or r["cancer"]
    return r["match_type"], detail["id"]


def test_mixed_search_pages_have_no_omissions_or_duplicates(client, contract_data):
    base = "/v1/search?q=contractneedle&country=US&limit="
    complete = client.get(base + "50").json()
    expected = [result_key(r) for r in complete["data"]["results"]]
    assert len(expected) == 6  # Four universal facts and two regional records.
    assert {k[0] for k in expected} == {"consensus_item", "content_record"}
    actual = []
    for page in range(1, math.ceil(len(expected) / 2) + 1):
        result = client.get(base + f"2&page={page}").json()
        assert result["pagination"]["total_records"] == len(expected)
        assert result["meta"]["result_count"] == len(result["data"]["results"])
        actual.extend(result_key(r) for r in result["data"]["results"])
    assert actual == expected
    assert len(set(actual)) == len(actual)
    repeat = client.get(base + "50").json()
    assert [result_key(r) for r in repeat["data"]["results"]] == expected
    beyond = client.get(base + "2&page=4").json()
    assert beyond["data"]["results"] == []
    assert beyond["pagination"]["has_next"] is False


def test_search_filters_and_consensus_country_policy(client, contract_data):
    results = client.get("/v1/search?q=contractneedle&source=nci-us&country=US&category=symptoms").json()["data"]["results"]
    assert len(results) == 6
    for r in results:
        if r["record"]:
            assert r["record"]["jurisdiction"]["country"] in ("US", "GLOBAL")
        else:
            assert [c["source_id"] for c in r["consensus_item"]["corroborated_by"]] == ["nci-us"]
    audience = client.get("/v1/search?q=contractneedle&audience=patient").json()["data"]["results"]
    assert len(audience) == 3
    assert all(r["match_type"] == "content_record" for r in audience)
    absent = client.get("/v1/search?q=contractneedle&source=absent-source").json()
    assert absent["data"]["results"] == []
    gb = client.get("/v1/search?q=contractneedle&country=GB").json()["data"]["results"]
    assert len(gb) == 6
    for r in gb:
        if r["consensus_item"]:
            assert [c["country_code"] for c in r["consensus_item"]["corroborated_by"]] == ["GLOBAL"]


def test_filtered_search_retains_document_rights(client, contract_data, db_session):
    for model in (ConsensusFactSource, ContentSource):
        links = db_session.query(model).filter(model.source_id == "nci-us").all()
        for link in links:
            if link.source_url.startswith("https://example.invalid/"):
                doc = link.source_document
                doc.title = "Synthetic rights fixture"
                doc.attribution_text = "Document attribution"
                doc.reuse_restrictions = "Synthetic restriction"
                doc.rights_evidence_url = "https://example.invalid/rights"
                link.attribution_text = "Link fallback attribution"
    db_session.flush()

    payload = client.get(
        "/v1/search?q=contractneedle&source=nci-us&country=US&limit=50"
    ).json()
    assert payload["pagination"]["total_records"] == 6
    for result in payload["data"]["results"]:
        consensus = result["consensus_item"]
        citations = consensus["corroborated_by"] if consensus else result["record"]["sources"]
        assert citations
        for citation in citations:
            assert citation["source_id"] == "nci-us"
            assert citation["document_title"] == "Synthetic rights fixture"
            assert citation["attribution_text"] == "Document attribution"
            assert citation["publication_status"] == "ELIGIBLE"
            assert citation["reuse_conditions"] == "Synthetic restriction"
            assert citation["commercial_redistribution_allowed"] is True
            assert citation["rights_evidence_url"] == "https://example.invalid/rights"


@pytest.mark.parametrize("url", ["/v1/search?q=x&page=0", "/v1/search?q=x&limit=0",
    "/v1/search?q=x&limit=51", "/v1/search?q=%20%20", "/v1/cancers?page=0", "/v1/cancers?limit=101"])
def test_validation_envelope(client, url):
    response = client.get(url)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "input" not in str(error["details"])
    assert "X-Request-ID" in response.headers


def test_router_errors_and_root_negotiation(client):
    assert client.get("/missing-path").json()["error"]["code"] == "NOT_FOUND"
    response = client.post("/v1/cancers")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in response.headers["allow"]
    assert client.get("/", headers={"Accept": "application/json"}).headers["content-type"].startswith("application/json")
    assert client.get("/", headers={"Accept": "text/html"}).headers["content-type"].startswith("text/html")
    for path in ("/health", "/api/health"):
        assert client.get(path).json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_internal_error_details_are_not_exposed():
    response = await generic_exception_handler(None, RuntimeError("private details"))
    assert response.status_code == 500
    assert b"private details" not in response.body
    assert b"RuntimeError" not in response.body


def test_public_path_inventory():
    paths = app.openapi()["paths"]
    admin = {p for p in paths if p.startswith("/v1/admin/")}
    assert len(paths) == 18
    assert len(admin) == 3
    assert len(set(paths) - admin) == 15
    assert "/v1/facts" in paths
    for code in ("404", "409", "422", "429", "500"):
        assert paths["/v1/search"]["get"]["responses"][code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorResponse"
        }


def test_public_openapi_export_matches_runtime_without_admin_routes():
    import json
    from pathlib import Path
    from scripts.export_public_openapi import build_public_openapi

    exported = json.loads(Path("rapidapi/rapidapi-openapi.json").read_text())
    assert exported == build_public_openapi()
    assert len(exported["paths"]) == 15
    assert "/v1/facts" in exported["paths"]
    assert not any(path.startswith("/v1/admin/") for path in exported["paths"])
