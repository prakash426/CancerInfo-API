"""
Content & Fact-Level Provenance Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.cancer import CancerSummaryOut


class JurisdictionOut(BaseModel):
    scope: str
    country: str
    region: Optional[str] = None


class ProvenanceSourceOut(BaseModel):
    source_id: str
    organization: str
    source_name: str
    url: str
    trust_tier: str
    source_updated_at: Optional[str] = None
    retrieved_at: str
    last_verified_at: str
    license_status: str
    attribution_text: Optional[str] = None
    quote_snippet: Optional[str] = None
    document_title: Optional[str] = None
    publication_status: Optional[str] = None
    reuse_conditions: Optional[str] = None
    commercial_redistribution_allowed: Optional[bool] = None
    rights_evidence_url: Optional[str] = None


class CorroboratingSourceOut(BaseModel):
    source_id: str
    organization: str
    authority_type: str
    trust_tier: str
    country_code: Optional[str] = None
    url: str
    quote: Optional[str] = None
    attribution_text: Optional[str] = None
    document_title: Optional[str] = None
    publication_status: Optional[str] = None
    reuse_conditions: Optional[str] = None
    commercial_redistribution_allowed: Optional[bool] = None
    rights_evidence_url: Optional[str] = None


class ConsensusItemOut(BaseModel):
    id: str
    fact_key: str
    sign: str
    clinical_detail: Optional[str] = None
    corroboration_count: int
    corroborated_by: List[CorroboratingSourceOut] = Field(default_factory=list)


class ConsensusSummaryOut(BaseModel):
    total_items: int
    consensus_status: str
    participating_sources: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class ContentRecordOut(BaseModel):
    id: str
    category: str
    subcategory: Optional[str] = None
    content: str
    content_type: str
    jurisdiction: Optional[JurisdictionOut] = None
    language: str
    audience: str
    disagreement_status: str
    disagreement_notes: Optional[str] = None
    version_number: int
    updated_at: str
    sources: List[ProvenanceSourceOut] = Field(default_factory=list)


class CancerCategoryDataOut(BaseModel):
    cancer: CancerSummaryOut
    category: str
    category_name: str
    category_description: str
    category_type: str
    consensus_summary: Optional[ConsensusSummaryOut] = None
    items: Optional[List[ConsensusItemOut]] = None
    records: List[ContentRecordOut] = Field(default_factory=list)


class ContentVersionOut(BaseModel):
    version_number: int
    content: str
    change_type: str
    change_reason: Optional[str] = None
    content_hash: str
    created_at: str