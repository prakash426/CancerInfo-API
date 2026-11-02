"""
Consensus Facts and Decoupled Biological Category Tests
"""
import pytest

pytestmark = pytest.mark.usefixtures("public_seed_evidence")



def test_biological_category_decoupled_symptoms(client):
    """
    Test that biological symptoms endpoint returns category_type='biological',
    structured consensus items, and multi-source corroboration tags.
    """
    response = client.get("/v1/cancers/breast-cancer/symptoms")
    assert response.status_code == 200
    res = response.json()
    data = res["data"]

    # Verify category classification
    assert data["category"] == "symptoms"
    assert data["category_type"] == "biological"

    # Verify consensus summary
    assert data["consensus_summary"] is not None
    assert data["consensus_summary"]["total_items"] == 3
    assert data["consensus_summary"]["consensus_status"] == "VERIFIED_MULTI_AUTHORITY"
    assert "nci-us" in data["consensus_summary"]["participating_sources"]
    assert "nhs-uk" in data["consensus_summary"]["participating_sources"]

    # Verify items array
    assert data["items"] is not None
    assert len(data["items"]) == 3

    # Verify first item (Lump or thickening)
    lump_item = next((item for item in data["items"] if item["fact_key"] == "sym-breast-lump"), None)
    assert lump_item is not None
    assert "lump or area of thickened tissue" in lump_item["sign"].lower()
    assert lump_item["corroboration_count"] == 3
    assert len(lump_item["corroborated_by"]) == 3

    # Check authority tags have both organization and authority_type
    orgs = [s["organization"] for s in lump_item["corroborated_by"]]
    assert "National Cancer Institute" in orgs
    assert "National Health Service" in orgs
    assert "World Health Organization" in orgs

    first_source = lump_item["corroborated_by"][0]
    assert first_source["authority_type"] is not None
    assert first_source["trust_tier"].startswith("Tier 1")
    assert first_source["url"].startswith("https://")
    assert first_source["quote"] is not None


def test_biological_category_country_tag_personalization(client):
    """
    Test Option A: All universal symptoms are returned, but corroboration tags
    prioritize / filter to the user's jurisdiction (e.g. US authorities).
    """
    response = client.get("/v1/cancers/breast-cancer/symptoms?country=US")
    assert response.status_code == 200
    res = response.json()
    data = res["data"]

    # All universal symptoms still returned (none hidden)
    assert len(data["items"]) == 3

    # Note explains universality
    assert data["consensus_summary"]["note"] is not None
    assert "universal across borders" in data["consensus_summary"]["note"]
    assert "US" in data["consensus_summary"]["note"]

    # Sources for first item should be US-relevant (NCI or GLOBAL WHO)
    lump_item = data["items"][0]
    for s in lump_item["corroborated_by"]:
        assert s["country_code"] in ["US", "GLOBAL"]


def test_jurisdictional_category_remains_jurisdictional(client):
    """
    Test that policy categories (screening) remain category_type='jurisdictional'
    with jurisdictional scope and country filtering preserved.
    """
    response = client.get("/v1/cancers/colorectal-cancer/screening?country=US")
    assert response.status_code == 200
    res = response.json()
    data = res["data"]

    assert data["category"] == "screening"
    assert data["category_type"] == "jurisdictional"
    assert len(data["records"]) > 0
    assert all(r["jurisdiction"]["country"] in ["US", "GLOBAL"] for r in data["records"])


def test_search_random_string_cough_with_blood(client):
    """
    Test universal search with a freeform patient query 'cough with blood'.
    Should match Lung Cancer as top result with consensus_item match type.
    """
    response = client.get("/v1/search?q=cough with blood")
    assert response.status_code == 200
    res = response.json()
    data = res["data"]

    assert len(data["results"]) > 0

    # Top result should match Lung Cancer
    top_result = data["results"][0]
    assert top_result["cancer"]["slug"] == "lung-cancer"
    assert top_result["match_type"] == "consensus_item"
    assert top_result["score"] >= 3.0
    assert "blood" in top_result["snippet"].lower()
    assert top_result["consensus_item"] is not None
    assert top_result["consensus_item"]["fact_key"] == "sym-lung-cough-blood"
    assert len(top_result["consensus_item"]["corroborated_by"]) >= 2


def test_search_jaundice_matches_pancreatic_cancer(client):
    """
    Test searching for 'jaundice' returns Pancreatic Cancer consensus symptom.
    """
    response = client.get("/v1/search?q=jaundice")
    assert response.status_code == 200
    res = response.json()
    data = res["data"]

    panc_match = next(
        (r for r in data["results"] if r["cancer"]["slug"] == "pancreatic-cancer" and r["match_type"] == "consensus_item"),
        None,
    )
    assert panc_match is not None
    assert "jaundice" in panc_match["snippet"].lower()


def test_search_abcde_matches_melanoma(client):
    """
    Test searching for 'ABCDE' returns Melanoma skin cancer consensus symptom.
    """
    response = client.get("/v1/search?q=ABCDE")
    assert response.status_code == 200
    res = response.json()
    data = res["data"]

    melanoma_match = next(
        (r for r in data["results"] if r["cancer"]["slug"] == "melanoma" and r["match_type"] == "consensus_item"),
        None,
    )
    assert melanoma_match is not None
    assert "abcde" in melanoma_match["snippet"].lower()
