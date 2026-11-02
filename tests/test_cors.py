"""Regression for the wildcard-plus-credentials finding in the live report."""
import os
import subprocess
import sys

import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_public_api_cors_does_not_grant_browser_credentials(client):
    headers = {"Origin": "https://untrusted.example", "Cookie": "test-only=1"}
    response = client.get("/health", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-credentials" not in response.headers
    # Starlette may reflect an Origin when a request has cookies. Without the
    # credentials header this does not grant credentialed browser access.
    preflight = client.options("/v1/cancers", headers={
        "Origin": headers["Origin"], "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-Admin-Key",
    })
    assert preflight.status_code == 200
    assert "access-control-allow-credentials" not in preflight.headers


@pytest.mark.parametrize("origins", ["*", ["*"], '["*"]', ["https://trusted.example", "*"]])
def test_wildcard_credentials_are_rejected(origins):
    with pytest.raises(ValidationError, match="Credentialed CORS requires explicit origins"):
        Settings(_env_file=None, CORS_ORIGINS=origins, CORS_ALLOW_CREDENTIALS=True)


@pytest.mark.parametrize("origins", ["https://trusted.example", '["https://trusted.example"]',
                                    ["https://trusted.example"]])
def test_explicit_origins_can_enable_credentials(origins):
    cfg = Settings(_env_file=None, CORS_ORIGINS=origins, CORS_ALLOW_CREDENTIALS=True)
    assert cfg.CORS_ORIGINS == ["https://trusted.example"]


def test_explicit_credentialed_origin_does_not_allow_other_sites():
    # Exercise the real app after settings are loaded from the environment.
    code = '''from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    good=client.get('/health',headers={'Origin':'https://trusted.example'})
    assert good.headers['access-control-allow-origin']=='https://trusted.example'
    assert good.headers['access-control-allow-credentials']=='true'
    bad=client.get('/health',headers={'Origin':'https://untrusted.example'})
    assert 'access-control-allow-origin' not in bad.headers
'''
    env = dict(os.environ, ENVIRONMENT="development", DATABASE_URL="sqlite:///:memory:",
               CHECK_MIGRATIONS_ON_STARTUP="false", CORS_ORIGINS='["https://trusted.example"]',
               CORS_ALLOW_CREDENTIALS="true")
    proc = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
