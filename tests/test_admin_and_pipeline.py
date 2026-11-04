"""
Admin and Pipeline Tests
"""
from app.core.config import settings
import pytest


@pytest.mark.parametrize("header", ["X-Admin-Key", "Authorization"])
def test_admin_verification_has_no_corpus_dependencies(client, monkeypatch, header):
    from app.api.v1.endpoints import admin
    from app.database.session import get_db
    from app.main import app

    def forbidden(*args, **kwargs):
        raise AssertionError("Verification must not access corpus operations")

    monkeypatch.setattr(admin, "seed_database", forbidden)
    monkeypatch.setattr(admin, "run_ingestion_for_source", forbidden)
    app.dependency_overrides[get_db] = forbidden
    key = settings.ADMIN_API_KEY
    value = key if header == "X-Admin-Key" else f"Bearer {key}"
    response = client.get("/v1/admin/verify", headers={header: value})
    assert response.status_code == 200
    assert response.json()["data"] == {"authenticated": True}
    assert key not in response.text
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("headers", [{}, {"X-Admin-Key": "invalid"},
                                      {"Authorization": "Bearer invalid"}])
def test_admin_verification_rejects_missing_or_invalid_credentials(client, headers):
    response = client.get("/v1/admin/verify", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["cache-control"] == "private, no-store"


def test_admin_unauthorized(client):
    response = client.post("/v1/admin/ingest", json={"source_id": "nci-us"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_admin_authorized_seed(client):
    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}
    response = client.post("/v1/admin/seed", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["message"] == "Seed routine executed successfully."


def test_categories_endpoint(client):
    response = client.get("/v1/categories")
    assert response.status_code == 200
    cats = response.json()["data"]
    assert len(cats) >= 30
    slugs = [c["category"] for c in cats]
    assert "symptoms" in slugs
    assert "screening" in slugs
    assert "biomarkers" in slugs
    assert "staging" in slugs


def test_countries_endpoint(client):
    response = client.get("/v1/countries")
    assert response.status_code == 200
    countries = response.json()["data"]
    codes = [c["code"] for c in countries]
    assert "US" in codes
    assert "GB" in codes
    assert "AU" in codes
    assert "GLOBAL" in codes
