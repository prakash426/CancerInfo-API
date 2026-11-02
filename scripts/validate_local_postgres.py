"""Interactive, local-only L003 validation. No Neon credentials are accepted."""
import getpass
import os
from pathlib import Path
import shutil
import subprocess
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def main():
    root = Path(__file__).resolve().parent.parent
    for tool in ("pg_dump", "pg_restore"):
        if not shutil.which(tool):
            raise SystemExit(f"Missing {tool}; put PostgreSQL 15 bin on PATH first")
    password = getpass.getpass("Local PostgreSQL password (not Neon): ")
    url = URL.create("postgresql+psycopg2", username="ciapi_test_admin",
                     password=password, host="127.0.0.1", port=55432,
                     database="ciapi_l003_test")
    # No inherited libpq routing or authentication overrides.
    for key in list(os.environ):
        if key.startswith("PG"):
            os.environ.pop(key)
    engine = create_engine(url, connect_args={"connect_timeout": 10})
    try:
        with engine.connect() as conn:
            identity = conn.execute(text(
                "SELECT current_database(), current_user, host(inet_server_addr()), "
                "inet_server_port()"
            )).one()
            if tuple(identity) != ("ciapi_l003_test", "ciapi_test_admin", "127.0.0.1", 55432):
                raise SystemExit(
                    "Unexpected database identity; stopping. "
                    f"Observed database={identity[0]!r}, role={identity[1]!r}, "
                    f"address={identity[2]!r}, port={identity[3]!r}. No tests ran."
                )
    except Exception:
        raise SystemExit("Local connection failed. Check server and local password; no tests ran.") from None
    finally:
        engine.dispose()
    print("Verified local target: ciapi_l003_test at 127.0.0.1:55432", flush=True)
    print("Tests create and remove their own unique databases; the control database is not reset.", flush=True)
    env = os.environ.copy()
    env.update(
        POSTGRES_TEST_URL=url.render_as_string(hide_password=False),
        DATABASE_URL="sqlite:///:memory:", ENVIRONMENT="development",
        CHECK_MIGRATIONS_ON_STARTUP="false", PYTHONDONTWRITEBYTECODE="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"],
        cwd=root, env=env,
    )
    if result.returncode:
        print("L003 LOCAL VALIDATION FAILED. Stop before Neon or deployment.")
    else:
        print("L003 LOCAL VALIDATION PASSED. Neon, CI and deployment are separate gates.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
