"""CLI: validate the WHO handoff package and write a report."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.who_validate import (load_package, parse_taxonomy_register,
                                        validate_package, write_report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", default=".")
    parser.add_argument("--taxonomy", default="tmp/taxonomy-updated.md")
    parser.add_argument("--live-db", default="cancerinfo.db")
    parser.add_argument("--report", default="who_validation_report.md")
    parser.add_argument("--no-live", action="store_true")
    args = parser.parse_args()

    pkg = load_package(args.package_dir)
    register, _aliases = parse_taxonomy_register(args.taxonomy)
    live = None if args.no_live else args.live_db
    report = validate_package(pkg, register, live_db_path=live)
    write_report(report, args.report)
    print("errors: %d, warnings: %d" % (len(report["errors"]),
                                       len(report["warnings"])))
    for item in report["errors"]:
        print("ERROR: " + item)
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
