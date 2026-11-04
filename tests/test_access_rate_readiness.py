"""Access and availability regressions; no production credentials or corpus writes."""
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest
from starlette.requests import Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from alembic import command

from app.core.config import Settings, settings
from app.core.security import client_address, InMemoryRateLimiter, PostgresRateLimiter, verify_admin_key
from app.core.errors import UnauthorizedError
from app.main import app
from app.database.session import get_db
from app.database.migration_check import get_alembic_config, set_alembic_url_safe
from app.models import RateLimitBucket

TEST_KEY = "ciapi-disposable-production-test-key-2026"


@pytest.mark.parametrize("key", ["", "dev-admin-secret-key", "your-secure-admin-api-key", "x" * 31,
                                  "x" * 32 + " ", "é" * 32, "your-secure-admin-api-key-change-me"])
def test_production_rejects_default_or_invalid_secret(key):
    with pytest.raises(ValueError) as error:
        Settings(_env_file=None, ENVIRONMENT="production", ADMIN_API_KEY=key,
                 DATABASE_URL="postgresql://fixture:private-fixture-password@localhost/db")
    assert "private-fixture-password" not in str(error.value)
    if key:
        assert key not in str(error.value)


def test_production_accepts_explicit_strong_secret():
    config = Settings(_env_file=None, ENVIRONMENT="production", ADMIN_API_KEY=TEST_KEY,
                      DATABASE_URL="postgresql://fixture:fixture@localhost/db")
    assert TEST_KEY not in repr(config)


@pytest.mark.parametrize("value", ["*", "0.0.0.0/0", "::/0", "invalid"])
def test_proxy_configuration_rejects_trust_all(value):
    with pytest.raises(ValueError):
        Settings(_env_file=None, TRUSTED_PROXY_CIDRS=[value])


@pytest.mark.parametrize("limit", [0, -1, 10001])
def test_rate_limit_must_be_bounded_positive(limit):
    with pytest.raises(ValueError):
        Settings(_env_file=None, RATE_LIMIT_PER_MINUTE=limit)


def request(peer, headers):
    return Request({"type": "http", "client": (peer, 123), "headers": headers})


@pytest.mark.parametrize("peer,xff,expected", [
    ("203.0.113.9", "198.51.100.1", "203.0.113.9"),
    ("10.0.0.2", "198.51.100.1, 203.0.113.9", "203.0.113.9"),
    ("10.0.0.2", "198.51.100.1, 10.0.0.3", "198.51.100.1"),
    ("10.0.0.2", "malformed, 10.0.0.3", "10.0.0.2"),
    ("10.0.0.2", "198.51.100.1," * 17, "10.0.0.2"),
    ("::1", "2001:db8::1", "2001:db8::1"),
])
def test_only_trusted_proxy_hops_are_unwrapped(monkeypatch, peer, xff, expected):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", ["10.0.0.0/24", "::1/128"])
    assert client_address(request(peer, [(b"x-forwarded-for", xff.encode())])) == expected


def test_duplicate_forwarding_headers_and_no_trust_fail_closed(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", ["10.0.0.0/24"])
    assert client_address(request("10.0.0.2", [(b"x-forwarded-for", b"198.51.100.1")] * 2)) == "10.0.0.2"
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", [])
    assert client_address(request("10.0.0.2", [(b"x-forwarded-for", b"198.51.100.1")])) == "10.0.0.2"


@pytest.mark.parametrize("render,kind", [(None, None), ("false", "web"), ("true", "pserv")])
def test_render_identity_requires_public_render_runtime(monkeypatch, render, kind):
    for name, value in [("RENDER", render), ("RENDER_SERVICE_TYPE", kind)]:
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match="Render public web service"):
        Settings(_env_file=None, TRUST_RENDER_CF_CONNECTING_IP=True)


