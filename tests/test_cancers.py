"""
Cancers and Knowledge Content Tests
"""
import pytest

pytestmark = pytest.mark.usefixtures("public_seed_evidence")



def test_list_cancers(client):
    response = client.get("/v1/cancers")
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    assert "meta" in res
    assert "pagination" in res
    assert len(res["data"]) >= 5
    slugs = [c["slug"] for c in res["data"]]
    assert "breast-cancer" in slugs
    assert "colorectal-cancer" in slugs
    assert "lung-cancer" in slugs


def test_get_cancer_by_slug(client):
    response = client.get("/v1/cancers/breast-cancer")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["slug"] == "breast-cancer"
    assert data["canonical_name"] == "Breast Cancer"
    assert "symptoms" in data["available_categories"]
    assert len(data["aliases"]) > 0


def test_get_cancer_by_alias(client):
    # Test resolving "bowel cancer" -> colorectal-cancer
    response = client.get("/v1/cancers/bowel-cancer")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["slug"] == "colorectal-cancer"
    assert data["canonical_name"] == "Colorectal Cancer"

    # Test abbreviation "CRC" -> colorectal-cancer
    response_crc = client.get("/v1/cancers/CRC")
    assert response_crc.status_code == 200
    assert response_crc.json()["data"]["slug"] == "colorectal-cancer"


def test_get_cancer_not_found(client):
    response = client.get("/v1/cancers/non-existent-cancer-xyz")
    assert response.status_code == 404
    err = response.json()["error"]
    assert err["code"] == "CANCER_NOT_FOUND"


def test_get_cancer_sections(client):
    response = client.get("/v1/cancers/breast-cancer/sections")
    assert response.status_code == 200
    sections = response.json()["data"]
    cat_names = [s["category"] for s in sections]
    assert "overview" in cat_names
    assert "symptoms" in cat_names
    assert "screening" in cat_names


def test_get_cancer_category_content_with_provenance(client):
    # Fetch symptoms for breast-cancer
    response = client.get("/v1/cancers/breast-cancer/symptoms")
    assert response.status_code == 200
    res = response.json()
    data = res["data"]
    assert data["category"] == "symptoms"
    assert data["cancer"]["slug"] == "breast-cancer"
    assert len(data["records"]) > 0

    first_record = data["records"][0]
    assert "content" in first_record
    assert "jurisdiction" in first_record
    assert len(first_record["sources"]) > 0

    first_source = first_record["sources"][0]
    assert first_source["organization"] in ["National Cancer Institute", "National Health Service"]
    assert first_source["url"].startswith("http")
    assert "attribution_text" in first_source


def test_get_cancer_category_country_filter(client):
    # US filter
    res_us = client.get("/v1/cancers/breast-cancer/screening?country=US")
    assert res_us.status_code == 200
    records_us = res_us.json()["data"]["records"]
    assert all(r["jurisdiction"]["country"] in ["US", "GLOBAL"] for r in records_us)

    # GB filter
    res_gb = client.get("/v1/cancers/breast-cancer/screening?country=GB")
    assert res_gb.status_code == 200
    records_gb = res_gb.json()["data"]["records"]
    assert all(r["jurisdiction"]["country"] in ["GB", "GLOBAL"] for r in records_gb)
