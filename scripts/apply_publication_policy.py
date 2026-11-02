"""Apply an exact reviewed metadata plan; dry-run and repeat-safe by default."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import SourceDocument, ContentRecord
from app.repositories.publication import PublicEvidence

FIELDS = {"publication_status", "redistribution_allowed", "commercial_redistribution_allowed",
          "noncommercial_redistribution_allowed", "approved_publication_content_types",
          "rights_reviewed_at", "rights_reviewer", "permissible_use", "attribution_text",
          "reuse_restrictions", "canonical_url", "publication_record_reviews", "full_text_storage_allowed", "derived_summary_allowed"}


def apply_plan(db, plan):
    if set(plan) != {"review", "documents", "expected_public_records"}:
        raise ValueError("Invalid plan structure")
    changed = 0
    seen = set()
    for item in plan["documents"]:
        if item["id"] in seen or set(item["updates"]) - FIELDS:
            raise ValueError("Duplicate document or unsupported metadata change")
        seen.add(item["id"])
        doc = db.get(SourceDocument, item["id"])
        if doc is None or doc.source_id != item["source_id"] or doc.original_url != item["original_url"]:
            raise ValueError("Document identity changed; review required")
        if doc.content_hash != item["content_hash"]:
            raise ValueError("Document content changed; review required")
        for field, value in item["updates"].items():
            if field == "rights_reviewed_at":
                value = datetime.fromisoformat(value)
            current = getattr(doc, field)
            before = item["before"][field]
            if field == "rights_reviewed_at" and before is not None:
                before = datetime.fromisoformat(before)
            if current != value:
                if current != before:
                    raise ValueError("Rights decision changed since the plan; review required")
                setattr(doc, field, value)
                changed += 1
    db.flush()
    actual = sorted(r.id for r in db.query(ContentRecord).filter(PublicEvidence(db).records()))
    if actual != sorted(plan["expected_public_records"]):
        raise ValueError("Public record manifest differs from the reviewed plan")
    return {"changed_fields": changed, "public_records": len(actual)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    engine = create_engine(settings.DATABASE_URL)
    try:
        with Session(engine) as db:
            result = apply_plan(db, plan)
            if args.apply:
                db.commit()
            else:
                db.rollback()
            print(json.dumps(dict(result, applied=args.apply)))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
