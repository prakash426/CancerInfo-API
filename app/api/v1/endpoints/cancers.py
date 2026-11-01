"""
Cancers and Content Category Endpoints
"""
import math
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.constants import (
    CANONICAL_CATEGORIES,
    get_category_nature,
)
from app.core.errors import CancerNotFoundError, CategoryNotFoundError
from app.database.session import get_db
from app.normalization.taxonomy import normalize_category
from app.repositories.cancer_repo import CancerRepository
from app.repositories.content_repo import ContentRepository
from app.schemas.cancer import (
    CancerAliasOut,
    CancerCategorySectionOut,
    CancerDetailOut,
    CancerSummaryOut,
)
from app.schemas.common import MetaInfo, PaginationMeta, StandardResponse
from app.schemas.content import (
    CancerCategoryDataOut,
    ConsensusItemOut,
    ConsensusSummaryOut,
    ContentRecordOut,
    ContentVersionOut,
    CorroboratingSourceOut,
    JurisdictionOut,
    ProvenanceSourceOut,
)
from app.schemas.source import SourceRegistryOut

router = APIRouter(prefix="/cancers", tags=["Cancers"])


@router.get("", response_model=StandardResponse[List[CancerSummaryOut]])
def list_cancers(
    site: Optional[str] = Query(None, description="Filter by anatomical site, e.g. 'Breast', 'Lung'"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    db: Session = Depends(get_db),
):
    """
    List all canonical cancers with pagination and optional anatomical site filtering.
    """
    repo = CancerRepository(db)
    skip = (page - 1) * limit
    cancers, total = repo.list_cancers(skip=skip, limit=limit, site=site)

    data = [
        CancerSummaryOut(
            id=c.id,
            slug=c.slug,
            canonical_name=c.canonical_name,
            anatomical_site=c.anatomical_site,
            aliases=[a.alias for a in c.aliases],
        )
        for c in cancers
    ]

    total_pages = math.ceil(total / limit) if limit > 0 else 1

    return StandardResponse(
        data=data,
        meta=MetaInfo(result_count=len(data)),
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total_records=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.get("/{cancer}", response_model=StandardResponse[CancerDetailOut])
def get_cancer(
    cancer: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve comprehensive details for a specific cancer.
    Accepts slug, UUID, canonical name, or recognized alias (e.g. 'breast-cancer', 'bowel-cancer', 'CRC').
    """
    cancer_repo = CancerRepository(db)
    cancer_obj = cancer_repo.resolve_cancer(cancer)
    if not cancer_obj:
        raise CancerNotFoundError(cancer)

    sections = cancer_repo.get_cancer_sections(cancer_obj.id)
    available_cats = [s["category"] for s in sections]
    counts_map = {s["category"]: s["count"] for s in sections}

    detail = CancerDetailOut(
        id=cancer_obj.id,
        slug=cancer_obj.slug,
        canonical_name=cancer_obj.canonical_name,
        description=cancer_obj.description,
        anatomical_site=cancer_obj.anatomical_site,
        aliases=[
            CancerAliasOut(
                alias=a.alias,
                language=a.language,
                alias_type=a.alias_type,
                country_code=a.country_code,
                confidence=a.confidence,
            )
            for a in cancer_obj.aliases
        ],
        taxonomy_codes=cancer_obj.taxonomy_codes or {},
        available_categories=available_cats,
        record_counts_by_category=counts_map,
    )

    return StandardResponse(
        data=detail,
        meta=MetaInfo(result_count=1),
    )


@router.get("/{cancer}/sections", response_model=StandardResponse[List[CancerCategorySectionOut]])
def get_cancer_sections(
    cancer: str,
    db: Session = Depends(get_db),
):
    """
    List all knowledge sections/categories available for this cancer with record counts and countries.
    """
    cancer_repo = CancerRepository(db)
    cancer_obj = cancer_repo.resolve_cancer(cancer)
    if not cancer_obj:
        raise CancerNotFoundError(cancer)

    sections_raw = cancer_repo.get_cancer_sections(cancer_obj.id)
    sections_out = []
    for s in sections_raw:
        cat_info = CANONICAL_CATEGORIES.get(s["category"], {"name": s["category"], "description": ""})
        sections_out.append(
            CancerCategorySectionOut(
                category=s["category"],
                name=cat_info["name"],
                description=cat_info["description"],
                record_count=s["count"],
                countries_represented=s["countries"],
            )
        )

    return StandardResponse(
        data=sections_out,
        meta=MetaInfo(result_count=len(sections_out)),
    )


@router.get("/{cancer}/sources", response_model=StandardResponse[List[SourceRegistryOut]])
def get_cancer_sources(
    cancer: str,
    db: Session = Depends(get_db),
):
    """
    List all authoritative sources that have provided verified records for this cancer.
    """
    cancer_repo = CancerRepository(db)
    cancer_obj = cancer_repo.resolve_cancer(cancer)
    if not cancer_obj:
        raise CancerNotFoundError(cancer)

    content_repo = ContentRepository(db)
    sources = content_repo.get_sources_for_cancer(cancer_obj.id)

    data = [
        SourceRegistryOut(
            id=s.id,
            organization_name=s.organization_name,
            source_name=s.source_name,
            base_url=s.base_url,
            country_code=s.country_code,
            region=s.region,
            source_type=s.source_type,
            trust_tier=s.trust_tier,
            authority_type=s.authority_type,
            license_type=s.license_type,
            license_status=s.license_status,
            reuse_allowed=s.reuse_allowed,
            full_text_storage_allowed=s.full_text_storage_allowed,
            attribution_required=s.attribution_required,
            attribution_text=s.attribution_text,
            reuse_policy_url=s.reuse_policy_url,
            crawl_frequency=s.crawl_frequency,
            active=s.active,
            last_reviewed=s.last_reviewed.isoformat() + "Z" if s.last_reviewed else None,
        )
        for s in sources
    ]

    return StandardResponse(
        data=data,
        meta=MetaInfo(result_count=len(data)),
    )


@router.get("/{cancer}/versions", response_model=StandardResponse[List[ContentVersionOut]])
def get_cancer_content_versions(
    cancer: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Historical version audit log for content records of this cancer.
    """
    cancer_repo = CancerRepository(db)
    cancer_obj = cancer_repo.resolve_cancer(cancer)
    if not cancer_obj:
        raise CancerNotFoundError(cancer)

    content_repo = ContentRepository(db)
    versions = content_repo.get_content_versions(cancer_obj.id, limit=limit)

    data = [
        ContentVersionOut(
            version_number=v.version_number,
            content=v.content,
            change_type=v.change_type,
            change_reason=v.change_reason,
            content_hash=v.content_hash,
            created_at=v.created_at.isoformat() + "Z",
        )
        for v in versions
    ]

    return StandardResponse(
        data=data,
        meta=MetaInfo(result_count=len(data)),
    )


@router.get("/{cancer}/{category}", response_model=StandardResponse[CancerCategoryDataOut])
def get_cancer_category_content(
    cancer: str,
    category: str,
    country: Optional[str] = Query(None, description="Country filter: 'US', 'GB', 'AU', 'GLOBAL'"),
    audience: Optional[str] = Query(None, description="Audience filter: 'patient', 'health_professionals', 'general_public'"),
    source: Optional[str] = Query(None, description="Specific source ID, e.g. 'nci-us', 'who-global', 'nhs-uk'"),
    language: Optional[str] = Query("en", description="ISO language code"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retrieve normalized content records with full fact-level provenance for a specific cancer and category.
    Example: `/v1/cancers/breast-cancer/symptoms?country=US`
    """
    cancer_repo = CancerRepository(db)
    cancer_obj = cancer_repo.resolve_cancer(cancer)
    if not cancer_obj:
        raise CancerNotFoundError(cancer)

    norm_category = normalize_category(category)
    if norm_category not in CANONICAL_CATEGORIES:
        raise CategoryNotFoundError(category)

    content_repo = ContentRepository(db)
    cat_nature = get_category_nature(norm_category)
    consensus_facts = content_repo.get_consensus_facts(cancer_obj.id, norm_category)

    items_out: Optional[List[ConsensusItemOut]] = None
    consensus_summary_out: Optional[ConsensusSummaryOut] = None

    if consensus_facts:
        items_out = []
        all_sources = set()
        user_country = country.strip().upper() if country else None

        for cf in consensus_facts:
            corrob_sources = []
            matching_sources = []
            other_sources = []

            for s_link in cf.corroborating_sources:
                s_obj = s_link.source
                s_doc = getattr(s_link, "source_document", None)
                all_sources.add(s_obj.id)
                c_out = CorroboratingSourceOut(
                    source_id=s_obj.id,
                    organization=s_obj.organization_name,
                    authority_type=s_obj.authority_type,
                    trust_tier=s_obj.trust_tier,
                    country_code=s_link.country_code or s_obj.country_code,
                    url=s_link.source_url,
                    quote=s_link.quote_snippet,
                    attribution_text=(s_doc.attribution_text if s_doc and s_doc.attribution_text else None) or s_link.attribution_text or s_obj.attribution_text,
                    document_title=s_doc.title if s_doc else None,
                    publication_status=s_doc.publication_status if s_doc else None,
                    reuse_conditions=s_doc.reuse_restrictions if s_doc else None,
                    commercial_redistribution_allowed=s_doc.commercial_redistribution_allowed if s_doc else False,
                    rights_evidence_url=s_doc.rights_evidence_url if s_doc else None,
                )
                if user_country and (c_out.country_code == user_country or c_out.country_code == "GLOBAL"):
                    matching_sources.append(c_out)
                else:
                    other_sources.append(c_out)

            # Option A with user tag personalization:
            # If user specifies country, prioritize matching country citations; keep all if none match
            if user_country and matching_sources:
                corrob_sources = matching_sources
            else:
                corrob_sources = matching_sources + other_sources

            items_out.append(
                ConsensusItemOut(
                    id=cf.id,
                    fact_key=cf.fact_key,
                    sign=cf.title,
                    clinical_detail=cf.clinical_detail,
                    corroboration_count=cf.corroboration_count,
                    corroborated_by=corrob_sources,
                )
            )

        note_text = None
        if user_country:
            note_text = f"Biological presentations are universal across borders. Corroboration citations personalized for jurisdiction: {user_country}."

        consensus_summary_out = ConsensusSummaryOut(
            total_items=len(items_out),
            consensus_status="VERIFIED_MULTI_AUTHORITY",
            participating_sources=sorted(list(all_sources)),
            note=note_text,
        )

    # Always fetch raw records for full backward compatibility
    records_out: List[ContentRecordOut] = []
    skip = (page - 1) * limit
    records, total = content_repo.get_records(
        cancer_id=cancer_obj.id,
        category=norm_category,
        country=country,
        audience=audience,
        source_id=source,
        language=language,
        skip=skip,
        limit=limit,
    )

    for r in records:
        sources_out = []
        for cs in r.sources:
            s_obj = cs.source
            s_doc = getattr(cs, "source_document", None)
            sources_out.append(
                ProvenanceSourceOut(
                    source_id=s_obj.id,
                    organization=s_obj.organization_name,
                    source_name=s_obj.source_name,
                    url=cs.source_url,
                    trust_tier=s_obj.trust_tier,
                    source_updated_at=cs.source_updated_at.isoformat() + "Z" if cs.source_updated_at else None,
                    retrieved_at=cs.retrieved_at.isoformat() + "Z",
                    last_verified_at=cs.last_verified_at.isoformat() + "Z",
                    license_status=s_doc.publication_status if s_doc else s_obj.license_status,
                    attribution_text=(s_doc.attribution_text if s_doc and s_doc.attribution_text else None) or cs.attribution_text or s_obj.attribution_text,
                    quote_snippet=cs.quote_snippet,
                    document_title=s_doc.title if s_doc else None,
                    publication_status=s_doc.publication_status if s_doc else None,
                    reuse_conditions=s_doc.reuse_restrictions if s_doc else None,
                    commercial_redistribution_allowed=s_doc.commercial_redistribution_allowed if s_doc else False,
                    rights_evidence_url=s_doc.rights_evidence_url if s_doc else None,
                )
            )

        jurisdiction_out = None
        if r.country_code:
            jurisdiction_out = JurisdictionOut(
                scope=r.jurisdiction_scope,
                country=r.country_code,
                region=r.region_code,
            )

        records_out.append(
            ContentRecordOut(
                id=r.id,
                category=r.category,
                subcategory=r.subcategory,
                content=r.content,
                content_type=r.content_type,
                jurisdiction=jurisdiction_out,
                language=r.language,
                audience=r.audience,
                disagreement_status=r.disagreement_status,
                disagreement_notes=r.disagreement_notes,
                version_number=r.version_number,
                updated_at=r.updated_at.isoformat() + "Z",
                sources=sources_out,
            )
        )

    cat_meta = CANONICAL_CATEGORIES[norm_category]
    category_data = CancerCategoryDataOut(
        cancer=CancerSummaryOut(
            id=cancer_obj.id,
            slug=cancer_obj.slug,
            canonical_name=cancer_obj.canonical_name,
            anatomical_site=cancer_obj.anatomical_site,
            aliases=[a.alias for a in cancer_obj.aliases],
        ),
        category=norm_category,
        category_name=cat_meta["name"],
        category_description=cat_meta["description"],
        category_type=cat_nature,
        consensus_summary=consensus_summary_out,
        items=items_out,
        records=records_out,
    )

    result_count = len(items_out) if items_out is not None else len(records_out)
    total_records = len(items_out) if items_out is not None else total
    total_pages = math.ceil(total_records / limit) if limit > 0 else 1

    return StandardResponse(
        data=category_data,
        meta=MetaInfo(result_count=result_count),
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total_records=total_records,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )
