#!/usr/bin/env python3
"""
CIAPI-L004: Controlled Database Transition CLI for Populated L003 Databases

Executes repeat-safe, transactional transition on populated databases:
- Populates document rights decisions from RIGHTS_INVENTORY
- Links consensus citation records to SourceDocument records
- Never reseeds or overwrites existing quotes, attribution, history, or clinical content
- Enforces single atomic transaction with rollback on failure
- Supports --dry-run / --validate-only inspection mode
"""
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.database.session import engine
from app.database.transition import transition_populated_l003_database


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
        description="Controlled Transition CLI for Populated Databases (CIAPI-L004)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate transition readiness without modifying data:
  python scripts/transition_l004.py --dry-run

  # Apply repeat-safe transition in a single atomic transaction:
  python scripts/transition_l004.py
""",
    )
    parser.add_argument(
        "--dry-run",
        "--validate-only",
        dest="dry_run",
        action="store_true",
        help="Inspect database state and report planned changes without mutating records.",
    )
    parser.add_argument(
        "--repair-legacy",
        action="store_true",
        help="Explicitly repair legacy revision identifier in disposable dev database before transition.",
    )

    args = parser.parse_args()

    masked_url = mask_database_url(settings.DATABASE_URL)
    print("=" * 70)
    print(" CancerInfo API - CIAPI-L004 Populated Database Transition")
    print("=" * 70)
    print(f"Target Database: {masked_url}")
    print(f"Environment:     {settings.ENVIRONMENT}")
    print(f"Mode:            {'VALIDATE ONLY (DRY-RUN)' if args.dry_run else 'APPLY TRANSITION'}")
    print("-" * 70)

    if args.repair_legacy:
        from app.database.migration_check import repair_legacy_revision
        repaired = repair_legacy_revision(engine)
        if repaired:
            print(f"[REPAIR] Repaired legacy revision to: {repaired}")
        else:
            print("[REPAIR] No legacy revision repair required.")

    try:
        result = transition_populated_l003_database(engine, dry_run=args.dry_run)
    except Exception as exc:
        print(f"\n[TRANSITION ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Status:                      {result['status']}")
    print(f"Mode:                        {result['mode']}")

    if args.dry_run:
        print(f"Pre-transition Documents:    {result['pre_total_documents']}")
        print(f"Pre-transition Citations:    {result['pre_total_citations']}")
        print(f"Unlinked Citations:          {result['pre_unlinked_citations']}")
        print(f"Documents to Update:         {result['documents_to_update']}")
        print(f"Documents to Create:         {result['documents_to_create']}")
        print(f"Citations to Link:           {result['citations_to_link']}")
        print(f"Citations Already Linked:    {result['citations_already_linked']}")
    else:
        print(f"Documents Updated:           {result['documents_updated']}")
        print(f"Documents Created:           {result['documents_created']}")
        print(f"Citations Linked:            {result['citations_linked']}")
        print(f"Citations Already Linked:    {result['citations_already_linked']}")
        print(f"Post-transition Documents:   {result['post_total_documents']}")
        print(f"Post-transition Citations:   {result['post_total_citations']}")
        print(f"Remaining Unlinked:          {result['remaining_unlinked_citations']}")

    print(f"\nMessage: {result['message']}")
    print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