def test_render_identity_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_SERVICE_TYPE", "web")
    assert Settings(_env_file=None, TRUST_RENDER_CF_CONNECTING_IP=True).TRUST_RENDER_CF_CONNECTING_IP
    assert not Settings(_env_file=None).TRUST_RENDER_CF_CONNECTING_IP


@pytest.mark.parametrize("value", ["198.51.100.1", "2001:db8::1"])
def test_render_header_takes_precedence_over_forged_forwarding(monkeypatch, value):
    monkeypatch.setattr(settings, "TRUST_RENDER_CF_CONNECTING_IP", True)
    headers = [(b"cf-connecting-ip", value.encode()),
               (b"x-forwarded-for", b"192.0.2.99"), (b"true-client-ip", b"192.0.2.98")]
    assert client_address(request("10.0.0.2", headers)) == value


@pytest.mark.parametrize("headers", [[], [(b"cf-connecting-ip", b"bad")],
    [(b"cf-connecting-ip", b"198.51.100.1, 192.0.2.1")],
    [(b"cf-connecting-ip", b"198.51.100.1")] * 2,
    [(b"cf-connecting-ip", b"a" * 1024)], [(b"cf-connecting-ip", b"fe80::1%eth0")]])
def test_bad_render_header_uses_socket_not_forged_chain(monkeypatch, headers):
    monkeypatch.setattr(settings, "TRUST_RENDER_CF_CONNECTING_IP", True)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", ["10.0.0.0/24"])
    assert client_address(request("10.0.0.2", headers + [
        (b"x-forwarded-for", b"192.0.2.99")])) == "10.0.0.2"


def test_render_header_ignored_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_RENDER_CF_CONNECTING_IP", False)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", [])
    assert client_address(request("10.0.0.2", [
        (b"cf-connecting-ip", b"198.51.100.1")])) == "10.0.0.2"


def test_render_clients_have_independent_quotas(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_RENDER_CF_CONNECTING_IP", True)
    limiter = InMemoryRateLimiter(1)
    def call(ip):
        return limiter.check(client_address(request("10.0.0.2", [
            (b"cf-connecting-ip", ip.encode())])))[0]
    assert call("198.51.100.1")
    assert not call("198.51.100.1")
    assert call("198.51.100.2")


def test_sliding_window_reset_and_idle_cleanup():
    clock = [100.0]
    limiter = InMemoryRateLimiter(2, max_clients=2, clock=lambda: clock[0])
    assert limiter.check("a") == (True, 2, 1, 60)
    clock[0] = 110
    assert limiter.check("a") == (True, 2, 0, 50)
    assert limiter.check("a") == (False, 2, 0, 50)
    assert limiter.check("b")[0]
    assert not limiter.check("c")[0]
    clock[0] = 160
    assert limiter.check("a") == (True, 2, 0, 10)
    clock[0] = 231
    assert limiter.check("c")[0]
    assert set(limiter.clients) == {"c"}


def test_concurrent_memory_limit_is_atomic():
    limiter = InMemoryRateLimiter(7)
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _: limiter.check("same-client")[0], range(40)))
    assert sum(results) == 7


@pytest.mark.parametrize("header", ["X-Admin-Key", "Authorization"])
def test_administrator_credentials_and_uniform_denials(client, monkeypatch, header):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", TEST_KEY)
    value = TEST_KEY if header == "X-Admin-Key" else "Bearer " + TEST_KEY
    # Exercise the auth dependency directly; valid credentials must not seed production.
    assert verify_admin_key(x_admin_key=TEST_KEY if header == "X-Admin-Key" else None,
                            authorization=value if header == "Authorization" else None)
    with pytest.raises(UnauthorizedError):
        verify_admin_key(x_admin_key="invalid", authorization=None)
    responses = [client.post("/v1/admin/seed", headers=h) for h in [{}, {header: "invalid"}]]
    assert [r.status_code for r in responses] == [401, 401]
    assert responses[0].json() == responses[1].json()


