"""
Source Registry Repository
"""
from typing import List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.repositories.publication import PublicEvidence
from app.models import ContentRecord, ContentSource, Source, SourceDocument, SourceHealth


class SourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_sources(
        self,
        country: Optional[str] = None,
        trust_tier: Optional[str] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Source], int]:
        query = self.db.query(Source)

        if active_only:
            query = query.filter(Source.active == True)

        if country:
            query = query.filter(Source.country_code == country.strip().upper())

        if trust_tier:
            query = query.filter(Source.trust_tier.ilike(f"%{trust_tier.strip()}%"))

        total = query.count()
        sources = query.order_by(Source.priority.asc(), Source.organization_name.asc()).offset(skip).limit(limit).all()
        return sources, total

    def get_source_by_id(self, source_id: str) -> Optional[Source]:
        return self.db.query(Source).filter(Source.id == source_id).first()

    def get_source_metrics(self, source_id: str) -> dict:
        evidence = PublicEvidence(self.db)
        doc_count = self.db.query(func.count(SourceDocument.id)).filter(SourceDocument.source_id == source_id, SourceDocument.id.in_(evidence.documents)).scalar() or 0
        record_count = (
            self.db.query(func.count(func.distinct(ContentRecord.id)))
            .join(ContentSource, ContentSource.content_record_id == ContentRecord.id)
            .filter(ContentSource.source_id == source_id, evidence.records())
            .scalar() or 0
        )
        health = (
            self.db.query(SourceHealth)
            .filter(SourceHealth.source_id == source_id)
            .order_by(SourceHealth.last_check.desc())
            .first()
        )
        return {
            "document_count": doc_count,
            "records_supported_count": record_count,
            "health_status": health.alert_status if health else "HEALTHY",
        }
