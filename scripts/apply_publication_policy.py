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
from app.core.constants import ThirdPartyPermissionStatus
from app.core.publication_access import publication_use

FIELDS = {"publication_status", "redistribution_allowed", "commercial_redistribution_allowed",
          "noncommercial_redistribution_allowed", "approved_publication_content_types",
          "rights_reviewed_at", "rights_reviewer", "permissible_use", "attribution_text",
          "reuse_restrictions", "canonical_url", "publication_record_reviews", "full_text_storage_allowed", "derived_summary_allowed", "third_party_permission_status"}


def apply_plan(db, plan):
    required = {"review", "documents", "expected_public_records"}
    if not required <= set(plan) or set(plan) - required - {"expected_noncommercial_public_records"}:
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
            if field == "third_party_permission_status":
                ThirdPartyPermissionStatus(value)
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
    results = {"changed_fields": changed}
    for use, manifest_key, count_key in [
        ("COMMERCIAL", "expected_public_records", "public_records"),
        ("NONCOMMERCIAL", "expected_noncommercial_public_records", "noncommercial_public_records"),
    ]:
        if manifest_key not in plan:
            continue
        token = publication_use.set(use)
        try:
            actual = sorted(r.id for r in db.query(ContentRecord).filter(PublicEvidence(db).records()))
        finally:
            publication_use.reset(token)
        if actual != sorted(plan[manifest_key]):
            raise ValueError(f"{use} public record manifest differs from the reviewed plan")
        results[count_key] = len(actual)
    return results



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