def assert_headers(response):
    for name in ["X-Request-ID", "X-Response-Time-MS", "X-Disclaimer", "X-Medical-Disclaimer",
                 "X-CancerInfo-API-Version", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]:
        assert name in response.headers
    assert response.headers["cache-control"] == "private, no-store"
    assert "X-API-Key" in response.headers["vary"]


def test_spoofing_cannot_bypass_limit_and_all_responses_have_headers(client, monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "rate_limiter", InMemoryRateLimiter(1))
    first = client.get("/v1/cancers", headers={"X-Forwarded-For": "198.51.100.1"})
    second = client.get("/v1/cancers", headers={"X-Forwarded-For": "198.51.100.2"})
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["Retry-After"] == second.headers["X-RateLimit-Reset"]
    assert_headers(first)
    assert_headers(second)
    assert client.get("/v1/ready").status_code == 200
    assert client.get("/health").status_code == 200
    # Prefix lookalikes are not exempt.
    assert client.get("/docs-not-a-probe").status_code == 429


def test_limiter_failure_is_closed_and_sanitized(client, monkeypatch, caplog):
    import app.main as main
    limiter = Mock()
    limiter.check.side_effect = RuntimeError("postgresql://private:secret@host/db")
    monkeypatch.setattr(main, "rate_limiter", limiter)
    r = client.get("/v1/cancers")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "RATE_LIMIT_UNAVAILABLE"
    assert_headers(r)
    assert "secret" not in r.text + caplog.text
    assert r.headers["x-request-id"] in caplog.text
    assert client.get("/health").status_code == 200


def test_validation_notfound_and_internal_errors_keep_headers(client, monkeypatch, caplog):
    for path, status in [("/v1/search", 422), ("/missing-route", 404)]:
        r = client.get(path)
        assert r.status_code == status
        assert_headers(r)
    def broken_db():
        raise RuntimeError("private connection failure")
        yield
    monkeypatch.setitem(app.dependency_overrides, get_db, broken_db)
    r = client.get("/v1/cancers")
    assert r.status_code == 500
    assert_headers(r)
    assert "private connection failure" not in r.text + caplog.text
    assert r.headers["x-request-id"] in caplog.text


@pytest.mark.parametrize("phase", ["connection", "registry", "limiter_table", "revision"])
def test_unready_database_returns_503_without_details(client, monkeypatch, caplog, phase):
    db = Mock()
    if phase == "connection":
        db.execute.side_effect = RuntimeError("private-password database failure")
    elif phase == "registry":
        db.query.side_effect = RuntimeError("private-password missing sources")
    elif phase == "limiter_table":
        db.execute.side_effect = [Mock(), RuntimeError("private-password missing rate table")]
    else:
        monkeypatch.setattr(settings, "CHECK_MIGRATIONS_ON_STARTUP", True)
        db.execute.return_value.scalars.return_value.all.return_value = ["outdated"]
    def override():
        yield db
    monkeypatch.setitem(app.dependency_overrides, get_db, override)
    for path in ["/v1/ready", "/v1/health"]:
        r = client.get(path)
        assert r.status_code == 503
        assert r.json()["database"] == "unavailable"
        assert r.json()["source_registry_count"] == 0
        assert "private-password" not in r.text + caplog.text
        assert_headers(r)
    assert db.rollback.called
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/health").status_code == 200


@pytest.fixture
def shared_pg():
    control = os.environ.get("POSTGRES_TEST_URL")
    if not control:
        pytest.skip("Dedicated local PostgreSQL test URL not supplied")
    from db_support import disposable_postgres
    with disposable_postgres(control) as url:
        engine = create_engine(url, pool_size=12, max_overflow=0)
        cfg = get_alembic_config()
        set_alembic_url_safe(cfg, url)
        command.upgrade(cfg, "head")
        try:
            yield engine
        finally:
            engine.dispose()


