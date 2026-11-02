"""Append reviewed excerpts without modifying originals; dry-run by default."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import ContentRecord, ContentSource, ContentVersion
from app.repositories.publication import PublicEvidence
from scripts.apply_publication_policy import apply_plan


def publish(db, plan):
    if set(plan) != {"policy", "excerpts"}:
        raise ValueError("Invalid excerpt plan")
    for item in plan["excerpts"]:
        original = db.get(ContentRecord, item["original_id"])
        if original is None or hashlib.sha256(original.content.encode()).hexdigest() != item["original_sha256"]:
            raise ValueError("Original content changed; review required")
        fields = item["record"]
        if fields["content_type"] != "SOURCE_CONTENT" or set(fields) != {
                "id", "canonical_cancer_id", "category", "subcategory", "content", "content_type",
                "country_code", "region_code", "jurisdiction_scope", "language", "audience", "active"}:
            raise ValueError("Invalid reviewed record")
        link_fields = dict(item["citation"])
        link_fields["retrieved_at"] = datetime.fromisoformat(link_fields["retrieved_at"])
        if set(link_fields) != {"id", "source_id", "source_document_id", "source_url", "retrieved_at", "quote_snippet"}:
            raise ValueError("Invalid citation")
        if not any(l.source_document_id == link_fields["source_document_id"]
                   and l.source_id == link_fields["source_id"] for l in original.sources):
            raise ValueError("Original citation identity changed")
        rec = db.get(ContentRecord, fields["id"])
        if rec:
            if any(getattr(rec, k) != v for k, v in fields.items()):
                raise ValueError("Published excerpt changed; review required")
            link = db.get(ContentSource, link_fields["id"])
            if link is None or link.content_record_id != rec.id or any(getattr(link, k) != v for k,v in link_fields.items()):
                raise ValueError("Published citation changed")
        else:
            rec = ContentRecord(**fields)
            db.add(rec); db.flush()
            db.add(ContentSource(content_record_id=rec.id, **link_fields))
            digest = hashlib.sha256(rec.content.encode()).hexdigest()
            db.add(ContentVersion(content_record_id=rec.id, version_number=1, content=rec.content,
                content_hash=digest, change_type="NEW", change_reason=json.dumps({
                    "document_id": link_fields["source_document_id"], "source_id": link_fields["source_id"],
                    "url": link_fields["source_url"], "content_type": "SOURCE_CONTENT",
                    "original_record_id": original.id, "reason": "Reviewed unchanged publication excerpt"})))
    db.flush()
    result = apply_plan(db, plan["policy"])
    assert not any(link.source_id == "who-global" for rec in db.query(ContentRecord).filter(
        PublicEvidence(db).records()) for link in rec.sources)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    engine = create_engine(settings.DATABASE_URL)
    try:
        with Session(engine) as db:
            result = publish(db, json.loads(args.plan.read_text()))
            if args.apply: db.commit()
            else: db.rollback()
            print(json.dumps(dict(result, applied=args.apply)))
    finally: engine.dispose()


if __name__ == "__main__": main()
