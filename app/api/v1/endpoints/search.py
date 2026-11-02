"""
Search Endpoint (Section 22)
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.repositories.search_repo import SearchRepository
from app.schemas.cancer import CancerSummaryOut
from app.schemas.common import MetaInfo, StandardResponse
from app.schemas.content import (
    ConsensusItemOut,
    ContentRecordOut,
    CorroboratingSourceOut,
    JurisdictionOut,
    ProvenanceSourceOut,
)
from app.schemas.search import SearchResultItem, SearchResultsOut

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=StandardResponse[SearchResultsOut])
def search(
    q: str = Query(..., min_length=1, description="Search query string, e.g. 'bowel cancer', 'CRC', 'cough with blood'"),
    category: Optional[str] = Query(None, description="Optional canonical category filter"),
    country: Optional[str] = Query(None, description="Country filter, e.g. 'US', 'GB', 'AU', 'GLOBAL'"),
    source: Optional[str] = Query(None, description="Source ID filter, e.g. 'nci-us', 'who-global'"),
    audience: Optional[str] = Query(None, description="Audience filter, e.g. 'patient'"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Search across canonical cancer names, aliases, and fact-level content records.
    Understands canonical names, abbreviations, and common names.
    """
    repo = SearchRepository(db)
    raw_results = repo.search(
        query_str=q,
        category=category,
        country=country,
        source_id=source,
        audience=audience,
        limit=limit,
    )

    items = []
    for r in raw_results:
        cancer_obj = r["cancer"]
        cancer_out = CancerSummaryOut(
            id=cancer_obj.id,
            slug=cancer_obj.slug,
            canonical_name=cancer_obj.canonical_name,
            anatomical_site=cancer_obj.anatomical_site,
            aliases=[a.alias for a in cancer_obj.aliases],
        )

        consensus_item_out = None
        if r.get("consensus_item"):
            cf = r["consensus_item"]
            corrob_sources = []
            for cs in cf.corroborating_sources:
                s_doc = getattr(cs, "source_document", None)
                corrob_sources.append(
                    CorroboratingSourceOut(
                        source_id=cs.source.id,
                        organization=cs.source.organization_name,
                        authority_type=cs.source.authority_type,
                        trust_tier=cs.source.trust_tier,
                        country_code=cs.country_code or cs.source.country_code,
                        url=cs.source_url,
                        quote=cs.quote_snippet,
                        attribution_text=(s_doc.attribution_text if s_doc and s_doc.attribution_text else None) or cs.attribution_text or cs.source.attribution_text,
                        document_title=s_doc.title if s_doc else None,
                        publication_status=s_doc.publication_status if s_doc else None,
                        reuse_conditions=s_doc.reuse_restrictions if s_doc else None,
                        commercial_redistribution_allowed=s_doc.commercial_redistribution_allowed if s_doc else False,
                        rights_evidence_url=s_doc.rights_evidence_url if s_doc else None,
                    )
                )
            consensus_item_out = ConsensusItemOut(
                id=cf.id,
                fact_key=cf.fact_key,
                sign=cf.title,
                clinical_detail=cf.clinical_detail,
                corroboration_count=cf.corroboration_count,
                corroborated_by=corrob_sources,
            )

        record_out = None
        if r.get("record"):
            rec = r["record"]
            sources_out = []
            for cs in rec.sources:
                s_doc = getattr(cs, "source_document", None)
                sources_out.append(
                    ProvenanceSourceOut(
                        source_id=cs.source.id,
                        organization=cs.source.organization_name,
                        source_name=cs.source.source_name,
                        url=cs.source_url,
                        trust_tier=cs.source.trust_tier,
                        source_updated_at=cs.source_updated_at.isoformat() + "Z" if cs.source_updated_at else None,
                        retrieved_at=cs.retrieved_at.isoformat() + "Z",
                        last_verified_at=cs.last_verified_at.isoformat() + "Z",
                        license_status=s_doc.publication_status if s_doc else cs.source.license_status,
                        attribution_text=(s_doc.attribution_text if s_doc and s_doc.attribution_text else None) or cs.attribution_text or cs.source.attribution_text,
                        quote_snippet=cs.quote_snippet,
                        document_title=s_doc.title if s_doc else None,
                        publication_status=s_doc.publication_status if s_doc else None,
                        reuse_conditions=s_doc.reuse_restrictions if s_doc else None,
                        commercial_redistribution_allowed=s_doc.commercial_redistribution_allowed if s_doc else False,
                        rights_evidence_url=s_doc.rights_evidence_url if s_doc else None,
                    )
                )
            jurisdiction_out = None
            if rec.country_code:
                jurisdiction_out = JurisdictionOut(
                    scope=rec.jurisdiction_scope,
                    country=rec.country_code,
                    region=rec.region_code,
                )
            record_out = ContentRecordOut(
                id=rec.id,
                category=rec.category,
                subcategory=rec.subcategory,
                content=rec.content,
                content_type=rec.content_type,
                jurisdiction=jurisdiction_out,
                language=rec.language,
                audience=rec.audience,
                disagreement_status=rec.disagreement_status,
                disagreement_notes=rec.disagreement_notes,
                version_number=rec.version_number,
                updated_at=rec.updated_at.isoformat() + "Z",
                sources=sources_out,
            )

        items.append(
            SearchResultItem(
                match_type=r["match_type"],
                score=r["score"],
                cancer=cancer_out,
                category=r.get("category"),
                snippet=r.get("snippet"),
                consensus_item=consensus_item_out,
                record=record_out,
                matched_terms=r.get("matched_terms", []),
            )
        )

    filters = {k: v for k, v in {"category": category, "country": country, "source": source, "audience": audience}.items() if v}
    payload = SearchResultsOut(
        query=q,
        filters_applied=filters,
        results=items,
    )

    return StandardResponse(
        data=payload,
        meta=MetaInfo(result_count=len(items)),
    )
