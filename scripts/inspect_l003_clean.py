"""Read-only preflight for the owner's Neon ciapi_l003_clean database."""
import getpass
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def main():
    raw = getpass.getpass("Paste the direct Neon URL for ciapi_l003_clean (hidden): ")
    try:
        url = make_url(raw)
    except Exception:
        raise SystemExit("Invalid connection URL; nothing was changed.") from None
    if url.database != "ciapi_l003_clean":
        raise SystemExit("Refused: database must be ciapi_l003_clean. Nothing was changed.")
    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg2"}:
        raise SystemExit("Refused: expected a PostgreSQL URL.")
    if not (url.host or "").endswith(".neon.tech") or "-pooler" in url.host:
        raise SystemExit("Refused: select the direct Neon connection, with pooling disabled.")
    if url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
        raise SystemExit("Refused: the connection must require TLS.")
    for key in list(os.environ):
        if key.startswith("PG"):
            os.environ.pop(key)
    engine = create_engine(url.set(drivername="postgresql+psycopg2"), connect_args={
        "connect_timeout": 15, "options": "-c default_transaction_read_only=on",
    })
    try:
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            row = connection.execute(text(
                "SELECT current_database(), current_user, "
                "current_setting('server_version'), current_setting('transaction_read_only')"
            )).one()
            tables = connection.execute(text(
                "SELECT schemaname, tablename FROM pg_catalog.pg_tables "
                "WHERE schemaname NOT IN ('pg_catalog', 'information_schema') "
                "AND schemaname NOT LIKE 'pg_toast%' ORDER BY schemaname, tablename"
            )).all()
            print(f"Endpoint: {url.host}")
            print(f"Database: {row[0]}")
            print(f"Role: {row[1]}")
            print(f"PostgreSQL version: {row[2]}")
            print(f"Read-only transaction: {row[3]}")
            print(f"User table count: {len(tables)}")
            for schema, table in tables:
                print(f"  {schema}.{table}")
            print("PREFLIGHT ONLY: no migrations, seeds or restore executed.")
    except Exception:
        raise SystemExit("Read-only preflight failed. Check the selected URL and access; credentials suppressed.") from None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