def test_shared_postgres_limit_survives_worker_restart_and_concurrency(shared_pg):
    workers = [PostgresRateLimiter(shared_pg, 7) for _ in range(3)]
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda i: workers[i % 3].check("198.51.100.4")[0], range(35)))
    assert sum(results) == 7
    assert not PostgresRateLimiter(shared_pg, 7).check("198.51.100.4")[0]
    assert workers[0].check("198.51.100.5")[0]
    with Session(shared_pg) as db:
        rows = db.query(RateLimitBucket).all()
        assert len(rows) == 2
        assert all(len(r.events) <= 7 for r in rows)
        assert all("198.51.100" not in r.id for r in rows)


def test_postgres_window_expiry_and_bounded_cleanup(shared_pg):
    key = hashlib.sha256(b"expired-client").hexdigest()
    with Session(shared_pg) as db:
        now = float(db.execute(text("SELECT EXTRACT(EPOCH FROM clock_timestamp())")).scalar_one())
        db.add(RateLimitBucket(id=key, events=[now-61], expires_at=now-1))
        for i in range(105):
            db.add(RateLimitBucket(id=hashlib.sha256(f"old-{i}".encode()).hexdigest(), events=[], expires_at=0))
        db.commit()
    limiter = PostgresRateLimiter(shared_pg, 1)
    assert limiter.check("expired-client")[0]
    assert not limiter.check("expired-client")[0]
    assert limiter.check("another-client")[0]
    with Session(shared_pg) as db:
        assert db.query(RateLimitBucket).count() == 2


def test_additive_rate_migration_preserves_populated_corpus(test_db_url, alembic_cfg):
    from app.database.manifest import capture_current_model_manifest, compare_current_model_manifests
    from app.ingestion.seed import seed_database
    from app.models import ContentRecord, WhoFactProvenance
    engine = create_engine(test_db_url)
    try:
        command.upgrade(alembic_cfg, "0005_record_publication")
        with Session(engine) as db:
            seed_database(db)
            db.add(WhoFactProvenance(content_record_id=db.query(ContentRecord).first().id, heading_path="Preserved"))
            db.commit()
        before = capture_current_model_manifest(engine)
        with engine.begin() as c:
            c.execute(text("CREATE TABLE cancer_content (id INTEGER PRIMARY KEY, content TEXT)"))
            c.execute(text("INSERT INTO cancer_content VALUES (1, 'preserved legacy')"))
        command.upgrade(alembic_cfg, "head")
        compare_current_model_manifests(before, capture_current_model_manifest(engine))
        command.downgrade(alembic_cfg, "0005_record_publication")
        compare_current_model_manifests(before, capture_current_model_manifest(engine))
        with engine.connect() as c:
            assert c.execute(text("SELECT content FROM cancer_content")).scalar_one() == 'preserved legacy'
    finally:
        engine.dispose()


from test_migrations import test_db_url, alembic_cfg  # noqa: E402,F401


def test_postgres_locked_bucket_wait_is_bounded(shared_pg):
    import time
    from sqlalchemy.exc import OperationalError
    limiter = PostgresRateLimiter(shared_pg, 2)
    limiter.check("locked-client")
    key = hashlib.sha256(b"locked-client").hexdigest()
    with shared_pg.begin() as connection:
        connection.execute(text("SELECT id FROM rate_limit_buckets WHERE id=:id FOR UPDATE"), {"id": key})
        started = time.monotonic()
        with pytest.raises(OperationalError):
            limiter.check("locked-client")
        assert time.monotonic() - started < 4
    assert limiter.check("locked-client")[0]


def test_readiness_detects_schema_damage_after_startup(client, monkeypatch, shared_pg):
    from app.ingestion.seed import seed_database
    with Session(shared_pg) as db:
        seed_database(db)
    def override():
        with Session(shared_pg) as db:
            yield db
    monkeypatch.setitem(app.dependency_overrides, get_db, override)
    monkeypatch.setattr(settings, "CHECK_MIGRATIONS_ON_STARTUP", True)
    assert client.get("/v1/ready").status_code == 200
    with shared_pg.begin() as connection:
        connection.execute(text("DROP TABLE who_fact_provenance"))
    assert client.get("/v1/ready").status_code == 503
    assert client.get("/health").status_code == 200


