"""Explicitly synchronize a selected local SQLite file from PostgreSQL, with backup."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from app.core.config import settings
from app.database.local_sync import sync_local_database


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 10})
    try:
        print(json.dumps(sync_local_database(engine, args.local, args.backup)))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
