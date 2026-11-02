"""Explicit migration/bootstrap of one owner-approved disposable Neon database."""
import getpass
import os
from pathlib import Path
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

EXPECTED_HOST = "ep-winter-heart-anc19kzu.c-6.us-east-1.aws.neon.tech"
EXPECTED_DATABASE = "ciapi_l003_clean"


def checked_url(raw):
    try:
        url = make_url(raw)
    except Exception:
        raise ValueError("Invalid connection URL") from None
    if (url.host != EXPECTED_HOST or url.database != EXPECTED_DATABASE
            or url.username != "neondb_owner" or url.port not in (None, 5432)
            or url.drivername not in {"postgres", "postgresql", "postgresql+psycopg2"}):
        raise ValueError("Refused: target does not match the approved clean database")
    if set(url.query) - {"sslmode", "channel_binding"}:
        raise ValueError("Refused: unexpected connection routing/options")
    if url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("Refused: TLS is required")
    return url.set(drivername="postgresql+psycopg2")


def main():
    url = checked_url(getpass.getpass("Paste the direct Neon URL for ciapi_l003_clean (hidden): "))
    for key in list(os.environ):
        if key.startswith("PG"):
            os.environ.pop(key)
    os.environ.update(DATABASE_URL=url.render_as_string(hide_password=False),
                      ENVIRONMENT="production", CHECK_MIGRATIONS_ON_STARTUP="true")
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    engine = create_engine(url, connect_args={"connect_timeout": 15})
    try:
        with engine.connect() as connection:
            identity = connection.execute(text("SELECT current_database(), current_user")).one()
            if tuple(identity) != (EXPECTED_DATABASE, "neondb_owner"):
                raise RuntimeError("Database identity mismatch")
            existing = connection.execute(text(
                "SELECT n.nspname, c.relname FROM pg_class c "
                "JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
                "AND n.nspname NOT LIKE 'pg_toast%' "
                "AND c.relkind IN ('r','p','v','m','S','f')"
            )).all()
            if existing:
                raise RuntimeError("Database is not empty. Stop; do not delete objects or rerun blindly")
        print(f"Verified empty target: {EXPECTED_HOST}/{EXPECTED_DATABASE}")
        print("This will create the migration schema and 191 baseline demo rows in this database only.")
        if input("Type MIGRATE ciapi_l003_clean to proceed: ") != "MIGRATE ciapi_l003_clean":
            print("Cancelled; no database changes made.")
            return 0

        from alembic import command
        from app.database.migration_check import get_alembic_config, set_alembic_url_safe
        from app.database.adoption import verify_schema_parity
        from app.database.bootstrap import execute_bootstrap
        from app.database.manifest import (
            capture_current_model_manifest, compare_current_model_manifests,
            verify_foreign_key_integrity,
        )
        cfg = get_alembic_config()
        set_alembic_url_safe(cfg, url.render_as_string(hide_password=False))
        print("STAGE 1: applying migrations", flush=True)
        command.upgrade(cfg, "head")
        command.check(cfg)
        if verify_schema_parity(engine)["tables_verified"] != 11:
            raise RuntimeError("Unexpected model table count")
        print("MIGRATIONS_OK: 11 model tables; no schema drift")

        print("STAGE 2: explicit bootstrap", flush=True)
        result = execute_bootstrap(engine)
        if result["total_records_created"] != 191:
            raise RuntimeError("Unexpected baseline row count")
        baseline = capture_current_model_manifest(engine)
        try:
            execute_bootstrap(engine)
        except RuntimeError as exc:
            if not str(exc).startswith("Refusing to bootstrap: Current-model database is already populated"):
                raise
        else:
            raise RuntimeError("Repeated bootstrap was not refused")
        compare_current_model_manifests(baseline, capture_current_model_manifest(engine))
        print("BOOTSTRAP_OK: 191 rows; repeated bootstrap refused without mutation")

        print("STAGE 3: two production-configured application starts", flush=True)
        from fastapi.testclient import TestClient
        from app.main import app
        if app.dependency_overrides:
            raise RuntimeError("Unexpected database dependency override")
        for attempt in range(2):
            with TestClient(app) as client:
                health = client.get("/v1/health")
                cancers = client.get("/v1/cancers")
                if health.status_code != 200 or cancers.status_code != 200:
                    raise RuntimeError("API smoke check failed")
                if health.json().get("approved_cancers_count", 0) < 1:
                    raise RuntimeError("Health endpoint did not observe seeded data")
                if "breast-cancer" not in {c["slug"] for c in cancers.json()["data"]}:
                    raise RuntimeError("API did not return expected seeded cancer")
            compare_current_model_manifests(baseline, capture_current_model_manifest(engine))
            print(f"START_{attempt + 1}_OK: endpoints passed; manifest unchanged")
        if verify_foreign_key_integrity(engine)["violations"]:
            raise RuntimeError("Foreign-key integrity failed")
        print(f"Model row counts: {baseline['row_counts']}")
        print(f"Model digest: {baseline['deterministic_digest']}")
        print("NEON CLEAN GATE PASSED. Restore, final CI, and deployment remain separate gates.")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Driver exceptions can contain connection details. Do not print them.
        print(f"STOP: {type(exc).__name__}. Do not rerun or reset the database. Report the last completed stage.")
        raise SystemExit(1) from None
