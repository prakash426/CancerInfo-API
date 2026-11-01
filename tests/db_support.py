"""Local-only disposable PostgreSQL databases. Never reset the supplied database."""
import os
import subprocess
import uuid
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def assert_safe_test_database(db_url):
    url_str = str(db_url)
    if url_str.startswith("postgres://"):
        url_str = url_str.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url_str.startswith("postgresql://"):
        url_str = url_str.replace("postgresql://", "postgresql+psycopg2://", 1)
    url = make_url(url_str)
    if url.get_backend_name() != "postgresql":
        raise RuntimeError("A PostgreSQL test connection is required")
    if url.host not in {"127.0.0.1", "localhost", "postgres"} or url.query:
        raise RuntimeError("Test databases must use an explicit local host without URL overrides")
    if url.database not in {"ciapi_l003_test", "cancerinfo_pytest"}:
        raise RuntimeError("Expected the dedicated L003 test control database")
    return url


@contextmanager
def disposable_postgres(control_url):
    """Only drop the unique database successfully created by this invocation."""
    url = assert_safe_test_database(control_url)
    name = "ciapi_l003_test_" + uuid.uuid4().hex
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    created = False
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE template0'))
        created = True
        yield url.set(database=name).render_as_string(hide_password=False)
    finally:
        try:
            if created:
                with admin.connect() as connection:
                    connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        finally:
            admin.dispose()


def pg_tool(program, url_string, *args):
    """Credentials go through the child environment, never process arguments."""
    url = make_url(url_string)
    env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    env.update(PGHOST=url.host, PGPORT=str(url.port or 5432),
               PGUSER=url.username, PGPASSWORD=url.password or "",
               PGDATABASE=url.database, PGCONNECT_TIMEOUT="10")
    result = subprocess.run([program, *args], env=env, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"{program} failed: {result.stderr}")
    return result.stdout
