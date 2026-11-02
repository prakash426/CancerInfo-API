"""
Document-Level Rights and Publication Decision Inventory (CIAPI-L004)

This module provides the authoritative, machine-readable inventory of document-level
rights decisions for candidate source documents in the CancerInfo API.

Guiding Principles:
1. Source-level metadata or licenses NEVER automatically clear individual documents.
2. Every exact canonical URL must have an explicit, auditable publication decision.
3. Fail-closed: documents lacking exact-url review evidence remain non-publication-eligible.
4. No external rights fabrication: do not assume clearance without explicit evidence.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Set, Union
from sqlalchemy.orm import Session

from app.core.constants import PublicationStatus, ThirdPartyPermissionStatus


@dataclass(frozen=True)
class DocumentRightsDecision:
    url: str
    source_id: str
    source_organization: str
    title: str
    canonical_cancer_slug: str
    country_code: str
    jurisdiction_scope: str
    publication_status: PublicationStatus
    rights_evidence_url: Optional[str]
    rights_reviewed_at: Optional[datetime]
    rights_reviewer: Optional[str]
    permissible_use: Optional[str]
    redistribution_allowed: bool
    commercial_redistribution_allowed: bool
    full_text_storage_allowed: bool
    derived_summary_allowed: bool
    attribution_required: bool
    attribution_text: Optional[str]
    reuse_restrictions: Optional[str]
    quarantine_reason: Optional[str]
    third_party_permission_status: Optional[str]
    third_party_permission_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["publication_status"] = self.publication_status.value
        if self.rights_reviewed_at:
            data["rights_reviewed_at"] = self.rights_reviewed_at.isoformat()
        return data


# Authoritative Document-Level Rights Decisions for All 32 Launch Candidate Documents
RIGHTS_INVENTORY: Dict[str, DocumentRightsDecision] = {
    # --------------------------------------------------------------------------
    # National Cancer Institute (NCI) - 14 candidate URLs
    # Policy: Presumptive U.S. Federal Government work (17 U.S.C. § 105).
    # Decision: REVIEW_REQUIRED fail-closed awaiting exact-page third-party audit.
    # --------------------------------------------------------------------------
    "https://www.cancer.gov/types/breast": DocumentRightsDecision(
        url="https://www.cancer.gov/types/breast",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Breast Cancer Overview - National Cancer Institute",
        canonical_cancer_slug="breast-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="Text created by NCI is in public domain, but exact page review is required to verify absence of proprietary clinical diagrams or external guideline excerpts.",
        quarantine_reason="Awaiting exact-document audit for third-party medical illustrations, copyrighted summaries, or external guideline inclusions. Source-level public domain status does not confer automatic per-document clearance.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/breast/screening": DocumentRightsDecision(
        url="https://www.cancer.gov/types/breast/screening",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Breast Cancer Screening Guidelines - NCI",
        canonical_cancer_slug="breast-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="Guidelines may quote USPSTF or third-party professional society recommendations that carry separate copyright protections.",
        quarantine_reason="Awaiting item-level verification of external guideline text and third-party recommendations.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/breast/symptoms": DocumentRightsDecision(
        url="https://www.cancer.gov/types/breast/symptoms",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Breast Cancer Symptoms - NCI",
        canonical_cancer_slug="breast-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="May contain medical illustration diagrams subject to third-party medical animator licensing.",
        quarantine_reason="Awaiting exact-document audit for embedded illustrations and third-party clinical media.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/breast/treatment": DocumentRightsDecision(
        url="https://www.cancer.gov/types/breast/treatment",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Breast Cancer Treatment Options - NCI",
        canonical_cancer_slug="breast-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="PDQ treatment summaries are written by editorial boards; certain tables and drug descriptions may reference proprietary clinical studies.",
        quarantine_reason="Awaiting exact-document verification of clinical study tables and proprietary drug references.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/cervical/symptoms": DocumentRightsDecision(
        url="https://www.cancer.gov/types/cervical/symptoms",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Cervical Cancer Symptoms - NCI",
        canonical_cancer_slug="cervical-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="Subject to verification of clinical infographics and third-party media.",
        quarantine_reason="Consensus-only citation awaiting exact-page review for third-party media and external citations.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/colorectal": DocumentRightsDecision(
        url="https://www.cancer.gov/types/colorectal",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Colorectal Cancer Overview - NCI",
        canonical_cancer_slug="colorectal-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="Subject to verification of anatomical diagrams and SEER statistical summaries.",
        quarantine_reason="Awaiting exact-document audit for anatomical graphics and proprietary statistics.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/colorectal/symptoms": DocumentRightsDecision(
        url="https://www.cancer.gov/types/colorectal/symptoms",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Colorectal Cancer Symptoms - NCI",
        canonical_cancer_slug="colorectal-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="Subject to verification of clinical symptom lists and patient education media.",
        quarantine_reason="Awaiting exact-document audit for embedded illustrations and third-party media.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/lung": DocumentRightsDecision(
        url="https://www.cancer.gov/types/lung",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Lung Cancer Overview - NCI",
        canonical_cancer_slug="lung-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="Subject to verification of thoracic anatomy illustrations and histological subtype classifications.",
        quarantine_reason="Awaiting exact-document audit for histological images and medical media.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/lung/symptoms": DocumentRightsDecision(
        url="https://www.cancer.gov/types/lung/symptoms",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Lung Cancer Symptoms - NCI",
        canonical_cancer_slug="lung-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="Subject to verification of symptom guides and clinical flowcharts.",
        quarantine_reason="Awaiting exact-document audit for diagnostic flowchart diagrams and external citations.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/pancreatic": DocumentRightsDecision(
        url="https://www.cancer.gov/types/pancreatic",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Pancreatic Cancer Overview - NCI",
        canonical_cancer_slug="pancreatic-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="Subject to verification of endocrine/exocrine medical illustrations.",
        quarantine_reason="Awaiting exact-document audit for medical diagrams and clinical text provenance.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/pancreatic/symptoms": DocumentRightsDecision(
        url="https://www.cancer.gov/types/pancreatic/symptoms",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Pancreatic Cancer Symptoms - NCI",
        canonical_cancer_slug="pancreatic-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="Subject to verification of clinical symptom presentation descriptions.",
        quarantine_reason="Awaiting exact-document audit for third-party clinical contributions.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/prostate": DocumentRightsDecision(
        url="https://www.cancer.gov/types/prostate",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Prostate Cancer Overview - NCI",
        canonical_cancer_slug="prostate-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="Subject to verification of male pelvic anatomy illustrations and grading scale references (Gleason/Grade Groups).",
        quarantine_reason="Awaiting exact-document audit for anatomical illustrations and grading diagrams.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/prostate/symptoms": DocumentRightsDecision(
        url="https://www.cancer.gov/types/prostate/symptoms",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Prostate Cancer Symptoms - NCI",
        canonical_cancer_slug="prostate-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="Subject to verification of patient education presentation descriptions.",
        quarantine_reason="Awaiting exact-document audit for clinical symptom text and media.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.cancer.gov/types/skin/symptoms": DocumentRightsDecision(
        url="https://www.cancer.gov/types/skin/symptoms",
        source_id="nci-us",
        source_organization="National Cancer Institute",
        title="Skin Cancer and Melanoma Symptoms - NCI",
        canonical_cancer_slug="melanoma",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cancer.gov/policies/copyright-reuse",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive U.S. Government work subject to item-level third-party audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: National Cancer Institute (NCI), U.S. National Institutes of Health.",
        reuse_restrictions="ABCDE photographic melanoma guides frequently license clinical photographs from dermatological societies.",
        quarantine_reason="Consensus citation; high risk of third-party clinical photograph copyright in dermatological ABCDE guides.",
        third_party_permission_status="UNREVIEWED",
    ),

    # --------------------------------------------------------------------------
    # National Health Service (NHS UK) - 9 candidate URLs
    # Policy: Open Government Licence v3.0 (OGL v3.0).
    # Decision: REVIEW_REQUIRED fail-closed awaiting exact-page third-party audit.
    # --------------------------------------------------------------------------
    "https://www.nhs.uk/conditions/bowel-cancer-screening/": DocumentRightsDecision(
        url="https://www.nhs.uk/conditions/bowel-cancer-screening/",
        source_id="nhs-uk",
        source_organization="National Health Service",
        title="NHS Bowel Cancer Screening Programme",
        canonical_cancer_slug="colorectal-cancer",
        country_code="GB",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive Open Government Licence v3.0 subject to exact-document verification",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: NHS (National Health Service, United Kingdom). Contains public sector information licensed under the Open Government Licence v3.0.",
        reuse_restrictions="OGL v3.0 excludes third-party materials, departmental logos, and proprietary screening kit instructions.",
        quarantine_reason="Awaiting exact-document verification under OGL v3.0 to confirm absence of proprietary screening kit imagery or third-party guidelines.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.nhs.uk/conditions/bowel-cancer/symptoms/": DocumentRightsDecision(
        url="https://www.nhs.uk/conditions/bowel-cancer/symptoms/",
        source_id="nhs-uk",
        source_organization="National Health Service",
        title="Bowel Cancer Symptoms - NHS",
        canonical_cancer_slug="colorectal-cancer",
        country_code="GB",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive Open Government Licence v3.0 subject to exact-document verification",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: NHS (National Health Service, United Kingdom). Contains public sector information licensed under the Open Government Licence v3.0.",
        reuse_restrictions="OGL v3.0 excludes third-party clinical imagery, case studies, and partner content.",
        quarantine_reason="Awaiting exact-document audit for third-party licensed patient photography and clinical graphics.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.nhs.uk/conditions/breast-cancer/symptoms/": DocumentRightsDecision(
        url="https://www.nhs.uk/conditions/breast-cancer/symptoms/",
        source_id="nhs-uk",
        source_organization="National Health Service",
        title="Breast Cancer Symptoms - NHS",
        canonical_cancer_slug="breast-cancer",
        country_code="GB",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive Open Government Licence v3.0 subject to exact-document verification",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: NHS (National Health Service, United Kingdom). Contains public sector information licensed under the Open Government Licence v3.0.",
        reuse_restrictions="Subject to verification of clinical symptom presentation illustrations.",
        quarantine_reason="Awaiting exact-document audit for clinical symptom media and proprietary partner contributions.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.nhs.uk/conditions/breast-screening-mammogram/": DocumentRightsDecision(
        url="https://www.nhs.uk/conditions/breast-screening-mammogram/",
        source_id="nhs-uk",
        source_organization="National Health Service",
        title="NHS Breast Screening Programme",
        canonical_cancer_slug="breast-cancer",
        country_code="GB",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive Open Government Licence v3.0 subject to exact-document verification",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: NHS (National Health Service, United Kingdom). Contains public sector information licensed under the Open Government Licence v3.0.",
        reuse_restrictions="Subject to verification of screening clinic equipment images and NHS visual identity.",
        quarantine_reason="Awaiting exact-document verification of clinical equipment photos and guideline references.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.nhs.uk/conditions/cervical-cancer/symptoms/": DocumentRightsDecision(
        url="https://www.nhs.uk/conditions/cervical-cancer/symptoms/",
        source_id="nhs-uk",
        source_organization="National Health Service",
        title="Cervical Cancer Symptoms - NHS",
        canonical_cancer_slug="cervical-cancer",
        country_code="GB",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive Open Government Licence v3.0 subject to exact-document verification",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: NHS (National Health Service, United Kingdom). Contains public sector information licensed under the Open Government Licence v3.0.",
        reuse_restrictions="Consensus citation; subject to verification of third-party clinical illustrations.",
        quarantine_reason="Consensus citation awaiting exact-page review for third-party media under OGL v3.0.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.nhs.uk/conditions/lung-cancer/symptoms/": DocumentRightsDecision(
        url="https://www.nhs.uk/conditions/lung-cancer/symptoms/",
        source_id="nhs-uk",
        source_organization="National Health Service",
        title="Lung Cancer Symptoms - NHS",
        canonical_cancer_slug="lung-cancer",
        country_code="GB",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive Open Government Licence v3.0 subject to exact-document verification",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: NHS (National Health Service, United Kingdom). Contains public sector information licensed under the Open Government Licence v3.0.",
        reuse_restrictions="Subject to verification of thoracic symptom graphics.",
        quarantine_reason="Consensus citation awaiting exact-page review for third-party imagery.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.nhs.uk/conditions/melanoma-skin-cancer/symptoms/": DocumentRightsDecision(
        url="https://www.nhs.uk/conditions/melanoma-skin-cancer/symptoms/",
        source_id="nhs-uk",
        source_organization="National Health Service",
        title="Melanoma Skin Cancer Symptoms - NHS",
        canonical_cancer_slug="melanoma",
        country_code="GB",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive Open Government Licence v3.0 subject to exact-document verification",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: NHS (National Health Service, United Kingdom). Contains public sector information licensed under the Open Government Licence v3.0.",
        reuse_restrictions="Melanoma ABCDE photographs on NHS pages are frequently credited to the British Association of Dermatologists (BAD) or clinical photography departments.",
        quarantine_reason="Consensus citation; high probability of third-party clinical dermatological copyright on ABCDE images.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.nhs.uk/conditions/pancreatic-cancer/symptoms/": DocumentRightsDecision(
        url="https://www.nhs.uk/conditions/pancreatic-cancer/symptoms/",
        source_id="nhs-uk",
        source_organization="National Health Service",
        title="Pancreatic Cancer Symptoms - NHS",
        canonical_cancer_slug="pancreatic-cancer",
        country_code="GB",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive Open Government Licence v3.0 subject to exact-document verification",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: NHS (National Health Service, United Kingdom). Contains public sector information licensed under the Open Government Licence v3.0.",
        reuse_restrictions="Subject to verification of clinical presentations.",
        quarantine_reason="Consensus citation awaiting exact-page review for third-party media under OGL v3.0.",
        third_party_permission_status="UNREVIEWED",
    ),
    "https://www.nhs.uk/conditions/prostate-cancer/symptoms/": DocumentRightsDecision(
        url="https://www.nhs.uk/conditions/prostate-cancer/symptoms/",
        source_id="nhs-uk",
        source_organization="National Health Service",
        title="Prostate Cancer Symptoms - NHS",
        canonical_cancer_slug="prostate-cancer",
        country_code="GB",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Presumptive Open Government Licence v3.0 subject to exact-document verification",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: NHS (National Health Service, United Kingdom). Contains public sector information licensed under the Open Government Licence v3.0.",
        reuse_restrictions="Subject to verification of clinical text and partner guidelines.",
        quarantine_reason="Consensus citation awaiting exact-page review for third-party media under OGL v3.0.",
        third_party_permission_status="UNREVIEWED",
    ),

    # --------------------------------------------------------------------------
    # World Health Organization (WHO) - 4 candidate URLs
    # Policy: CC BY-NC-SA 3.0 IGO (Non-Commercial, Share-Alike).
    # Decision: PERMISSION_PENDING / QUARANTINED due to commercial/API restriction.
    # --------------------------------------------------------------------------
    "https://www.who.int/news-room/fact-sheets/detail/breast-cancer": DocumentRightsDecision(
        url="https://www.who.int/news-room/fact-sheets/detail/breast-cancer",
        source_id="who-global",
        source_organization="World Health Organization",
        title="Breast Cancer Fact Sheet - WHO",
        canonical_cancer_slug="breast-cancer",
        country_code="GLOBAL",
        jurisdiction_scope="GLOBAL",
        publication_status=PublicationStatus.PERMISSION_PENDING,
        rights_evidence_url="https://www.who.int/about/policies/publishing/open-access",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Non-commercial research/educational only under CC BY-NC-SA 3.0 IGO",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: World Health Organization (WHO). Licensed under CC BY-NC-SA 3.0 IGO.",
        reuse_restrictions="CC BY-NC-SA 3.0 IGO prohibits commercial use and requires share-alike adaptation licensing. Public/commercial API distribution is not permitted without explicit written agreement from WHO.",
        quarantine_reason="WHO CC BY-NC-SA 3.0 IGO non-commercial restriction and redistribution conditions are unresolved for public/commercial API consumption. A free API cannot be presumed non-commercial. Written permission or commercial waiver required.",
        third_party_permission_status=ThirdPartyPermissionStatus.REQUIRED_NOT_SUBMITTED.value,
        third_party_permission_notes="Commercial waiver or formal written permission from WHO is required for public/commercial API redistribution, but no request has yet been submitted to WHO permissions team.",
    ),
    "https://www.who.int/news-room/fact-sheets/detail/cancer": DocumentRightsDecision(
        url="https://www.who.int/news-room/fact-sheets/detail/cancer",
        source_id="who-global",
        source_organization="World Health Organization",
        title="Cancer Fact Sheet - WHO",
        canonical_cancer_slug="lung-cancer",
        country_code="GLOBAL",
        jurisdiction_scope="GLOBAL",
        publication_status=PublicationStatus.PERMISSION_PENDING,
        rights_evidence_url="https://www.who.int/about/policies/publishing/open-access",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Non-commercial research/educational only under CC BY-NC-SA 3.0 IGO",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: World Health Organization (WHO). Licensed under CC BY-NC-SA 3.0 IGO.",
        reuse_restrictions="Non-commercial restriction applies. Commercial/API distribution forbidden without explicit waiver.",
        quarantine_reason="Consensus citation; WHO CC BY-NC-SA 3.0 IGO non-commercial license restriction prevents public/commercial API redistribution without written permission.",
        third_party_permission_status=ThirdPartyPermissionStatus.REQUIRED_NOT_SUBMITTED.value,
        third_party_permission_notes="Commercial waiver or formal written permission from WHO is required for public/commercial API redistribution, but no request has yet been submitted to WHO permissions team.",
    ),
    "https://www.who.int/news-room/fact-sheets/detail/cervical-cancer": DocumentRightsDecision(
        url="https://www.who.int/news-room/fact-sheets/detail/cervical-cancer",
        source_id="who-global",
        source_organization="World Health Organization",
        title="Cervical Cancer Fact Sheet - WHO",
        canonical_cancer_slug="cervical-cancer",
        country_code="GLOBAL",
        jurisdiction_scope="GLOBAL",
        publication_status=PublicationStatus.PERMISSION_PENDING,
        rights_evidence_url="https://www.who.int/about/policies/publishing/open-access",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Non-commercial research/educational only under CC BY-NC-SA 3.0 IGO",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: World Health Organization (WHO). Licensed under CC BY-NC-SA 3.0 IGO.",
        reuse_restrictions="Non-commercial restriction applies. Commercial/API distribution forbidden without explicit waiver.",
        quarantine_reason="Consensus citation; WHO CC BY-NC-SA 3.0 IGO non-commercial license restriction prevents public/commercial API redistribution without written permission.",
        third_party_permission_status=ThirdPartyPermissionStatus.REQUIRED_NOT_SUBMITTED.value,
        third_party_permission_notes="Commercial waiver or formal written permission from WHO is required for public/commercial API redistribution, but no request has yet been submitted to WHO permissions team.",
    ),
    "https://www.who.int/news-room/fact-sheets/detail/lung-cancer": DocumentRightsDecision(
        url="https://www.who.int/news-room/fact-sheets/detail/lung-cancer",
        source_id="who-global",
        source_organization="World Health Organization",
        title="Lung Cancer Risk Factors - WHO",
        canonical_cancer_slug="lung-cancer",
        country_code="GLOBAL",
        jurisdiction_scope="GLOBAL",
        publication_status=PublicationStatus.PERMISSION_PENDING,
        rights_evidence_url="https://www.who.int/about/policies/publishing/open-access",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Non-commercial research/educational only under CC BY-NC-SA 3.0 IGO",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: World Health Organization (WHO). Licensed under CC BY-NC-SA 3.0 IGO.",
        reuse_restrictions="Non-commercial restriction applies. Commercial/API distribution forbidden without explicit waiver.",
        quarantine_reason="WHO CC BY-NC-SA 3.0 IGO non-commercial restriction prevents public/commercial API redistribution without written permission.",
        third_party_permission_status=ThirdPartyPermissionStatus.REQUIRED_NOT_SUBMITTED.value,
        third_party_permission_notes="Commercial waiver or formal written permission from WHO is required for public/commercial API redistribution, but no request has yet been submitted to WHO permissions team.",
    ),

    # --------------------------------------------------------------------------
    # Cancer Australia - 4 candidate URLs
    # Policy: CC BY 4.0 subject to Australian Crown copyright and third-party exceptions.
    # Decision: REVIEW_REQUIRED fail-closed; blanket label does not clear pages.
    # --------------------------------------------------------------------------
    "https://www.canceraustralia.gov.au/affected-cancer/cancer-types/bowel-cancer/symptoms": DocumentRightsDecision(
        url="https://www.canceraustralia.gov.au/affected-cancer/cancer-types/bowel-cancer/symptoms",
        source_id="cancer-australia",
        source_organization="Cancer Australia",
        title="Bowel Cancer Symptoms - Cancer Australia",
        canonical_cancer_slug="colorectal-cancer",
        country_code="AU",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.canceraustralia.gov.au/copyright",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Pending item-level rights audit; subject to Commonwealth of Australia Crown copyright terms",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: Cancer Australia, Australian Government. Licensed under CC BY 4.0.",
        reuse_restrictions="Blanket CC BY 4.0 source statement excludes third-party material, agency branding, and materials subject to separate Crown copyright conditions.",
        quarantine_reason="Source-level CC BY 4.0 label cannot be used as automatic blanket clearance. Exact documents remain non-publication-eligible until individual page review verifies absence of third-party restrictions or Crown copyright carve-outs.",
        third_party_permission_status="REVIEW_REQUIRED",
    ),
    "https://www.canceraustralia.gov.au/affected-cancer/cancer-types/lung-cancer/symptoms": DocumentRightsDecision(
        url="https://www.canceraustralia.gov.au/affected-cancer/cancer-types/lung-cancer/symptoms",
        source_id="cancer-australia",
        source_organization="Cancer Australia",
        title="Lung Cancer Symptoms - Cancer Australia",
        canonical_cancer_slug="lung-cancer",
        country_code="AU",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.canceraustralia.gov.au/copyright",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Pending item-level rights audit; subject to Commonwealth of Australia Crown copyright terms",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: Cancer Australia, Australian Government. Licensed under CC BY 4.0.",
        reuse_restrictions="Subject to third-party copyright exceptions and Australian Crown copyright conditions.",
        quarantine_reason="Consensus citation; source-level CC BY 4.0 is unverified for this exact document. Item-level audit required under Crown copyright.",
        third_party_permission_status="REVIEW_REQUIRED",
    ),
    "https://www.canceraustralia.gov.au/affected-cancer/cancer-types/melanoma/symptoms": DocumentRightsDecision(
        url="https://www.canceraustralia.gov.au/affected-cancer/cancer-types/melanoma/symptoms",
        source_id="cancer-australia",
        source_organization="Cancer Australia",
        title="Melanoma Symptoms - Cancer Australia",
        canonical_cancer_slug="melanoma",
        country_code="AU",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.canceraustralia.gov.au/copyright",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Pending item-level rights audit; subject to Commonwealth of Australia Crown copyright terms",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: Cancer Australia, Australian Government. Licensed under CC BY 4.0.",
        reuse_restrictions="Melanoma skin presentation guides in Australia often incorporate licensed images from Melanoma Institute Australia or clinical colleges.",
        quarantine_reason="Consensus citation; high probability of third-party clinical copyright on dermatological symptoms and illustrations under Commonwealth Crown copyright and CC BY 4.0 conditions.",
        third_party_permission_status="REVIEW_REQUIRED",
    ),
    "https://www.canceraustralia.gov.au/cancer-types/breast-cancer/screening": DocumentRightsDecision(
        url="https://www.canceraustralia.gov.au/cancer-types/breast-cancer/screening",
        source_id="cancer-australia",
        source_organization="Cancer Australia",
        title="BreastScreen Australia Recommendations",
        canonical_cancer_slug="breast-cancer",
        country_code="AU",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.canceraustralia.gov.au/copyright",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="Pending item-level rights audit; subject to Commonwealth of Australia Crown copyright terms",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: Cancer Australia, Australian Government. Licensed under CC BY 4.0.",
        reuse_restrictions="BreastScreen Australia is a joint Commonwealth and State/Territory program; guidelines may involve multi-jurisdictional copyright.",
        quarantine_reason="Awaiting exact-document verification of multi-jurisdictional program recommendations under Commonwealth Crown copyright and CC BY 4.0 terms.",
        third_party_permission_status="REVIEW_REQUIRED",
    ),

    # --------------------------------------------------------------------------
    # Centers for Disease Control and Prevention (CDC) - 1 candidate URL
    # Policy: Public domain U.S. Federal Government work with third-party exceptions.
    # Decision: REVIEW_REQUIRED fail-closed; CDC policy specifically identifies exceptions.
    # --------------------------------------------------------------------------
    "https://www.cdc.gov/cancer/colorectal/basic_info/screening/": DocumentRightsDecision(
        url="https://www.cdc.gov/cancer/colorectal/basic_info/screening/",
        source_id="cdc-us",
        source_organization="Centers for Disease Control and Prevention",
        title="Colorectal Cancer Screening Recommendations - CDC",
        canonical_cancer_slug="colorectal-cancer",
        country_code="US",
        jurisdiction_scope="COUNTRY",
        publication_status=PublicationStatus.REVIEW_REQUIRED,
        rights_evidence_url="https://www.cdc.gov/other/agencymaterials.html",
        rights_reviewed_at=None,
        rights_reviewer=None,
        permissible_use="U.S. Federal Government public domain subject to exact-document third-party exception audit",
        redistribution_allowed=False,
        commercial_redistribution_allowed=False,
        full_text_storage_allowed=True,
        derived_summary_allowed=True,
        attribution_required=True,
        attribution_text="Source: Centers for Disease Control and Prevention (CDC).",
        reuse_restrictions="CDC website materials frequently incorporate third-party copyrighted text, clinical flowcharts, or non-public-domain graphics that cannot be freely redistributed.",
        quarantine_reason="Item-level review unresolved. CDC specifically identifies third-party and copyrighted material exceptions on its pages. Without item-level evidence confirming the page contains only public domain text, publication remains fail-closed.",
        third_party_permission_status="REVIEW_REQUIRED",
    ),
}


def get_rights_inventory_entry(url: str) -> Optional[DocumentRightsDecision]:
    """Retrieve rights decision for exact URL."""
    return RIGHTS_INVENTORY.get(url)


def list_rights_inventory() -> List[DocumentRightsDecision]:
    """List all candidate document rights records in deterministic URL order."""
    return [RIGHTS_INVENTORY[url] for url in sorted(RIGHTS_INVENTORY.keys())]


def export_rights_audit_report(db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """
    Generates a deterministic rights audit report for all current candidate documents.
    If a database session is provided, enriches records with linked consensus facts,
    quote snippets, and content record provenance.
    """
    from app.models import ConsensusFactSource, ContentSource, SourceDocument

    report: List[Dict[str, Any]] = []

    for entry in list_rights_inventory():
        item = entry.to_dict()
        item["linked_consensus_citations"] = []
        item["linked_content_records"] = []

        if db:
            doc = db.query(SourceDocument).filter(SourceDocument.original_url == entry.url).first()
            if doc:
                item["source_document_id"] = doc.id
                item["db_publication_status"] = doc.publication_status
                item["db_is_eligible"] = doc.is_publication_eligible()

                # Linked consensus citations
                for cfs in db.query(ConsensusFactSource).filter(ConsensusFactSource.source_document_id == doc.id).all():
                    fact = cfs.fact
                    item["linked_consensus_citations"].append({
                        "fact_key": fact.fact_key,
                        "fact_title": fact.title,
                        "quote_snippet": cfs.quote_snippet,
                        "attribution_text": cfs.attribution_text,
                        "country_code": cfs.country_code,
                    })

                # Linked content records
                for cs in db.query(ContentSource).filter(ContentSource.source_document_id == doc.id).all():
                    rec = cs.content_record
                    item["linked_content_records"].append({
                        "content_record_id": rec.id,
                        "category": rec.category,
                        "quote_snippet": cs.quote_snippet,
                        "attribution_text": cs.attribution_text,
                    })

        report.append(item)

    return report


def audit_candidate_acceptance(
    records=None,
    db: Optional[Session] = None,
    owner_corpus_decision: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deterministic acceptance-validation audit for CIAPI-L004 candidate documents.
    Inspects all candidate documents and reports exact status across:
    - rights evidence URL
    - review date (rights_reviewed_at)
    - decision owner (rights_reviewer)
    - permissible-use determination
    - attribution decision
    - publication decision
    - third-party permission status
    - actual fail-closed publication eligibility evaluation
    - explicit owner-approved corpus decision (supplied by repository owner Prakash)

    Truthfully separates Engineering Implementation status from L004 Acceptance status.
    Requires an explicit owner-approved corpus decision supplied by repository owner (Prakash).
    Until Prakash supplies that decision, reports it as PENDING. Never claims cross-source
    approval based only on document count.
    Distinguishes:
    - Candidate documents (32 canonical URLs)
    - Excluded / untracked documents (non-candidate documents present in database)
    - Owner-approved eligible corpus (documents actually validated as publication-eligible)
    - Unresolved candidate decisions (awaiting item-level review or owner sign-off)
    - Unresolved permission decisions (both unsubmitted and submitted-awaiting-response)
    - Excluded / quarantined documents (quarantined or pending permissions)
    """
    from app.core.rights_validation import evaluate_publication_eligibility

    inv_urls = set(RIGHTS_INVENTORY.keys())
    excluded_untracked_documents: List[str] = []

    if records is None:
        if db is not None:
            from app.models import SourceDocument
            db_docs = db.query(SourceDocument).all()
            candidate_docs = []
            for d in db_docs:
                doc_url = getattr(d, "original_url", getattr(d, "url", None))
                if doc_url in inv_urls:
                    candidate_docs.append(d)
                else:
                    excluded_untracked_documents.append(doc_url)
            records = candidate_docs if candidate_docs else list_rights_inventory()
        else:
            records = list_rights_inventory()

    total = len(records)
    with_rights_evidence = 0
    with_review_date = 0
    with_decision_owner = 0
    with_permissible_use = 0
    with_attribution_decision = 0
    with_publication_decision = 0
    eligible_count = 0
    review_required_count = 0
    permission_pending_count = 0
    permission_requests_submitted = 0
    permission_required_not_submitted = 0

    owner_approved_eligible_corpus: List[str] = []
    unresolved_candidate_decisions: List[str] = []
    unresolved_permission_decisions: List[str] = []
    excluded_quarantined_documents: List[str] = []
    inconsistent_eligible_records: List[str] = []

    missing_fields_by_url: Dict[str, List[str]] = {}
    documents_missing_review_date: List[str] = []
    documents_missing_decision_owner: List[str] = []
    eligibility_deficiencies_by_url: Dict[str, List[str]] = {}

    for doc in records:
        url = getattr(doc, "url", getattr(doc, "original_url", None))
        missing: List[str] = []

        # 1. Rights evidence URL
        evidence_url = getattr(doc, "rights_evidence_url", None)
        if evidence_url and str(evidence_url).strip():
            with_rights_evidence += 1
        else:
            missing.append("rights_evidence_url")

        # 2. Review date
        reviewed_at = getattr(doc, "rights_reviewed_at", None)
        if reviewed_at is not None:
            with_review_date += 1
        else:
            missing.append("rights_reviewed_at")
            documents_missing_review_date.append(url)

        # 3. Decision owner / reviewer
        reviewer = getattr(doc, "rights_reviewer", None)
        if reviewer and str(reviewer).strip():
            with_decision_owner += 1
        else:
            missing.append("rights_reviewer")
            documents_missing_decision_owner.append(url)

        # 4. Permissible use
        permissible_use = getattr(doc, "permissible_use", None)
        if permissible_use and str(permissible_use).strip():
            with_permissible_use += 1
        else:
            missing.append("permissible_use")

        # 5. Attribution decision
        attr_req = getattr(doc, "attribution_required", None)
        attr_text = getattr(doc, "attribution_text", None)
        if attr_req is not None and (not attr_req or (attr_text and str(attr_text).strip())):
            with_attribution_decision += 1
        else:
            missing.append("attribution_decision")

        # 6. Publication decision
        pub_status = getattr(doc, "publication_status", None)
        if hasattr(pub_status, "value"):
            pub_status = pub_status.value
        if pub_status in {
            PublicationStatus.ELIGIBLE.value,
            PublicationStatus.REVIEW_REQUIRED.value,
            PublicationStatus.QUARANTINED.value,
            PublicationStatus.PERMISSION_PENDING.value,
            PublicationStatus.REJECTED.value,
        }:
            with_publication_decision += 1
            if pub_status == PublicationStatus.ELIGIBLE.value:
                eligible_count += 1
            elif pub_status == PublicationStatus.REVIEW_REQUIRED.value:
                review_required_count += 1
                unresolved_candidate_decisions.append(url)
            elif pub_status == PublicationStatus.PERMISSION_PENDING.value:
                permission_pending_count += 1
                if url not in unresolved_permission_decisions:
                    unresolved_permission_decisions.append(url)
            elif pub_status in {PublicationStatus.QUARANTINED.value, PublicationStatus.REJECTED.value}:
                excluded_quarantined_documents.append(url)
        else:
            missing.append("publication_status")

        # 7. Third-party permission status
        tp_status = getattr(doc, "third_party_permission_status", None)
        if hasattr(tp_status, "value"):
            tp_status = tp_status.value
        if tp_status in {"REQUESTED_AWAITING_RESPONSE", "PENDING"}:
            permission_requests_submitted += 1
            if url not in unresolved_permission_decisions:
                unresolved_permission_decisions.append(url)
        elif tp_status == "REQUIRED_NOT_SUBMITTED":
            permission_required_not_submitted += 1
            if url not in unresolved_permission_decisions:
                unresolved_permission_decisions.append(url)

        # 8. Actual publication eligibility evaluation (fail-closed)
        is_eligible, deficiencies = evaluate_publication_eligibility(doc)
        if is_eligible:
            owner_approved_eligible_corpus.append(url)
        else:
            eligibility_deficiencies_by_url[url] = deficiencies
            if pub_status == PublicationStatus.ELIGIBLE.value:
                inconsistent_eligible_records.append(url)

        if missing:
            missing_fields_by_url[url] = missing

    # Determine blockers
    blockers: List[str] = []
    if with_review_date < total:
        blockers.append(
            f"{total - with_review_date} candidate documents are missing formal owner review timestamp (rights_reviewed_at is null)"
        )
    if with_decision_owner < total:
        blockers.append(
            f"{total - with_decision_owner} candidate documents are missing formal owner decision reviewer (rights_reviewer is null)"
        )
    if len(inconsistent_eligible_records) > 0:
        blockers.append(
            f"{len(inconsistent_eligible_records)} candidate documents marked ELIGIBLE fail publication eligibility validation (inconsistent/incomplete evidence)"
        )
    if len(unresolved_candidate_decisions) > 0:
        blockers.append(
            f"{len(unresolved_candidate_decisions)} candidate documents remain unresolved under REVIEW_REQUIRED"
        )
    if permission_requests_submitted > 0:
        blockers.append(
            f"{permission_requests_submitted} candidate documents have third-party commercial permission REQUESTED_AWAITING_RESPONSE (submitted but still unresolved; awaiting response)"
        )
    if permission_required_not_submitted > 0:
        blockers.append(
            f"{permission_required_not_submitted} WHO candidate documents have third-party commercial permission REQUIRED_NOT_SUBMITTED (unsubmitted)"
        )
    # Explicit owner-approved corpus decision evaluation
    owner_corpus_status = owner_corpus_decision if owner_corpus_decision else "PENDING"
    owner_corpus_approved = (owner_corpus_decision == "APPROVED")

    if not owner_corpus_approved:
        blockers.append(
            f"Owner-approved corpus decision is pending: Prakash has not supplied an explicit decision approving the publication-eligible corpus (status: {owner_corpus_status}). Acceptance cannot be claimed based only on document count."
        )

    if len(owner_approved_eligible_corpus) == 0:
        blockers.append(
            "0 candidate documents are currently verified publication-eligible (entire candidate corpus is quarantined/review-required)"
        )

    engineering_implementation_complete = (
        total == 32
        and with_rights_evidence == total
        and with_permissible_use == total
        and with_attribution_decision == total
        and with_publication_decision == total
    )
    owner_review_completed = (
        with_review_date == total
        and with_decision_owner == total
        and len(documents_missing_review_date) == 0
        and len(documents_missing_decision_owner) == 0
    )
    # L004 acceptance requires all candidate documents to be reviewed, permissions resolved,
    # no unresolved candidates or inconsistent records, an explicit owner corpus approval decision,
    # and validated publication-eligible documents.
    l004_acceptance_satisfied = (
        engineering_implementation_complete
        and owner_review_completed
        and owner_corpus_approved
        and len(unresolved_candidate_decisions) == 0
        and len(unresolved_permission_decisions) == 0
        and len(inconsistent_eligible_records) == 0
        and len(owner_approved_eligible_corpus) > 0
        and len(blockers) == 0
    )

    return {
        "total_candidate_documents": total,
        "with_rights_evidence": with_rights_evidence,
        "with_review_date": with_review_date,
        "with_decision_owner": with_decision_owner,
        "with_permissible_use": with_permissible_use,
        "with_attribution_decision": with_attribution_decision,
        "with_publication_decision": with_publication_decision,
        "eligible_count": eligible_count,
        "review_required_count": review_required_count,
        "permission_pending_count": permission_pending_count,
        "permission_requests_submitted": permission_requests_submitted,
        "permission_required_not_submitted": permission_required_not_submitted,
        "owner_corpus_decision": owner_corpus_status,
        "owner_corpus_approved": owner_corpus_approved,
        "owner_approved_eligible_corpus_count": len(owner_approved_eligible_corpus),
        "owner_approved_eligible_corpus": owner_approved_eligible_corpus,
        "inconsistent_eligible_records_count": len(inconsistent_eligible_records),
        "inconsistent_eligible_records": inconsistent_eligible_records,
        "unresolved_candidate_decisions_count": len(unresolved_candidate_decisions),
        "unresolved_candidate_decisions": unresolved_candidate_decisions,
        "unresolved_permission_decisions_count": len(unresolved_permission_decisions),
        "unresolved_permission_decisions": unresolved_permission_decisions,
        "explicitly_excluded_documents_count": len(excluded_quarantined_documents),
        "explicitly_excluded_documents": excluded_quarantined_documents,
        "excluded_quarantined_documents_count": len(excluded_quarantined_documents),
        "excluded_quarantined_documents": excluded_quarantined_documents,
        "excluded_untracked_documents_count": len(excluded_untracked_documents),
        "excluded_untracked_documents": excluded_untracked_documents,
        "engineering_implementation_complete": engineering_implementation_complete,
        "owner_review_completed": owner_review_completed,
        "l004_acceptance_satisfied": l004_acceptance_satisfied,
        "blockers": blockers,
        "documents_missing_review_date": documents_missing_review_date,
        "documents_missing_decision_owner": documents_missing_decision_owner,
        "missing_fields_by_url": missing_fields_by_url,
        "eligibility_deficiencies_by_url": eligibility_deficiencies_by_url,
    }


