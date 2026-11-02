"""Read-only inventory of the two owner-selected disposable Neon branches."""
import getpass
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def read_url(label):
    raw = getpass.getpass(f"Paste direct URL for {label}, database neondb (hidden): ")
    try:
        url = make_url(raw)
    except Exception:
        raise ValueError("Invalid URL") from None
    if (url.drivername not in {"postgres", "postgresql", "postgresql+psycopg2"}
            or not (url.host or "").endswith(".neon.tech")
            or "-pooler" in url.host or url.database != "neondb"
            or url.port not in (None, 5432)):
        raise ValueError("Expected a direct Neon PostgreSQL URL for neondb")
    if (set(url.query) - {"sslmode", "channel_binding"}
            or url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}):
        raise ValueError("TLS is required; connection overrides are not allowed")
    return url.set(drivername="postgresql+psycopg2")


def inspect_target(label, url):
    engine = create_engine(url, connect_args={
        "connect_timeout": 15, "options": "-c default_transaction_read_only=on",
    })
    try:
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            identity = conn.execute(text(
                "SELECT current_database(), current_user, current_setting('server_version'), "
                "current_setting('transaction_read_only')"
            )).one()
            tables = conn.execute(text(
                "SELECT schemaname, tablename FROM pg_catalog.pg_tables "
                "WHERE schemaname NOT IN ('pg_catalog','information_schema') "
                "AND schemaname NOT LIKE 'pg_toast%' ORDER BY schemaname, tablename"
            )).all()
            print(f"\nSelected label: {label} (confirm this branch in Neon console)")
            print(f"Endpoint: {url.host}")
            print(f"Database: {identity[0]}; role: {identity[1]}")
            print(f"Server version: {identity[2]}; read-only: {identity[3]}")
            print(f"User table count: {len(tables)}")
            quote = engine.dialect.identifier_preparer.quote
            for schema, table in tables:
                count = conn.execute(text(f"SELECT count(*) FROM {quote(schema)}.{quote(table)}")).scalar_one()
                print(f"  {schema}.{table}: {count} rows")
            if ("public", "alembic_version") in [tuple(row) for row in tables]:
                revisions = conn.execute(text("SELECT version_num FROM public.alembic_version")).scalars().all()
                print(f"Alembic revision(s): {revisions}")
            else:
                print("Alembic revision: unversioned (no public.alembic_version)")
    finally:
        engine.dispose()


def main():
    print("READ-ONLY inventory. Select the disposable branches in Neon, never production.")
    for key in list(os.environ):
        if key.startswith("PG"):
            os.environ.pop(key)
    source = read_url("ciapi-l003-upgrade-test")
    destination = read_url("ciapi-l003-restore-test")
    if source.host == destination.host:
        raise ValueError("Both URLs use the same endpoint; select the two different test branches")
    inspect_target("ciapi-l003-upgrade-test", source)
    inspect_target("ciapi-l003-restore-test", destination)
    print("\nINVENTORY ONLY: no migrations, backups, restores or data changes executed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Read-only inventory stopped ({type(exc).__name__}); credentials suppressed. No writes executed.")
        raise SystemExit(1) from None
