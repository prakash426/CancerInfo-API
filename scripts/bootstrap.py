#!/usr/bin/env bash
""":" # Shell wrapper allowing direct execution with python
exec python3 "$0" "$@"
"""
# ==============================================================================
# scripts/bootstrap.py
# CIAPI-L003: Controlled Database Bootstrap CLI
# ==============================================================================
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.database.bootstrap import execute_bootstrap, inspect_database_state
from app.database.session import engine


def mask_database_url(url: str) -> str:
    """Mask credentials in database URL to prevent accidental log leakage."""
    try:
        parsed = urlparse(url)
        if parsed.password:
            masked_netloc = f"{parsed.username}:***@{parsed.hostname}"
            if parsed.port:
                masked_netloc += f":{parsed.port}"
            return url.replace(parsed.netloc, masked_netloc)
        return url
    except Exception:
        return "DATABASE_URL_REDACTED"


def main():
    parser = argparse.ArgumentParser(
        description="Controlled Database Bootstrap CLI for CancerInfo API (CIAPI-L003)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate database readiness without modifying anything:
  python scripts/bootstrap.py --validate-only

  # Execute one-transaction bootstrap against active database:
  python scripts/bootstrap.py
""",
    )
    parser.add_argument(
        "--validate-only",
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Inspect database state and report readiness without creating or mutating any records.",
    )

    args = parser.parse_args()

    masked_url = mask_database_url(settings.DATABASE_URL)
    print("=" * 70)
    print(" CancerInfo API - Controlled Database Bootstrap")
    print("=" * 70)
    print(f"Target Database: {masked_url}")
    print(f"Environment:     {settings.ENVIRONMENT}")
    print(f"Mode:            {'VALIDATE ONLY (DRY-RUN)' if args.dry_run else 'APPLY BOOTSTRAP'}")
    print("-" * 70)

    try:
        result = execute_bootstrap(engine, dry_run=args.dry_run)
    except Exception as exc:
        print(f"\n[BOOTSTRAP ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Status:             {result['status']}")
    print(f"Application Commit: {result['application_commit']}")
    print(f"Dataset Version:    {result['dataset_version']}")

    if result.get("legacy_table_found"):
        print(f"Legacy Table:       cancer_content detected ({result['legacy_rows']} rows, PRESERVED & UNTOUCHED)")
    else:
        print("Legacy Table:       None detected")

    if args.dry_run:
        print("\nPre-Bootstrap Current-Model Row Counts:")
        for table, count in result["pre_counts"].items():
            print(f"  - {table}: {count}")
        print(f"\nPlanned Baseline Records to Create: {result['planned_baseline_records']}")
        print(f"\n{result['message']}")
    else:
        print("\nCreated Records Breakdown:")
        for table, count in result["post_counts"].items():
            created = count - result["pre_counts"].get(table, 0)
            print(f"  - {table}: {count} (created +{created})")
        print(f"\nTotal Current-Model Records Created: {result['total_records_created']}")
        print(f"\n{result['message']}")

    print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
