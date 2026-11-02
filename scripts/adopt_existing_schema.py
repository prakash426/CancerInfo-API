#!/usr/bin/env bash
""":" # Shell wrapper allowing direct execution with python
exec python3 "$0" "$@"
"""
# ==============================================================================
# scripts/adopt_existing_schema.py
# CIAPI-L003: Safe Pre-Alembic Schema Adoption CLI
# ==============================================================================
import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.database.adoption import SchemaParityError, adopt_existing_schema
from app.database.session import engine
from scripts.bootstrap import mask_database_url


def main():
    parser = argparse.ArgumentParser(
        description="Safe Pre-Alembic Schema Adoption CLI (CIAPI-L003)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check schema parity without stamping (dry run):
  python scripts/adopt_existing_schema.py --validate-only

  # Adopt verified existing schema by stamping Alembic to head:
  python scripts/adopt_existing_schema.py
""",
    )
    parser.add_argument(
        "--validate-only",
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Verify schema parity across all 11 tables without stamping Alembic version.",
    )

    args = parser.parse_args()

    masked_url = mask_database_url(settings.DATABASE_URL)
    print("=" * 70)
    print(" CancerInfo API - Pre-Alembic Schema Adoption")
    print("=" * 70)
    print(f"Target Database: {masked_url}")
    print(f"Mode:            {'VALIDATE PARITY ONLY' if args.dry_run else 'APPLY ADOPTION (STAMP HEAD)'}")
    print("-" * 70)

    try:
        result = adopt_existing_schema(engine, dry_run=args.dry_run)
    except SchemaParityError as exc:
        print(f"\n[SCHEMA PARITY ERROR]\n{exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\n[ADOPTION ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Status:          {result['status']}")
    print(f"Tables Verified: {result['tables_verified']}")
    print(f"\n{result['message']}")
    print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
