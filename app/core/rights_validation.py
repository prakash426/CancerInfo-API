"""
Publication Eligibility and Rights Validation Module (CIAPI-L004)

Enforces strict fail-closed publication gates:
1. Documents without explicit ELIGIBLE status and complete rights audit evidence cannot be published.
2. Rejects unknown or missing third-party permission decisions and inconsistent evidence.
3. Source-level registry fields (APPROVED, Tier 1, government status, domain) NEVER confer document clearance.
"""
from typing import List, Tuple
from urllib.parse import urlparse
from app.core.constants import ContentType, PublicationStatus, ThirdPartyPermissionStatus


class PublicationEligibilityError(ValueError):
    """Raised when an unreviewed, quarantined, or insufficiently evidenced document is evaluated for publication."""
    pass


VALID_THIRD_PARTY_STATUSES = {s.value for s in ThirdPartyPermissionStatus}
ELIGIBLE_THIRD_PARTY_STATUSES = {
    ThirdPartyPermissionStatus.NOT_APPLICABLE.value,
    ThirdPartyPermissionStatus.GRANTED.value,
}


def evaluate_publication_eligibility(
    doc,
    source=None,
    *,
    content_type=None,
    publication_use="COMMERCIAL",
) -> Tuple[bool, List[str]]:
    """Evaluate a reviewed document for an exact output type and use.

    The default retains the legacy commercial document audit. Public callers
    must supply the actual output type. Noncommercial use requires a separate
    explicit grant; neither free text nor a source's identity implies approval.
    This evaluates delivery rights, not permission to retain source full text.
    """
    reasons: List[str] = []

    # 1. Publication status check
    pub_status = getattr(doc, "publication_status", None)
    if hasattr(pub_status, "value"):
        pub_status = pub_status.value
    if pub_status != PublicationStatus.ELIGIBLE.value:
        reasons.append(
            f"Document publication status is '{pub_status}' (must be '{PublicationStatus.ELIGIBLE.value}')"
        )

    # 2. Rights evidence URL
    evidence_url = getattr(doc, "rights_evidence_url", None)
    if not evidence_url or not str(evidence_url).strip():
        reasons.append("Missing required rights evidence URL")
    else:
        ev_str = str(evidence_url).strip()
        parsed = urlparse(ev_str)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            reasons.append(f"Inconsistent evidence: rights_evidence_url '{ev_str}' is not a valid http/https URL")

    # 3. Review timestamp
    reviewed_at = getattr(doc, "rights_reviewed_at", None)
    if reviewed_at is None:
        reasons.append("Missing required rights review timestamp (rights_reviewed_at)")

    # 4. Reviewer / decision owner
    reviewer = getattr(doc, "rights_reviewer", None)
    if not reviewer or not str(reviewer).strip():
        reasons.append("Missing required rights reviewer or decision owner (rights_reviewer)")

    # 5. Permissible use evidence
    permissible_use = getattr(doc, "permissible_use", None)
    if not permissible_use or not str(permissible_use).strip():
        reasons.append("Missing required permissible-use evidence or determination (permissible_use)")

    # 6. Redistribution permissions & consistency
    redist_allowed = getattr(doc, "redistribution_allowed", None)
    comm_allowed = getattr(doc, "commercial_redistribution_allowed", None)

    if redist_allowed is None:
        reasons.append("Missing explicit decision for redistribution_allowed (redistribution is not allowed)")
    elif not redist_allowed:
        reasons.append("Document-level redistribution is not allowed (redistribution_allowed=False)")

    if publication_use not in {"COMMERCIAL", "NONCOMMERCIAL"}:
        reasons.append("Unknown publication use")
    elif publication_use == "COMMERCIAL":
        if comm_allowed is not True:
            reasons.append("Document-level commercial/API redistribution is not allowed (commercial_redistribution_allowed must be True)")
    else:
        if getattr(doc, "noncommercial_redistribution_allowed", None) is not True:
            reasons.append("Missing explicit approved noncommercial redistribution permission")
        if comm_allowed not in (True, False):
            reasons.append("Missing explicit commercial permission decision")

    if comm_allowed and not redist_allowed:
        reasons.append("Inconsistent evidence: commercial_redistribution_allowed is True while redistribution_allowed is False")

    approved_types = getattr(doc, "approved_publication_content_types", None)
    known_types = {t.value for t in ContentType}
    if content_type is not None and (not isinstance(content_type, str) or content_type not in known_types):
        reasons.append("Unknown publication content type")
        content_type = "INVALID"
    # An explicit allowlist is mandatory for noncommercial delivery and full
    # source text. Existing broad commercial reviews remain valid for summaries.
    needs_types = publication_use == "NONCOMMERCIAL" or content_type in {
        "SOURCE_CONTENT", "TRANSLATION", "AI_ASSISTED_NORMALIZATION", "MANUALLY_CURATED"
    }
    if approved_types is not None or needs_types:
        if (not isinstance(approved_types, list) or not approved_types
                or any(not isinstance(t, str) or t not in known_types for t in approved_types)
                or content_type not in approved_types):
            reasons.append("Output content type lacks explicit document approval")

    storage_allowed = getattr(doc, "full_text_storage_allowed", None)
    derived_allowed = getattr(doc, "derived_summary_allowed", None)
    if content_type is None or content_type == "SOURCE_CONTENT":
        if storage_allowed is not True:
            reasons.append("Document does not allow full text storage (full_text_storage_allowed must be True)")
    if content_type != "SOURCE_CONTENT":
        if derived_allowed is not True:
            reasons.append("Document does not allow derived summary generation (derived_summary_allowed must be True)")

    # 8. Attribution consistency and explicit decision
    attr_required = getattr(doc, "attribution_required", None)
    attr_text = getattr(doc, "attribution_text", None)
    if attr_required is None:
        reasons.append("Missing explicit decision for attribution_required (cannot be None)")
    elif attr_required and (not attr_text or not str(attr_text).strip()):
        reasons.append("Inconsistent evidence: attribution_required is True but attribution_text is missing or empty")

    # 9. Quarantine reason consistency
    quarantine_reason = getattr(doc, "quarantine_reason", None)
    if quarantine_reason and str(quarantine_reason).strip():
        reasons.append(f"Document has active quarantine reason: {quarantine_reason}")

    # 10. Third-party permissions fail-closed evaluation
    tp_status = getattr(doc, "third_party_permission_status", None)
    if hasattr(tp_status, "value"):
        tp_status = tp_status.value

    if not tp_status or not str(tp_status).strip():
        reasons.append("Missing third-party permission decision (third_party_permission_status is null or empty)")
    elif tp_status not in VALID_THIRD_PARTY_STATUSES:
        reasons.append(f"Unknown third-party permission decision: '{tp_status}' (must be a valid ThirdPartyPermissionStatus)")
    elif tp_status not in ELIGIBLE_THIRD_PARTY_STATUSES:
        reasons.append(f"Unresolved third-party permission status: '{tp_status}' (only NOT_APPLICABLE or GRANTED may be eligible)")
    elif tp_status in (ThirdPartyPermissionStatus.GRANTED.value, "GRANTED"):
        tp_notes = getattr(doc, "third_party_permission_notes", None)
        if not tp_notes or not str(tp_notes).strip():
            reasons.append("Inconsistent evidence: third-party permission is GRANTED but supporting evidence/notes are missing (third_party_permission_notes)")

    is_eligible = len(reasons) == 0
    return is_eligible, reasons


def assert_publication_eligible(doc, source=None) -> None:
    """
    Raises PublicationEligibilityError if the document cannot be published.
    """
    is_eligible, reasons = evaluate_publication_eligibility(doc, source=source)
    if not is_eligible:
        url = getattr(doc, "original_url", getattr(doc, "url", "<unknown-url>"))
        raise PublicationEligibilityError(
            f"Document '{url}' is NOT publication eligible: {'; '.join(reasons)}"
        )


def verify_source_cannot_grant_eligibility(doc, source) -> None:
    """
    Verification check: Proves that even if parent source is active, APPROVED, Tier 1,
    and a government agency, an unreviewed document remains ineligible.
    """
    is_eligible, reasons = evaluate_publication_eligibility(doc, source=source)
    if is_eligible:
        raise AssertionError("Document unexpectedly marked eligible without satisfying item-level review criteria!")
