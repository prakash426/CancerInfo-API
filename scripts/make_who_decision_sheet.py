"""CLI: build the per URL rights decision sheet from the package."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.who_validate import load_package, make_decision_sheet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", default=".")
    parser.add_argument("--sheet", default="who_rights_decisions.csv")
    args = parser.parse_args()

    pkg = load_package(args.package_dir)
    out = make_decision_sheet(pkg, args.sheet)
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
