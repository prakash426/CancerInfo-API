"""
CancerInfo API Constants and Canonical Taxonomies
"""
from enum import Enum
from typing import Dict, List


class TrustTier(str, Enum):
    TIER_1 = "Tier 1 - Primary Authoritative"
    TIER_2 = "Tier 2 - Highly Trusted Scientific / Clinical"
    TIER_3 = "Tier 3 - Reputable Cancer Organizations"
    TIER_4 = "Tier 4 - Supplemental"


class LicenseStatus(str, Enum):
    APPROVED = "APPROVED"
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    ATTRIBUTION_REQUIRED = "ATTRIBUTION_REQUIRED"
    LINK_ONLY = "LINK_ONLY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RESTRICTED = "RESTRICTED"
    REJECTED = "REJECTED"


class PublicationStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    QUARANTINED = "QUARANTINED"
    PERMISSION_PENDING = "PERMISSION_PENDING"
    REJECTED = "REJECTED"


class ThirdPartyPermissionStatus(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REQUIRED_NOT_SUBMITTED = "REQUIRED_NOT_SUBMITTED"
    REQUESTED_AWAITING_RESPONSE = "REQUESTED_AWAITING_RESPONSE"
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    RESTRICTED = "RESTRICTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNREVIEWED = "UNREVIEWED"


class JurisdictionScope(str, Enum):
    GLOBAL = "GLOBAL"
    REGIONAL = "REGIONAL"
    COUNTRY = "COUNTRY"
    STATE_OR_PROVINCE = "STATE_OR_PROVINCE"
    ORGANIZATION_SPECIFIC = "ORGANIZATION_SPECIFIC"


class Audience(str, Enum):
    PATIENT = "patient"
    GENERAL_PUBLIC = "general_public"
    CAREGIVERS = "caregivers"
    HEALTH_PROFESSIONALS = "health_professionals"
    RESEARCHERS = "researchers"
    PUBLIC_HEALTH = "public_health"


class ContentType(str, Enum):
    SOURCE_CONTENT = "SOURCE_CONTENT"
    STRUCTURED_EXTRACTION = "STRUCTURED_EXTRACTION"
    DERIVED_SUMMARY = "DERIVED_SUMMARY"
    TRANSLATION = "TRANSLATION"
    AI_ASSISTED_NORMALIZATION = "AI_ASSISTED_NORMALIZATION"
    MANUALLY_CURATED = "MANUALLY_CURATED"


class DisagreementStatus(str, Enum):
    CONSISTENT = "CONSISTENT"
    JURISDICTIONAL_VARIATION = "JURISDICTIONAL_VARIATION"
    POSSIBLE_CONFLICT = "POSSIBLE_CONFLICT"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class ChangeType(str, Enum):
    NEW = "NEW"
    UPDATED = "UPDATED"
    REMOVED_FROM_SOURCE = "REMOVED_FROM_SOURCE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    PARSER_CHANGED = "PARSER_CHANGED"
    MANUALLY_CORRECTED = "MANUALLY_CORRECTED"


class IngestionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


# Canonical Categories as defined in Section 11
CANONICAL_CATEGORIES: Dict[str, Dict[str, str]] = {
    "overview": {"name": "Overview", "description": "High-level summary, definition, and introduction"},
    "types_and_subtypes": {"name": "Types & Subtypes", "description": "Histological or anatomical subtypes"},
    "symptoms": {"name": "Symptoms", "description": "Patient-reported indications and sensations"},
    "signs": {"name": "Signs", "description": "Clinically observable physical indicators"},
    "causes": {"name": "Causes", "description": "Known direct etiologies and biological mechanisms"},
    "risk_factors": {"name": "Risk Factors", "description": "Lifestyle, genetic, and environmental factors that elevate risk"},
    "prevention": {"name": "Prevention", "description": "Primary prevention measures and lifestyle interventions"},
    "screening": {"name": "Screening", "description": "Population and targeted screening recommendations and guidelines"},
    "early_detection": {"name": "Early Detection", "description": "Early diagnosis strategies and warning signs"},
    "diagnosis": {"name": "Diagnosis", "description": "Diagnostic pathway and clinical confirmation"},
    "diagnostic_tests": {"name": "Diagnostic Tests", "description": "Biopsies, imaging, blood tests, and scans"},
    "grading": {"name": "Grading", "description": "Tumor differentiation grades (G1-G4)"},
    "staging": {"name": "Staging", "description": "TNM staging, Roman numeral stages (0-IV)"},
    "biomarkers": {"name": "Biomarkers", "description": "Molecular markers (e.g. HER2, ER/PR, EGFR, BRAF, PSA)"},
    "genetics": {"name": "Genetics", "description": "Hereditary cancer syndromes and germline/somatic mutations"},
    "treatment": {"name": "Treatment", "description": "General treatment modalities and overarching therapy strategies"},
    "surgery": {"name": "Surgery", "description": "Surgical procedures, resections, and margins"},
    "chemotherapy": {"name": "Chemotherapy", "description": "Systemic cytotoxic anti-cancer medications"},
    "radiation_therapy": {"name": "Radiation Therapy", "description": "External beam, brachytherapy, and proton therapies"},
    "immunotherapy": {"name": "Immunotherapy", "description": "Checkpoint inhibitors, CAR T-cell therapy, vaccines"},
    "targeted_therapy": {"name": "Targeted Therapy", "description": "Small molecules, monoclonal antibodies targeting mutations"},
    "hormone_therapy": {"name": "Hormone Therapy", "description": "Endocrine therapies (e.g. anti-estrogens, anti-androgens)"},
    "stem_cell_transplant": {"name": "Stem Cell Transplant", "description": "Autologous and allogeneic bone marrow/stem cell transplants"},
    "supportive_care": {"name": "Supportive Care", "description": "Management of treatment side effects and supportive care"},
    "side_effects": {"name": "Side Effects", "description": "Adverse events and toxicities associated with therapies"},
    "prognosis": {"name": "Prognosis", "description": "Prognostic outlook and factors influencing outcomes"},
    "survival": {"name": "Survival", "description": "5-year and 10-year relative survival rates and data"},
    "recurrence": {"name": "Recurrence", "description": "Local, regional, and distant cancer recurrence patterns"},
    "follow_up": {"name": "Follow-up", "description": "Surveillance regimens and survivorship monitoring"},
    "palliative_care": {"name": "Palliative Care", "description": "Specialized comfort care and symptom management"},
    "living_with_cancer": {"name": "Living with Cancer", "description": "Quality of life, emotional wellness, diet, and exercise"},
    "caregiver_information": {"name": "Caregiver Information", "description": "Guidance for family members, friends, and caregivers"},
    "childhood_cancer": {"name": "Childhood Cancer", "description": "Pediatric-specific considerations and protocols"},
    "research": {"name": "Research", "description": "Current scientific research initiatives and advancements"},
    "statistics": {"name": "Statistics", "description": "Incidence, prevalence, and mortality statistics by region"},
    "clinical_trials": {"name": "Clinical Trials", "description": "Investigational studies and registry resources"},
    "terminology": {"name": "Terminology", "description": "Medical glossaries, abbreviations, and lay definitions"},
}

CATEGORY_ALIASES: Dict[str, str] = {
    "types": "types_and_subtypes",
    "subtypes": "types_and_subtypes",
    "risk-factors": "risk_factors",
    "early-detection": "early_detection",
    "diagnostic-tests": "diagnostic_tests",
    "radiation": "radiation_therapy",
    "chemo": "chemotherapy",
    "targeted-therapy": "targeted_therapy",
    "hormone": "hormone_therapy",
    "stem-cell-transplant": "stem_cell_transplant",
    "supportive": "supportive_care",
    "side-effects": "side_effects",
    "followup": "follow_up",
    "palliative": "palliative_care",
    "living-with-cancer": "living_with_cancer",
    "caregivers": "caregiver_information",
    "childhood": "childhood_cancer",
    "trials": "clinical_trials",
    "stats": "statistics",
    "genes": "genetics",
}
# Classification of Canonical Categories: Biological (Universal) vs Jurisdictional (Policy-Dependent)
BIOLOGICAL_CATEGORIES: set = {
    "symptoms",
    "signs",
    "causes",
    "risk_factors",
    "prevention",
    "early_detection",
    "diagnosis",
    "diagnostic_tests",
    "grading",
    "staging",
    "biomarkers",
    "genetics",
    "types_and_subtypes",
    "treatment",
    "surgery",
    "chemotherapy",
    "radiation_therapy",
    "immunotherapy",
    "targeted_therapy",
    "hormone_therapy",
    "stem_cell_transplant",
    "supportive_care",
    "side_effects",
    "recurrence",
    "palliative_care",
}

JURISDICTIONAL_CATEGORIES: set = {
    "screening",
    "statistics",
    "follow_up",
    "living_with_cancer",
    "caregiver_information",
    "childhood_cancer",
    "research",
    "clinical_trials",
    "terminology",
    "overview",
    "prognosis",
    "survival",
}


def is_biological_category(category: str) -> bool:
    """Return True if category represents universal biological clinical presentation."""
    cat_clean = category.lower().replace("-", "_")
    return cat_clean in BIOLOGICAL_CATEGORIES


def get_category_nature(category: str) -> str:
    """Return 'biological' or 'jurisdictional' depending on category type."""
    return "biological" if is_biological_category(category) else "jurisdictional"

# Standard Country metadata
COUNTRIES: Dict[str, Dict[str, str]] = {
    "US": {"code": "US", "name": "United States", "region": "Americas", "default_language": "en"},
    "GB": {"code": "GB", "name": "United Kingdom", "region": "Europe", "default_language": "en"},
    "AU": {"code": "AU", "name": "Australia", "region": "Oceania", "default_language": "en"},
    "CA": {"code": "CA", "name": "Canada", "region": "Americas", "default_language": "en"},
    "GLOBAL": {"code": "GLOBAL", "name": "Global / International", "region": "Global", "default_language": "en"},
}

MEDICAL_DISCLAIMER = (
    "CancerInfo API provides public informational data aggregated from authoritative health organizations "
    "for developers and researchers. It does not provide medical diagnosis, personal treatment recommendations, "
    "individualized drug selection or dosage, or replace licensed medical professionals."
)
