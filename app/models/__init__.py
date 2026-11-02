"""
SQLAlchemy Models for CancerInfo API
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship
from app.core.constants import PublicationStatus
from app.database.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Source(Base):
    """
    Approved Source in the Source Registry (Section 8)
    """
    __tablename__ = "sources"

    id = Column(String(64), primary_key=True, index=True)  # e.g. "nci-us", "who-global"
    organization_name = Column(String(255), nullable=False)
    source_name = Column(String(255), nullable=False)
    base_url = Column(String(512), nullable=False)
    country_code = Column(String(10), nullable=False, index=True)  # "US", "GB", "AU", "GLOBAL"
    region = Column(String(100), nullable=True)
    source_type = Column(String(100), nullable=False)  # government, international_health_org
    trust_tier = Column(String(100), nullable=False, index=True)
    authority_type = Column(String(100), nullable=False)
    default_language = Column(String(10), default="en")
    supported_languages = Column(JSON, default=lambda: ["en"])

    # Legal & Licensing Fields (Section 8, 42)
    license_type = Column(String(255), nullable=False)
    license_status = Column(String(50), nullable=False, index=True)  # APPROVED, PUBLIC_DOMAIN, etc.
    reuse_allowed = Column(Boolean, default=True)
    full_text_storage_allowed = Column(Boolean, default=True)
    derived_summary_allowed = Column(Boolean, default=True)
    attribution_required = Column(Boolean, default=True)
    attribution_text = Column(String(512), nullable=True)
    reuse_policy_url = Column(String(512), nullable=True)
    terms_url = Column(String(512), nullable=True)
    robots_url = Column(String(512), nullable=True)

    # Operational
    ingestion_method = Column(String(50), default="ADAPTER_HTML")
    crawl_frequency = Column(String(50), default="monthly")
    priority = Column(Integer, default=1)
    active = Column(Boolean, default=True, index=True)
    date_added = Column(DateTime, default=datetime.utcnow)
    last_reviewed = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Relationships
    documents = relationship("SourceDocument", back_populates="source", cascade="all, delete-orphan")
    content_sources = relationship("ContentSource", back_populates="source")
    ingestion_jobs = relationship("IngestionJob", back_populates="source")
    health_records = relationship("SourceHealth", back_populates="source")


class Cancer(Base):
    """
    Canonical Cancer Entity (Section 10)
    """
    __tablename__ = "cancers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    slug = Column(String(128), unique=True, index=True, nullable=False)
    canonical_name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    anatomical_site = Column(String(128), nullable=True, index=True)
    parent_cancer_id = Column(String(36), ForeignKey("cancers.id"), nullable=True)
    taxonomy_codes = Column(JSON, default=dict)  # e.g. {"ICD-O-3": "C50", "MeSH": "D001943"}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    aliases = relationship("CancerAlias", back_populates="cancer", cascade="all, delete-orphan")
    content_records = relationship("ContentRecord", back_populates="cancer", cascade="all, delete-orphan")
    subtypes = relationship("Cancer", backref="parent_cancer", remote_side=[id])


class CancerAlias(Base):
    """
    Aliases, localized names, and synonyms (Section 10)
    """
    __tablename__ = "cancer_aliases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    cancer_id = Column(String(36), ForeignKey("cancers.id"), nullable=False, index=True)
    alias = Column(String(255), nullable=False, index=True)
    language = Column(String(10), default="en", index=True)
    alias_type = Column(String(64), default="common_name")  # common_name, medical_name, abbreviation
    country_code = Column(String(10), nullable=True)
    confidence = Column(Float, default=1.0)
    review_status = Column(String(32), default="APPROVED")

    cancer = relationship("Cancer", back_populates="aliases")

    __table_args__ = (
        Index("ix_alias_lookup", "alias", "language"),
    )


class SourceDocument(Base):
    """
    Raw / Parsed Source Document Metadata (Section 14)
    """
    __tablename__ = "source_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(64), ForeignKey("sources.id"), nullable=False, index=True)
    original_url = Column(String(1024), nullable=False, index=True)
    canonical_url = Column(String(1024), nullable=True)
    title = Column(String(512), nullable=False)
    source_document_type = Column(String(64), default="FACT_SHEET")
    source_cancer_name = Column(String(255), nullable=True)
    canonical_cancer_id = Column(String(36), ForeignKey("cancers.id"), nullable=True, index=True)
    language = Column(String(10), default="en")
    country_code = Column(String(10), nullable=False)
    jurisdiction_scope = Column(String(32), default="COUNTRY")
    published_at = Column(DateTime, nullable=True)
    source_updated_at = Column(DateTime, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    last_verified_at = Column(DateTime, default=datetime.utcnow)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    http_etag = Column(String(128), nullable=True)
    http_last_modified = Column(String(128), nullable=True)
    parser_version = Column(String(32), default="1.0.0")
    processing_status = Column(String(32), default="PROCESSED")
    license_status = Column(String(32), default="REVIEW_REQUIRED")

    # Document-Level Rights & Publication Decision Fields (CIAPI-L004)
    publication_status = Column(
        String(32),
        server_default="REVIEW_REQUIRED",
        default=PublicationStatus.REVIEW_REQUIRED.value,
        nullable=False,
        index=True,
    )
    rights_evidence_url = Column(String(1024), nullable=True)
    rights_reviewed_at = Column(DateTime, nullable=True)
    rights_reviewer = Column(String(255), nullable=True)
    permissible_use = Column(String(255), nullable=True)
    commercial_redistribution_allowed = Column(Boolean, nullable=True)
    redistribution_allowed = Column(Boolean, nullable=True)
    full_text_storage_allowed = Column(Boolean, nullable=True)
    derived_summary_allowed = Column(Boolean, nullable=True)
    attribution_required = Column(Boolean, nullable=True)
    attribution_text = Column(String(512), nullable=True)
    reuse_restrictions = Column(Text, nullable=True)
    quarantine_reason = Column(Text, nullable=True)
    third_party_permission_status = Column(String(64), nullable=True)
    third_party_permission_notes = Column(Text, nullable=True)

    source = relationship("Source", back_populates="documents")
    content_sources = relationship("ContentSource", back_populates="source_document")
    consensus_fact_sources = relationship("ConsensusFactSource", back_populates="source_document")

    def __init__(self, **kwargs):
        kwargs.setdefault("publication_status", PublicationStatus.REVIEW_REQUIRED.value)
        kwargs.setdefault("license_status", "REVIEW_REQUIRED")
        super().__init__(**kwargs)

    def is_publication_eligible(self) -> bool:
        """
        Evaluate fail-closed document publication eligibility.
        Delegates strictly to the consolidated evaluate_publication_eligibility engine.
        """
        from app.core.rights_validation import evaluate_publication_eligibility
        is_eligible, _ = evaluate_publication_eligibility(self)
        return is_eligible

    def assert_publication_eligible(self) -> None:
        """Raise PublicationEligibilityError if document is not eligible."""
        from app.core.rights_validation import assert_publication_eligible
        assert_publication_eligible(self)


class ContentRecord(Base):
    """
    Normalized Cancer Information Record (Sections 11, 12, 13, 16)
    """
    __tablename__ = "content_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    canonical_cancer_id = Column(String(36), ForeignKey("cancers.id"), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)  # e.g. "symptoms", "treatment"
    subcategory = Column(String(64), nullable=True, index=True)
    content = Column(Text, nullable=False)
    content_type = Column(String(64), default="STRUCTURED_EXTRACTION")
    country_code = Column(String(10), nullable=True, index=True)  # "US", "GB", "GLOBAL", or None for universal
    region_code = Column(String(32), nullable=True)
    jurisdiction_scope = Column(String(32), default="COUNTRY", index=True)  # GLOBAL, COUNTRY, etc.
    language = Column(String(10), default="en", index=True)
    audience = Column(String(32), default="patient", index=True)  # patient, health_professionals
    disagreement_status = Column(String(32), default="CONSISTENT")
    disagreement_notes = Column(Text, nullable=True)
    active = Column(Boolean, default=True, index=True)
    version_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cancer = relationship("Cancer", back_populates="content_records")
    sources = relationship("ContentSource", back_populates="content_record", cascade="all, delete-orphan")
    versions = relationship("ContentVersion", back_populates="content_record", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_content_cancer_category", "canonical_cancer_id", "category"),
        Index("ix_content_filter", "canonical_cancer_id", "category", "country_code", "audience"),
    )


class ContentSource(Base):
    """
    Fact-Level Provenance Link between ContentRecord and Source (Section 16, 17)
    """
    __tablename__ = "content_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    content_record_id = Column(String(36), ForeignKey("content_records.id"), nullable=False, index=True)
    source_id = Column(String(64), ForeignKey("sources.id"), nullable=False, index=True)
    source_document_id = Column(String(36), ForeignKey("source_documents.id"), nullable=True, index=True)
    source_url = Column(String(1024), nullable=False)
    source_updated_at = Column(DateTime, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    last_verified_at = Column(DateTime, default=datetime.utcnow)
    quote_snippet = Column(Text, nullable=True)
    attribution_text = Column(String(512), nullable=True)

    content_record = relationship("ContentRecord", back_populates="sources")
    source = relationship("Source", back_populates="content_sources")
    source_document = relationship("SourceDocument", back_populates="content_sources")


class ContentVersion(Base):
    """
    Immutable version history for content records (Section 15)
    """
    __tablename__ = "content_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    content_record_id = Column(String(36), ForeignKey("content_records.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    change_type = Column(String(32), default="NEW")  # NEW, UPDATED, REMOVED_FROM_SOURCE
    change_reason = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    content_record = relationship("ContentRecord", back_populates="versions")


class IngestionJob(Base):
    """
    Ingestion Job Observability (Section 35)
    """
    __tablename__ = "ingestion_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(64), ForeignKey("sources.id"), nullable=False, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(32), default="PENDING")  # PENDING, RUNNING, SUCCESS, FAILED
    pages_discovered = Column(Integer, default=0)
    pages_retrieved = Column(Integer, default=0)
    pages_changed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_rejected = Column(Integer, default=0)
    parser_failures = Column(Integer, default=0)
    error_details = Column(JSON, default=dict)

    source = relationship("Source", back_populates="ingestion_jobs")


class SourceHealth(Base):
    """
    Source Health Monitoring (Section 36)
    """
    __tablename__ = "source_health"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(64), ForeignKey("sources.id"), nullable=False, index=True)
    last_check = Column(DateTime, default=datetime.utcnow)
    is_reachable = Column(Boolean, default=True)
    http_status = Column(Integer, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    last_successful_crawl = Column(DateTime, nullable=True)
    alert_status = Column(String(32), default="HEALTHY")

    source = relationship("Source", back_populates="health_records")


class ConsensusFact(Base):
    """
    Pre-computed, ingestion-time atomic consensus clinical facts (e.g. symptoms, signs, risk factors).
    Decoupled from jurisdiction; corroborated across multiple authoritative health bodies.
    """
    __tablename__ = "consensus_facts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    cancer_id = Column(String(36), ForeignKey("cancers.id"), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)  # e.g. "symptoms", "risk_factors"
    fact_key = Column(String(128), nullable=False, index=True)  # e.g. "sym-breast-lump"
    title = Column(String(512), nullable=False)  # The canonical sign/symptom title
    clinical_detail = Column(Text, nullable=True)  # Clinical nuance, presentation characteristics
    corroboration_count = Column(Integer, default=1)
    display_order = Column(Integer, default=0)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cancer = relationship("Cancer", backref="consensus_facts")
    corroborating_sources = relationship(
        "ConsensusFactSource",
        back_populates="fact",
        cascade="all, delete-orphan",
        order_by="ConsensusFactSource.display_order",
    )

    __table_args__ = (
        Index("ix_consensus_cancer_category", "cancer_id", "category"),
    )


class ConsensusFactSource(Base):
    """
    Direct multi-source citation and provenance link for a ConsensusFact.
    Stores direct quote snippets, primary URLs, attribution text, and authority metadata.
    """
    __tablename__ = "consensus_fact_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    consensus_fact_id = Column(String(36), ForeignKey("consensus_facts.id"), nullable=False, index=True)
    source_id = Column(String(64), ForeignKey("sources.id"), nullable=False, index=True)
    source_url = Column(String(1024), nullable=False)
    quote_snippet = Column(Text, nullable=True)
    attribution_text = Column(String(512), nullable=True)
    country_code = Column(String(10), nullable=True, index=True)  # "US", "GB", "AU", "GLOBAL"
    display_order = Column(Integer, default=0)
    source_document_id = Column(String(36), ForeignKey("source_documents.id"), nullable=True, index=True)
    last_verified_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    fact = relationship("ConsensusFact", back_populates="corroborating_sources")
    source = relationship("Source")
    source_document = relationship("SourceDocument", back_populates="consensus_fact_sources")

