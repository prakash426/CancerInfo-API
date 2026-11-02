"""
Source Registry and Coverage Tests
"""
import pytest

pytestmark = pytest.mark.usefixtures("public_seed_evidence")



def test_list_sources(client):
    response = client.get("/v1/sources")
    assert response.status_code == 200
    res = response.json()
    sources = res["data"]
    assert len(sources) >= 4
    source_ids = [s["id"] for s in sources]
    assert "nci-us" in source_ids
    assert "who-global" in source_ids
    assert "nhs-uk" in source_ids


def test_get_source_detail(client):
    response = client.get("/v1/sources/nci-us")
    assert response.status_code == 200
    src = response.json()["data"]
    assert src["id"] == "nci-us"
    assert src["organization_name"] == "National Cancer Institute"
    assert src["license_status"] == "APPROVED"
    assert src["trust_tier"].startswith("Tier 1")
    assert src["document_count"] >= 1
    assert src["records_supported_count"] >= 1


def test_source_not_found(client):
    response = client.get("/v1/sources/unknown-nonexistent-source")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SOURCE_NOT_FOUND"


def test_coverage_endpoint(client):
    response = client.get("/v1/coverage")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_cancers"] >= 5
    assert data["total_sources"] >= 4
    assert data["total_content_records"] >= 10
    assert "US" in data["countries_represented"]
    assert "GB" in data["countries_represented"]
    assert "GLOBAL" in data["countries_represented"]
    assert "symptoms" in data["categories_available"]


def test_coverage_specific_cancer(client):
    response = client.get("/v1/coverage?cancer=breast-cancer")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["cancers"]) == 1
    c = data["cancers"][0]
    assert c["slug"] == "breast-cancer"
    assert c["total_records"] >= 3