def test_container_preserves_real_socket_peer():
    from pathlib import Path
    command = Path("Dockerfile").read_text().split("CMD ")[1]
    assert "--no-proxy-headers" in command


def test_production_http_accounting_and_readiness_across_restart(shared_pg):
    import subprocess
    import sys
    from app.ingestion.seed import seed_database
    with Session(shared_pg) as db:
        seed_database(db)
    env = dict(os.environ, ENVIRONMENT="production", ADMIN_API_KEY=TEST_KEY,
               DATABASE_URL=shared_pg.url.render_as_string(hide_password=False),
               RATE_LIMIT_PER_MINUTE="1", TRUSTED_PROXY_CIDRS="[]")
    script = '''
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import PostgresRateLimiter, rate_limiter
assert isinstance(rate_limiter, PostgresRateLimiter)
with TestClient(app) as client:
    assert client.get('/v1/ready').status_code == 200
    r = client.get('/v1/search?q=cancer&source=who-global', headers={'X-Forwarded-For':'198.51.100.1'})
    assert r.status_code == 200 and r.json()['data']['results'] == []
with TestClient(app) as client:
    r = client.get('/v1/cancers', headers={'X-Forwarded-For':'198.51.100.2'})
    assert r.status_code == 429 and r.headers['X-Request-ID']
    assert r.headers['Cache-Control'] == 'private, no-store'
    assert client.get('/v1/health').status_code == 200
from sqlalchemy import text
from app.database.session import engine
with engine.begin() as connection:
    connection.execute(text('DROP TABLE rate_limit_buckets'))

# The last startup must refuse the damaged schema before serving anything.
try:
    with TestClient(app):
        raise AssertionError('Damaged production schema started')
except RuntimeError as exc:
    assert 'schema validation failed' in str(exc)
print('PRODUCTION_ACCOUNTING_READINESS_OK')
'''
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "PRODUCTION_ACCOUNTING_READINESS_OK" in result.stdout


@pytest.mark.parametrize("failure", ["rate", "accounting", "internal"])
def test_allowed_browser_origin_can_read_failure_response(client, monkeypatch, failure):
    import app.main as main
    limiter = Mock()
    if failure == "rate":
        limiter.check.return_value = (False, 120, 0, 27)
        expected = 429
    elif failure == "accounting":
        limiter.check.side_effect = RuntimeError("private dependency failure")
        expected = 503
    else:
        limiter.check.return_value = (True, 120, 119, 60)
        def broken_db():
            raise RuntimeError("private dependency failure")
            yield
        monkeypatch.setitem(app.dependency_overrides, get_db, broken_db)
        expected = 500
    monkeypatch.setattr(main, "rate_limiter", limiter)
    r = client.get("/v1/cancers", headers={"Origin": "https://example.invalid"})
    assert r.status_code == expected
    assert r.headers["Access-Control-Allow-Origin"] == "*"
    assert "access-control-allow-credentials" not in r.headers
    assert "Retry-After" in r.headers["Access-Control-Expose-Headers"]
    assert_headers(r)
    assert "private dependency failure" not in r.text


def test_hung_database_readiness_fails_closed_within_deadline(client, monkeypatch):
    import threading
    import time
    release = threading.Event()

    def hanging_execute(*args, **kwargs):
        release.wait(30)
        raise RuntimeError("late database failure")

    db = Mock()
    db.execute.side_effect = hanging_execute

    def override():
        yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, override)
    try:
        started = time.monotonic()
        r = client.get("/v1/ready")
        elapsed = time.monotonic() - started
        assert r.status_code == 503
        assert r.json()["database"] == "unavailable"
        assert r.json()["source_registry_count"] == 0
        assert r.headers["Retry-After"] == "5"
        assert elapsed < 10
        assert_headers(r)
        assert client.get("/health").json() == {"status": "ok"}
    finally:
        release.set()
    # The hung probe unwinds in its own worker and still cleans up.
    deadline = time.monotonic() + 10
    while not db.rollback.called and time.monotonic() < deadline:
        time.sleep(0.05)
    assert db.rollback.called


