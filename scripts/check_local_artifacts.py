"""Reject local databases and private restored artifacts in the Git index.

This is a read-only check. It never removes, relocates, or opens file contents.
"""
from pathlib import PurePosixPath
import re
import subprocess
import sys


def is_local_artifact(name):
    path = PurePosixPath(name)
    if path.parts[0] in {"database", "permissions", "tmp"}:
        return True
    if name.startswith("tests/Competitor-Analysis/"):
        return True
    if re.search(r"\.(db|sqlite|sqlite3)(?:$|[.-])|\.dump$", path.name, re.IGNORECASE):
        return True
    if path.name.startswith(".env") and path.name != ".env.example":
        return True
    if "neon-url" in path.name.lower():
        return True
    return len(path.parts) == 1 and path.name.startswith("who_") and path.suffix in {
        ".csv", ".ndjson", ".json", ".md",
    }


def main():
    result = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True)
    tracked = [name.decode("utf-8") for name in result.stdout.split(b"\0") if name]
    rejected = sorted(name for name in tracked if is_local_artifact(name))
    if rejected:
        print("Local data or private artifacts must not be tracked:")
        for name in rejected:
            print(name)
        print("Preserve the files locally and remove only their Git tracking.")
        return 1
    print("Repository artifact check passed: no tracked local databases or private staging artifacts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
