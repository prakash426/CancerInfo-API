"""CLI: import the WHO handoff package into a target database.

Default is a dry run that rolls back. Pass --apply to commit.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ingestion.who_import import load_decisions, run_import
from app.ingestion.who_validate import load_package

STAGING_URL = "sqlite:////tmp/cancerinfo_staging.db"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=STAGING_URL)
    parser.add_argument("--package-dir", default=".")
    parser.add_argument("--decisions", default="who_rights_decisions.csv")
    parser.add_argument("--manifest-out", default="who_load_manifest.json")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    pkg = load_package(args.package_dir)
    decisions = load_decisions(args.decisions)
    engine = create_engine(args.database_url)
    session = sessionmaker(bind=engine)()
    try:
        manifest = run_import(session, pkg, decisions)
        if args.apply:
            session.commit()
            manifest["committed"] = True
        else:
            session.rollback()
            manifest["committed"] = False
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    with open(args.manifest_out, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    print("documents=%d created=%d updated=%d retired=%d provenance=%d "
          "metadata_docs=%d skipped=%d warnings=%d committed=%s" % (
              manifest["documents"], manifest["created"], manifest["updated"],
              manifest["retired"], manifest["provenance_rows"],
              manifest["metadata_docs"], len(manifest["skipped"]),
              len(manifest["warnings"]), manifest["committed"]))
    for item in manifest["warnings"][:10]:
        print("WARNING: " + item)


if __name__ == "__main__":
    main()
