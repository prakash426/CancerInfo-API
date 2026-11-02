"""
Search Endpoint Tests
"""
import pytest

pytestmark = pytest.mark.usefixtures("public_seed_evidence")



def test_search_canonical_cancer_name(client):
    response = client.get("/v1/search?q=breast+cancer")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    results = res["data"]["results"]
    assert len(results) > 0
    # Top result should be breast cancer
    assert results[0]["cancer"]["slug"] == "breast-cancer"


def test_search_alias(client):
    # Search for "bowel cancer"
    response = client.get("/v1/search?q=bowel+cancer")
    assert response.status_code == 200
    results = response.json()["data"]["results"]
    assert len(results) > 0
    slugs = [r["cancer"]["slug"] for r in results]
    assert "colorectal-cancer" in slugs


def test_search_abbreviation(client):
    response = client.get("/v1/search?q=CRC")
    assert response.status_code == 200
    results = response.json()["data"]["results"]
    assert len(results) > 0
    slugs = [r["cancer"]["slug"] for r in results]
    assert "colorectal-cancer" in slugs


def test_search_with_category_term(client):
    # Query: "pancreatic symptoms"
    response = client.get("/v1/search?q=pancreatic+symptoms")
    assert response.status_code == 200
    results = response.json()["data"]["results"]
    assert len(results) > 0
    slugs = [r["cancer"]["slug"] for r in results]
    assert "pancreatic-cancer" in slugs
