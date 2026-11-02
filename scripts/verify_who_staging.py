"""CLI: verify a staged WHO load (counts, citations, coverage, API)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from app.database.session import get_db
from app.main import app
from app.models import (Cancer, ContentRecord, ContentSource, SourceDocument,
                        WhoFactProvenance)

STAGING_URL = "sqlite:////tmp/cancerinfo_staging.db"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=STAGING_URL)
    args = parser.parse_args()

    engine = create_engine(args.database_url,
                           connect_args={"check_same_thread": False})
    session = sessionmaker(bind=engine)()
    failures = []

    def check(label, ok, detail=""):
        print(("PASS " if ok else "FAIL ") + label
              + (" | " + str(detail) if detail else ""))
        if not ok:
            failures.append(label)

    try:
        docs = session.query(SourceDocument).filter(
            SourceDocument.source_id == "who-global").all()
        by_status = {}
        for doc in docs:
            by_status[doc.publication_status] = \
                by_status.get(doc.publication_status, 0) + 1
        check("who documents present", len(docs) > 0, len(docs))
        check("no eligible documents", "ELIGIBLE" not in by_status,
              by_status)

        links = session.query(ContentSource).filter(
            ContentSource.source_id == "who-global").all()
        orphans = [link.id for link in links
                   if link.source_document_id is None or
                   session.get(SourceDocument, link.source_document_id)
                   is None]
        check("citations resolve to documents", not orphans,
              "%d links, %d orphans" % (len(links), len(orphans)))

        from app.models import ContentVersion
        imported_ids = {row.content_record_id for row in
                        session.query(ContentVersion).filter(
                            ContentVersion.change_reason.like(
                                "%who-handoff-v1%")).all()}
        prov_ids = {row.content_record_id for row in
                    session.query(WhoFactProvenance).all()}
        missing = {rid for rid in imported_ids if rid not in prov_ids}
        check("every imported record has provenance", not missing,
              "%d imported, %d provenance rows"
              % (len(imported_ids), len(prov_ids)))

        record_ids = {link.content_record_id for link in links}
        dupes = session.query(
            ContentRecord.canonical_cancer_id, ContentRecord.category,
            ContentRecord.subcategory, ContentRecord.audience,
            func.count(ContentRecord.id)).filter(
                ContentRecord.id.in_(record_ids),
                ContentRecord.active == True).group_by(
                    ContentRecord.canonical_cancer_id,
                    ContentRecord.category, ContentRecord.subcategory,
                    ContentRecord.audience).having(
                        func.count(ContentRecord.id) > 1).all()
        check("no duplicate active identities", not dupes, len(dupes))

        cancers = session.query(Cancer).count()
        check("25 cancers present", cancers == 25, cancers)

        probe = session.query(ContentRecord).join(
            ContentSource,
            ContentSource.content_record_id == ContentRecord.id).filter(
                ContentSource.source_id == "who-global",
                ContentRecord.active == True).first()
        if probe is None:
            print("SKIP api probe | no active WHO records in this load")
        else:
            cancer = session.get(Cancer, probe.canonical_cancer_id)

            def override():
                local = sessionmaker(bind=engine)()
                try:
                    yield local
                finally:
                    local.close()

            app.dependency_overrides[get_db] = override
            try:
                client = TestClient(app)
                resp = client.get("/v1/cancers/%s/%s?source=who-global"
                                  % (cancer.slug, probe.category))
            finally:
                app.dependency_overrides.clear()
            body = resp.json() if resp.status_code == 200 else {}
            items = ((body.get("data") or {}).get("records")
                     if isinstance(body, dict) else None) or []
            statuses = set()
            for item in items:
                for src in item.get("sources", []):
                    if src.get("source_id") == "who-global":
                        statuses.add(src.get("publication_status"))
            check("api serves staged record", resp.status_code == 200
                  and len(items) > 0, resp.status_code)
            check("api exposes publication status", bool(statuses),
                  sorted(str(s) for s in statuses))
    finally:
        session.close()
    print("failures=%d" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
