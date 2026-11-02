#!/usr/bin/env bash
""":" # Shell wrapper allowing direct execution with python
exec python3 "$0" "$@"
"""
# ==============================================================================
# scripts/audit_legacy_table.py
# CIAPI-L003: Legacy Table Auditor CLI
# ==============================================================================
import argparse
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.database.legacy_audit import (
    audit_legacy_cancer_content,
    compare_legacy_audits,
)
from app.database.session import engine
from scripts.bootstrap import mask_database_url


def main():
    parser = argparse.ArgumentParser(
        description="Audit legacy cancer_content table integrity (CIAPI-L003)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Capture audit and display summary:
  python scripts/audit_legacy_table.py

  # Save audit JSON to file:
  python scripts/audit_legacy_table.py --output baseline_audit.json

  # Compare current database against saved baseline audit:
  python scripts/audit_legacy_table.py --compare baseline_audit.json
""",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Path to save full audit JSON results.",
    )
    parser.add_argument(
        "--compare",
        "-c",
        type=str,
        default=None,
        help="Path to baseline audit JSON to compare against.",
    )

    args = parser.parse_args()
    masked_url = mask_database_url(settings.DATABASE_URL)

    print("=" * 70)
    print(" CancerInfo API - Legacy cancer_content Table Integrity Audit")
    print("=" * 70)
    print(f"Target Database: {masked_url}")
    print("-" * 70)

    try:
        current_audit = audit_legacy_cancer_content(engine)
    except Exception as exc:
        print(f"\n[AUDIT ERROR] Failed to audit legacy table: {exc}", file=sys.stderr)
        sys.exit(1)

    if not current_audit["exists"]:
        print("Status: TABLE_NOT_FOUND (cancer_content does not exist in target database)")
        sys.exit(1)

    print(f"Status:               TABLE_VERIFIED")
    print(f"Columns Verified:     {current_audit['column_count']} (expected: 22)")
    print(f"Total Rows:           {current_audit['row_count']}")
    print(f"Null Content Hashes:  {current_audit['null_hash_count']}")
    print(f"Indexes Captured:     {len(current_audit['indexes'])}")
    print(f"Deterministic Digest: {current_audit['deterministic_digest']}")

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(current_audit, indent=2))
        print(f"\nFull audit JSON saved to: {out_path}")

    if args.compare:
        compare_path = Path(args.compare)
        if not compare_path.exists():
            print(f"\n[ERROR] Baseline audit file not found: {compare_path}", file=sys.stderr)
            sys.exit(1)

        try:
            baseline_audit = json.loads(compare_path.read_text())
            compare_legacy_audits(baseline_audit, current_audit)
            print("-" * 70)
            print("Audit Comparison: 100% BIT-FOR-BIT MATCH (Zero legacy table mutations)")
        except AssertionError as exc:
            print(f"\n[AUDIT MISMATCH] Integrity violation detected:\n{exc}", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            print(f"\n[ERROR] Failed to compare audits: {exc}", file=sys.stderr)
            sys.exit(1)

    print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
