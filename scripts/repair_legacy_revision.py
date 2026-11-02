#!/usr/bin/env python3
"""
Explicit operator script to repair legacy revision identifiers in dev/disposable databases.

Remaps '0002_document_rights_and_consensus_linkage' to '0002_document_rights'.
This is an explicit operator action; inspection commands and migrations do NOT perform
automatic repair.
"""
import argparse
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from app.core.config import settings
from app.database.migration_check import repair_legacy_revision, get_current_revision


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Explicitly repair legacy Alembic revision identifiers in dev/disposable databases."
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL") or settings.DATABASE_URL,
        help="Database URL to check and repair (default: DATABASE_URL env var)",
    )
    args = parser.parse_args()

    db_url = args.db_url
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

    print(f"Connecting to database...")
    engine = create_engine(db_url)
    try:
        current_rev = get_current_revision(engine)
        print(f"Current revision before repair: {current_rev}")

        repaired_rev = repair_legacy_revision(engine)
        if repaired_rev:
            print(f"SUCCESS: Repaired legacy revision to '{repaired_rev}'.")
            persisted_rev = get_current_revision(engine)
            print(f"Verified persisted revision on disk: {persisted_rev}")
        else:
            print("No legacy revision repair was needed.")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
