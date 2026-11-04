"""
Search, Coverage, and Health Schemas
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.cancer import CancerSummaryOut
from app.schemas.content import ConsensusItemOut, ContentRecordOut
from app.schemas.common import MetaInfo


class SearchResultItem(BaseModel):
    match_type: str = Field(..., description="'cancer', 'consensus_item', or 'content_record'")
    score: float = Field(default=1.0)
    cancer: CancerSummaryOut
    category: Optional[str] = None
    snippet: Optional[str] = None
    consensus_item: Optional[ConsensusItemOut] = None
    record: Optional[ContentRecordOut] = None
    matched_terms: List[str] = Field(default_factory=list)


class SearchResultsOut(BaseModel):
    query: str
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    results: List[SearchResultItem] = Field(default_factory=list)


class FactsResponseOut(BaseModel):
    data: List[SearchResultItem]
    meta: MetaInfo


class CancerCoverageItem(BaseModel):
    slug: str
    canonical_name: str
    total_records: int
    categories_covered: List[str]
    countries: List[str]
    supporting_sources: List[str]
    last_verified_at: Optional[str] = None


class CoverageResponseOut(BaseModel):
    total_cancers: int
    total_sources: int
    total_content_records: int
    total_source_documents: int
    countries_represented: List[str]
    categories_available: List[str]
    sources_by_trust_tier: Dict[str, int]
    cancers: List[CancerCoverageItem]


class HealthResponseOut(BaseModel):
    status: str
    api_name: str
    api_version: str
    database: str
    timestamp: str
    uptime_seconds: float
    environment: str
    source_registry_count: int
    approved_cancers_count: int