def test_concurrent_readiness_probes_stay_bounded_under_hang(monkeypatch):
    import threading
    import time
    from fastapi.testclient import TestClient
    release = threading.Event()
    db = Mock()
    db.execute.side_effect = lambda *args, **kwargs: release.wait(30)

    def override():
        yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, override)

    def probe(_):
        with TestClient(app) as probe_client:
            started = time.monotonic()
            r = probe_client.get("/v1/ready")
            return r.status_code, r.headers.get("Retry-After"), time.monotonic() - started

    try:
        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(probe, range(8)))
        total = time.monotonic() - started
    finally:
        release.set()
    assert [status for status, _, _ in results] == [503] * 8
    assert all(retry == "5" for _, retry, _ in results)
    assert all(elapsed < 10 for _, _, elapsed in results)
    assert total < 12
    assert db.rollback.called


def test_shared_request_evidence_matches_fresh_builds(db_session, public_seed_evidence):
    from app.models import ContentRecord, SourceDocument
    from app.repositories.cancer_repo import CancerRepository
    from app.repositories.content_repo import ContentRepository
    from app.repositories.publication import PublicEvidence
    record = db_session.query(ContentRecord).first()
    assert record is not None
    cancer_id, category = record.canonical_cancer_id, record.category
    content_repo = ContentRepository(db_session)
    cancer_repo = CancerRepository(db_session)
    shared = PublicEvidence(db_session)
    try:
        assert content_repo.get_records(cancer_id, category, evidence=shared)[1] == \
            content_repo.get_records(cancer_id, category)[1]
        assert [f.id for f in content_repo.get_consensus_facts(cancer_id, category, evidence=shared)] == \
            [f.id for f in content_repo.get_consensus_facts(cancer_id, category)]
        assert cancer_repo.get_cancer_sections(cancer_id, evidence=shared) == \
            cancer_repo.get_cancer_sections(cancer_id)
        snapshot_view = content_repo.get_records(cancer_id, category, evidence=shared)[1]
        doc = db_session.query(SourceDocument).first()
        assert doc is not None
        doc.publication_status = "QUARANTINED"
        db_session.flush()
        # The in-request snapshot is stable, while every fresh build re-evaluates.
        assert content_repo.get_records(cancer_id, category, evidence=shared)[1] == snapshot_view
        assert content_repo.get_records(cancer_id, category)[1] == \
            content_repo.get_records(cancer_id, category, evidence=PublicEvidence(db_session))[1]
    finally:
        db_session.rollback()


def test_shared_postgres_readiness_bounded_under_limiter_contention(shared_pg, monkeypatch):
    import threading
    import time
    from fastapi.testclient import TestClient
    from app.database.manifest import capture_current_model_manifest, compare_current_model_manifests
    from app.ingestion.seed import seed_database
    with Session(shared_pg) as db:
        seed_database(db)

    def override():
        with Session(shared_pg) as db:
            yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, override)
    limiter = PostgresRateLimiter(shared_pg, 10000)
    stop = threading.Event()

    def churn(_):
        while not stop.is_set():
            limiter.check("198.51.100.9")

    def probe(_):
        with TestClient(app) as probe_client:
            return probe_client.get("/v1/ready").status_code

    before = capture_current_model_manifest(shared_pg)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=8) as pool:
        churners = [pool.submit(churn, i) for i in range(4)]
        try:
            statuses = list(pool.map(probe, range(12)))
        finally:
            stop.set()
        for churner in churners:
            churner.result(timeout=20)
    elapsed = time.monotonic() - started
    assert statuses == [200] * 12
    assert elapsed < 30
    compare_current_model_manifests(before, capture_current_model_manifest(shared_pg))
