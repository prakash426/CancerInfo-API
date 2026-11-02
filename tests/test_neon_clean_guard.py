"""Offline guard tests: importing this script never connects to Neon."""
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy.engine import URL

spec = importlib.util.spec_from_file_location(
    "neon_clean_guard", Path(__file__).resolve().parents[1] / "scripts/validate_neon_clean.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def target():
    return URL.create("postgresql", username="neondb_owner", password="offline-test",
                      host=guard.EXPECTED_HOST, database="ciapi_l003_clean",
                      query={"sslmode": "require", "channel_binding": "require"})


def test_approved_neon_clean_target():
    assert guard.checked_url(target().render_as_string(hide_password=False)).database == "ciapi_l003_clean"


@pytest.mark.parametrize("change", [
    {"database": "neondb"}, {"host": "production.neon.tech"},
    {"username": "another_role"}, {"port": 55432},
    {"query": {"sslmode": "disable"}},
    {"query": {"sslmode": "require", "host": "another-host"}},
])
def test_other_targets_refused(change):
    with pytest.raises(ValueError):
        guard.checked_url(target().set(**change).render_as_string(hide_password=False))