def record_owner_rights_review(
    url: str,
    reviewer: str,
    reviewed_at: Optional[datetime] = None,
    publication_status: Optional[Union[str, PublicationStatus]] = None,
    rights_evidence_url: Optional[str] = None,
    permissible_use: Optional[str] = None,
    commercial_redistribution_allowed: Optional[bool] = None,
    redistribution_allowed: Optional[bool] = None,
    quarantine_reason: Optional[str] = None,
    third_party_permission_status: Optional[Union[str, ThirdPartyPermissionStatus]] = None,
    third_party_permission_notes: Optional[str] = None,
    permission_reference: Optional[str] = None,
    full_text_storage_allowed: Optional[bool] = None,
    derived_summary_allowed: Optional[bool] = None,
    attribution_required: Optional[bool] = None,
    attribution_text: Optional[str] = None,
    clear_quarantine: bool = False,
    db: Optional[Session] = None,
    commit: bool = True,
    update_inventory: bool = False,
) -> Dict[str, Any]:
    """
    Explicit, durable, and auditable owner review workflow function.
    Allows repository owner (Prakash) to truthfully record a verified decision
    on an exact candidate document.

    Safety invariants:
    1. Rejects unknown target URLs (must match RIGHTS_INVENTORY or existing database document).
    2. Supports recording exact evidence URLs and permission references.
    3. Clearly documents transaction persistence:
       - If db is passed, commits/persists durably to the database in a transaction.
       - If db is omitted, clearly flags that the update is in-memory only and NOT saved to database.
    """
    from urllib.parse import urlparse
    from app.models import SourceDocument

    if not reviewer or not str(reviewer).strip():
        raise ValueError("A decision owner/reviewer name is required to record an owner review.")
    reviewer_clean = str(reviewer).strip()

    # 1. Validate target existence (reject unknown targets)
    known_in_inventory = url in RIGHTS_INVENTORY
    db_doc = None
    if db is not None:
        db_doc = db.query(SourceDocument).filter(
            SourceDocument.original_url == url
        ).first()

    if not known_in_inventory and db_doc is None:
        raise ValueError(
            f"Unknown target document URL '{url}'. Cannot record review for an unrecognized target."
        )

    # 2. Validate evidence URL if provided
    if rights_evidence_url is not None:
        ev_clean = str(rights_evidence_url).strip()
        parsed = urlparse(ev_clean)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid rights evidence URL: '{rights_evidence_url}'. Must be valid http/https URL.")

    # 3. Format permission reference and notes if provided
    combined_notes = third_party_permission_notes
    if permission_reference:
        ref_tag = f"[Permission Ref: {str(permission_reference).strip()}]"
        if combined_notes and str(combined_notes).strip():
            combined_notes = f"{ref_tag} {str(combined_notes).strip()}"
        else:
            combined_notes = ref_tag

    review_timestamp = reviewed_at or datetime.utcnow()

    # 4. Update in-memory inventory entry if present
    if known_in_inventory:
        entry = RIGHTS_INVENTORY[url]
        pub_stat = publication_status
        if isinstance(pub_stat, str):
            pub_stat = PublicationStatus(pub_stat)
        elif pub_stat is None:
            pub_stat = entry.publication_status

        tp_stat = third_party_permission_status
        if hasattr(tp_stat, "value"):
            tp_stat = tp_stat.value
        elif tp_stat is None:
            tp_stat = entry.third_party_permission_status

        updated = DocumentRightsDecision(
            url=entry.url,
            source_id=entry.source_id,
            source_organization=entry.source_organization,
            title=entry.title,
            canonical_cancer_slug=entry.canonical_cancer_slug,
            country_code=entry.country_code,
            jurisdiction_scope=entry.jurisdiction_scope,
            publication_status=pub_stat,
            rights_evidence_url=str(rights_evidence_url).strip() if rights_evidence_url else entry.rights_evidence_url,
            rights_reviewed_at=review_timestamp,
            rights_reviewer=reviewer_clean,
            permissible_use=permissible_use if permissible_use is not None else entry.permissible_use,
            redistribution_allowed=redistribution_allowed if redistribution_allowed is not None else entry.redistribution_allowed,
            commercial_redistribution_allowed=commercial_redistribution_allowed if commercial_redistribution_allowed is not None else entry.commercial_redistribution_allowed,
            full_text_storage_allowed=entry.full_text_storage_allowed,
            derived_summary_allowed=entry.derived_summary_allowed,
            attribution_required=entry.attribution_required,
            attribution_text=entry.attribution_text,
            reuse_restrictions=entry.reuse_restrictions,
            quarantine_reason=quarantine_reason if quarantine_reason is not None else entry.quarantine_reason,
            third_party_permission_status=tp_stat,
            third_party_permission_notes=combined_notes if combined_notes is not None else entry.third_party_permission_notes,
        )
        if update_inventory:
            RIGHTS_INVENTORY[url] = updated

    # 5. Handle database transaction persistence
    persisted_to_database = False
    persistence_status = "TRANSIENT_MEMORY_ONLY"
    persistence_warning: Optional[str] = (
        "Review recorded in-memory only. To persist durably and auditably, "
        "pass an active database session (db=session, commit=True)."
    )

    if db is not None:
        if db_doc:
            db_doc.rights_reviewed_at = review_timestamp
            db_doc.rights_reviewer = reviewer_clean
            if rights_evidence_url:
                db_doc.rights_evidence_url = str(rights_evidence_url).strip()
            if publication_status:
                pub_val = str(publication_status.value if hasattr(publication_status, "value") else publication_status)
                db_doc.publication_status = pub_val
                if pub_val == PublicationStatus.ELIGIBLE.value:
                    db_doc.quarantine_reason = None
            if permissible_use is not None:
                db_doc.permissible_use = permissible_use
            if commercial_redistribution_allowed is not None:
                db_doc.commercial_redistribution_allowed = commercial_redistribution_allowed
            if redistribution_allowed is not None:
                db_doc.redistribution_allowed = redistribution_allowed
            if full_text_storage_allowed is not None:
                db_doc.full_text_storage_allowed = full_text_storage_allowed
            if derived_summary_allowed is not None:
                db_doc.derived_summary_allowed = derived_summary_allowed
            if attribution_required is not None:
                db_doc.attribution_required = attribution_required
            if attribution_text is not None:
                db_doc.attribution_text = attribution_text
            if clear_quarantine:
                db_doc.quarantine_reason = None
            elif quarantine_reason is not None:
                db_doc.quarantine_reason = quarantine_reason
            if third_party_permission_status is not None:
                tp_val = third_party_permission_status.value if hasattr(third_party_permission_status, "value") else str(third_party_permission_status)
                db_doc.third_party_permission_status = tp_val
            if combined_notes is not None:
                db_doc.third_party_permission_notes = combined_notes

            if commit:
                db.commit()
                persistence_status = "COMMITTED_TO_DATABASE"
            else:
                db.flush()
                persistence_status = "TRANSACTION_PENDING"

            persisted_to_database = True
            persistence_warning = None

    return {
        "url": url,
        "rights_reviewed_at": review_timestamp.isoformat(),
        "rights_reviewer": reviewer_clean,
        "rights_evidence_url": str(rights_evidence_url).strip() if rights_evidence_url else (entry.rights_evidence_url if known_in_inventory else None),
        "permission_reference": permission_reference,
        "persisted_to_database": persisted_to_database,
        "persistence_status": persistence_status,
        "persistence_warning": persistence_warning,
        "status": "RECORDED",
    }


