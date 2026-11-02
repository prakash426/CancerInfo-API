"""
Ingestion Pipeline (Sections 31-35)
"""
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.core.constants import ChangeType, IngestionStatus, LicenseStatus, PublicationStatus
from app.models import (
    Cancer,
    ContentRecord,
    ContentSource,
    ContentVersion,
    IngestionJob,
    Source,
    SourceDocument,
    SourceHealth,
)
from app.normalization.hash import compute_content_hash
from app.normalization.taxonomy import normalize_category
from app.sources.registry import get_adapter


async def run_ingestion_for_source(
    source_id: str,
    db: Session,
    mock_payloads: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Executes an ingestion cycle for the given source_id.
    """
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise ValueError(f"Source '{source_id}' not found in registry.")

    adapter = get_adapter(source_id)
    if not adapter:
        raise ValueError(f"No registered adapter for source '{source_id}'.")

    job = IngestionJob(
        source_id=source.id,
        start_time=datetime.utcnow(),
        status=IngestionStatus.RUNNING.value,
    )
    db.add(job)
    db.commit()

    pages_discovered = 0
    pages_retrieved = 0
    pages_changed = 0
    records_created = 0
    records_updated = 0
    parser_failures = 0
    error_details = []

    try:
        targets = await adapter.discover_urls()
        pages_discovered = len(targets)
        job.pages_discovered = pages_discovered
        db.commit()

        for target in targets:
            url = target["url"]
            c_slug = target["cancer_slug"]
            c_name = target["source_cancer_name"]

            html = None
            etag = None
            last_mod = None

            # Check mock/fixture payload or fetch live
            if mock_payloads and url in mock_payloads:
                html = mock_payloads[url]
            else:
                html, etag, last_mod = await adapter.fetch_url(url)

            if not html:
                # If network is unavailable or mock is provided, don't fail immediately
                continue

            pages_retrieved += 1
            content_hash = compute_content_hash(html)

            # Check existing document
            existing_doc = db.query(SourceDocument).filter(SourceDocument.original_url == url).first()

            if existing_doc and existing_doc.content_hash == content_hash:
                # Unchanged
                existing_doc.last_verified_at = datetime.utcnow()
                db.commit()
                continue

            pages_changed += 1

            try:
                norm_doc = adapter.parse_document(
                    html_content=html,
                    url=url,
                    cancer_slug=c_slug,
                    source_cancer_name=c_name,
                )
            except Exception as pe:
                parser_failures += 1
                error_details.append({"url": url, "error": str(pe)})
                continue

            # Find matching canonical cancer
            cancer = db.query(Cancer).filter(Cancer.slug == c_slug).first()
            if not cancer:
                cancer = Cancer(
                    slug=c_slug,
                    canonical_name=c_name,
                    anatomical_site=c_name,
                )
                db.add(cancer)
                db.flush()

            # Save / update SourceDocument
            if existing_doc:
                doc = existing_doc
                doc.content_hash = content_hash
                doc.last_verified_at = datetime.utcnow()
                doc.title = norm_doc.title
            else:
                doc = SourceDocument(
                    source_id=source.id,
                    original_url=url,
                    canonical_url=norm_doc.canonical_url,
                    title=norm_doc.title,
                    canonical_cancer_id=cancer.id,
                    source_cancer_name=c_name,
                    language=norm_doc.language,
                    country_code=norm_doc.country_code,
                    jurisdiction_scope=norm_doc.jurisdiction_scope,
                    content_hash=content_hash,
                    processing_status="PROCESSED",
                    publication_status=PublicationStatus.REVIEW_REQUIRED.value,
                    license_status=LicenseStatus.REVIEW_REQUIRED.value,
                    quarantine_reason="Newly discovered document pending rights review",
                    third_party_permission_status="UNREVIEWED",
                    redistribution_allowed=False,
                    commercial_redistribution_allowed=False,
                    retrieved_at=datetime.utcnow(),
                    last_verified_at=datetime.utcnow(),
                )
                db.add(doc)
                db.flush()

            # Process sections
            for sec in norm_doc.sections:
                cat = normalize_category(sec.category)

                # Look for existing active ContentRecord for this cancer + category + country
                existing_rec = (
                    db.query(ContentRecord)
                    .filter(
                        ContentRecord.canonical_cancer_id == cancer.id,
                        ContentRecord.category == cat,
                        ContentRecord.country_code == norm_doc.country_code,
                        ContentRecord.active == True,
                    )
                    .first()
                )

                sec_hash = compute_content_hash(sec.content)

                if existing_rec:
                    old_hash = compute_content_hash(existing_rec.content)
                    if old_hash != sec_hash:
                        # Archive old version
                        version_log = ContentVersion(
                            content_record_id=existing_rec.id,
                            version_number=existing_rec.version_number,
                            content=existing_rec.content,
                            change_type=ChangeType.UPDATED.value,
                            change_reason=f"Updated from {source.source_name}",
                            content_hash=old_hash,
                            created_at=datetime.utcnow(),
                        )
                        db.add(version_log)

                        # Update existing
                        existing_rec.content = sec.content
                        existing_rec.version_number += 1
                        existing_rec.updated_at = datetime.utcnow()
                        records_updated += 1
                else:
                    new_rec = ContentRecord(
                        canonical_cancer_id=cancer.id,
                        category=cat,
                        subcategory=sec.subcategory,
                        content=sec.content,
                        content_type=sec.content_type,
                        country_code=norm_doc.country_code,
                        jurisdiction_scope=norm_doc.jurisdiction_scope,
                        language=norm_doc.language,
                        audience=sec.audience,
                        disagreement_status=sec.disagreement_status,
                        version_number=1,
                        active=True,
                    )
                    db.add(new_rec)
                    db.flush()

                    cv = ContentVersion(
                        content_record_id=new_rec.id,
                        version_number=1,
                        content=sec.content,
                        change_type=ChangeType.NEW.value,
                        change_reason="Ingested from source",
                        content_hash=sec_hash,
                    )
                    db.add(cv)

                    # Provenance link
                    cs = ContentSource(
                        content_record_id=new_rec.id,
                        source_id=source.id,
                        source_document_id=doc.id,
                        source_url=url,
                        source_updated_at=norm_doc.source_updated_at or datetime.utcnow(),
                        retrieved_at=datetime.utcnow(),
                        last_verified_at=datetime.utcnow(),
                        quote_snippet=sec.quote_snippet,
                        attribution_text=source.attribution_text,
                    )
                    db.add(cs)
                    records_created += 1

            db.commit()

        # Update source health
        health = db.query(SourceHealth).filter(SourceHealth.source_id == source.id).first()
        if not health:
            health = SourceHealth(source_id=source.id)
            db.add(health)
        health.last_check = datetime.utcnow()
        health.is_reachable = True
        health.last_successful_crawl = datetime.utcnow()
        health.consecutive_failures = 0
        health.alert_status = "HEALTHY"

        job.status = IngestionStatus.SUCCESS.value
        job.end_time = datetime.utcnow()
        job.pages_retrieved = pages_retrieved
        job.pages_changed = pages_changed
        job.records_created = records_created
        job.records_updated = records_updated
        job.parser_failures = parser_failures
        job.error_details = {"errors": error_details}
        db.commit()

    except Exception as e:
        job.status = IngestionStatus.FAILED.value
        job.end_time = datetime.utcnow()
        job.error_details = {"exception": str(e)}
        db.commit()
        raise e
    finally:
        await adapter.close()

    return {
        "job_id": job.id,
        "status": job.status,
        "pages_discovered": pages_discovered,
        "pages_retrieved": pages_retrieved,
        "pages_changed": pages_changed,
        "records_created": records_created,
        "records_updated": records_updated,
        "parser_failures": parser_failures,
    }
