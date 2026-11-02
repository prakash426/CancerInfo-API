"""Coverage of publishable evidence, distinct from the source registry."""
from typing import Any, Dict, Optional

from app.models import Cancer, ContentRecord
from app.repositories.publication import PublicEvidence


class CoverageRepository:
    def __init__(self, db):
        self.db = db

    def get_coverage(self, cancer_slug: Optional[str] = None) -> Dict[str, Any]:
        evidence = PublicEvidence(self.db)
        cancers_query = self.db.query(Cancer)
        if cancer_slug:
            cancers_query = cancers_query.filter(Cancer.slug == cancer_slug.strip().lower())
        cancers = cancers_query.all()
        records = self.db.query(ContentRecord).filter(
            ContentRecord.canonical_cancer_id.in_([c.id for c in cancers]),
            evidence.records(),
        ).all()
        sources = {link.source_id: link.source for rec in records for link in rec.sources}
        documents = {link.source_document_id for rec in records for link in rec.sources}
        tiers = {}
        for source in sources.values():
            tiers[source.trust_tier] = tiers.get(source.trust_tier, 0) + 1
        coverage = []
        for cancer in cancers:
            visible = [rec for rec in records if rec.canonical_cancer_id == cancer.id]
            links = [link for rec in visible for link in rec.sources]
            verified = max((link.last_verified_at for link in links
                            if link.last_verified_at is not None), default=None)
            coverage.append({
                "slug": cancer.slug,
                "canonical_name": cancer.canonical_name,
                "total_records": len(visible),
                "categories_covered": sorted({rec.category for rec in visible}),
                "countries": sorted({rec.country_code for rec in visible if rec.country_code}),
                "supporting_sources": sorted({link.source.source_name for link in links}),
                "last_verified_at": verified.isoformat() + "Z" if verified else None,
            })
        return {
            "total_cancers": len(cancers),
            "total_sources": len(sources),
            "total_content_records": len(records),
            "total_source_documents": len(documents),
            "countries_represented": sorted({rec.country_code for rec in records if rec.country_code}),
            "categories_available": sorted({rec.category for rec in records}),
            "sources_by_trust_tier": tiers,
            "cancers": coverage,
        }