def generate_markdown_inventory_table() -> str:
    """
    Deterministically generates the markdown table for all 32 candidate URLs
    directly from RIGHTS_INVENTORY, ordered by authority then URL.
    """
    source_order = ["nci-us", "nhs-uk", "who-global", "cancer-australia", "cdc-us"]
    sorted_items = sorted(
        RIGHTS_INVENTORY.items(),
        key=lambda x: (source_order.index(x[1].source_id) if x[1].source_id in source_order else 99, x[0]),
    )
    lines = [
        "| # | Source ID | Publishing Body | URL | Status | Assigned Quarantine Reason |",
        "|---|---|---|---|---|---|",
    ]
    for i, (url, dec) in enumerate(sorted_items, 1):
        lines.append(
            f"| {i} | `{dec.source_id}` | {dec.source_organization} | `{url}` | `{dec.publication_status.value}` | {dec.quarantine_reason} |"
        )
    return "\n".join(lines)


def extract_candidate_urls_from_markdown(markdown_text: str) -> Set[str]:
    """
    Extracts candidate document URLs from markdown tables.
    Matches lines starting with '|' and containing backticked candidate URLs.
    """
    urls: Set[str] = set()
    for line in markdown_text.splitlines():
        if line.strip().startswith("|") and "`http" in line:
            m = re.search(r"`(https?://[^`]+)`", line)
            if m:
                u = m.group(1)
                if any(d in u for d in ["cancer.gov", "nhs.uk", "who.int", "canceraustralia.gov.au", "cdc.gov"]):
                    if not any(p in u for p in ["/policies/", "/copyright", "/open-access", "agencymaterials"]):
                        urls.add(u)
    return urls

