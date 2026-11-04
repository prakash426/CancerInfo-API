"""Saved citation lookup across disposable SQLite and PostgreSQL fixtures."""
from app.models import ContentRecord
from app.schemas.search import SearchResultItem
from test_public_contract import contract_data, db_session  # noqa: F401


def test_found_record_matches_search_item_shape(client, contract_data):
    response = client.get("/v1/facts", params={"ids": "contract-us"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "meta"}
    assert body["meta"]["result_count"] == 1
    item = body["data"][0]
    SearchResultItem.model_validate(item)
    assert item["match_type"] == "content_record"
    assert item["record"]["id"] == "contract-us"
    search = client.get("/v1/search?q=contractneedle&limit=50").json()["data"]["results"]
    expected = next(result for result in search if result["record"] and result["record"]["id"] == "contract-us")
    assert item["record"] == expected["record"]
    assert item["cancer"] == expected["cancer"]
    assert item["record"]["sources"] == expected["record"]["sources"]
    assert item["matched_terms"] == []
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Publication-Use"] == "COMMERCIAL"
    assert response.headers["Cache-Control"] == "private, no-store"


def test_partial_unknown_batch_returns_found_only_in_request_order(client, contract_data):
    response = client.get("/v1/facts", params={"ids": "unknown, contract-global, contract-fact-0, missing"})
    assert response.status_code == 200
    items = response.json()["data"]
    assert [item["record"]["id"] if item["record"] else item["consensus_item"]["id"] for item in items] == [
        "contract-global", "contract-fact-0"
    ]
    assert response.json()["meta"]["result_count"] == 2


def test_consensus_id_resolves_with_search_source_fields(client, contract_data):
    response = client.get("/v1/facts?ids=contract-fact-0")
    assert response.status_code == 200
    item = response.json()["data"][0]
    SearchResultItem.model_validate(item)
    assert item["match_type"] == "consensus_item"
    assert item["record"] is None
    assert item["consensus_item"]["id"] == "contract-fact-0"
    search = client.get("/v1/search?q=contractneedle&limit=50").json()["data"]["results"]
    expected = next(result for result in search if result["consensus_item"] and result["consensus_item"]["id"] == "contract-fact-0")
    assert item["consensus_item"] == expected["consensus_item"]
    assert item["cancer"] == expected["cancer"]


def test_withdrawn_record_is_omitted_without_hiding_other_ids(client, db_session, contract_data):
    record = db_session.get(ContentRecord, "contract-us")
    record.sources[0].source_document.publication_status = "QUARANTINED"
    db_session.flush()
    response = client.get("/v1/facts?ids=contract-us,contract-fact-0")
    assert response.status_code == 200
    assert [item["consensus_item"]["id"] for item in response.json()["data"]] == ["contract-fact-0"]


def test_withdrawn_consensus_is_omitted(client, db_session, contract_data):
    from app.models import ConsensusFact
    fact = db_session.get(ConsensusFact, "contract-fact-0")
    fact.active = False
    db_session.flush()
    response = client.get("/v1/facts?ids=contract-fact-0,contract-global")
    assert response.status_code == 200
    assert [item["record"]["id"] for item in response.json()["data"]] == ["contract-global"]


def test_over_limit_count_uses_existing_validation_envelope(client):
    response = client.get("/v1/facts", params={"ids": ",".join(f"missing-{n}" for n in range(51))})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.headers["X-Request-ID"]


def test_fifty_ids_are_allowed_and_unknown_ids_are_omitted(client):
    response = client.get("/v1/facts", params={"ids": ",".join(f"missing-{n}" for n in range(50))})
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["result_count"] == 0


def test_empty_ids_param_uses_existing_validation_envelope(client):
    for url in ("/v1/facts?ids=", "/v1/facts?ids=%20%20", "/v1/facts?ids=one,,two"):
        response = client.get(url)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
