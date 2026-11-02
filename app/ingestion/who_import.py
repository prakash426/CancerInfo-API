"""Transform the reviewed WHO handoff package into normalized documents.

Reads the validated package plus the approver decision sheet, builds one
normalized document per approved URL and cancer pair with one section per
approved fact, loads them through the shared refresh path, and writes
per-fact provenance rows. Undecided pages become metadata only documents.
Rejected pages are skipped. Nothing here marks any record publishable.
"""
import csv
import hashlib
import json
import re
from datetime import datetime

from app.core.constants import PublicationStatus, ThirdPartyPermissionStatus
from app.ingestion.refresh import refresh_document
from app.ingestion.who_validate import load_package
from app.models import (Cancer, ContentRecord, ContentSource, Source,
                        SourceDocument, WhoFactProvenance)
from app.sources.base import NormalizedDocument, NormalizedSection

SOURCE_ID = "who-global"
AUDIENCE = "general_public"
APPROVE = "APPROVE_SUMMARIES"
METADATA = "METADATA_ONLY"
REJECT = "REJECT"
DECISIONS = {APPROVE, METADATA, REJECT, ""}
DENOM_RE = re.compile(r"\(denominator: ([^)]+)\)")


def normalize_decision(value):
    """Accept human written variants of the three decision values."""
    cleaned = re.sub(r"[\s\-]+", "_", (value or "").strip().upper())
    if cleaned in ("APPROVED", "APPROVE"):
        return APPROVE
    if cleaned in ("METADATA", "METADATA_ONLY"):
        return METADATA
    if cleaned in ("REJECTED", "REJECT"):
        return REJECT
    if cleaned == "":
        return ""
    raise ValueError("unknown decision %r" % value)


def load_decisions(path):
    """Read the decision sheet keyed by canonical URL."""
    with open(path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    decisions = {}
    for row in rows:
        try:
            row["decision"] = normalize_decision(row.get("decision"))
        except ValueError:
            raise ValueError("unknown decision %r for %s"
                             % (row.get("decision"),
                                row.get("canonical_url")))
        decisions[row["canonical_url"]] = row
    return decisions


def _slugify(text, fallback):
    base = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return base[:44] or fallback


def page_namespace(url):
    """Short stable page slug from a URL for namespaced identity keys."""
    tail = (url or "").rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0]
    return _slugify(tail, "page")[:24]


def fact_key(heading, category, namespace, used):
    """Deterministic unique subcategory key, namespaced per page."""
    stem = ("%s-%s" % (namespace, _slugify(heading, category)[:24]))[:51]
    seq = 1
    while True:
        key = "%s-%02d" % (stem, seq)
        if key not in used:
            used.add(key)
            return key
        seq += 1


def enrich_content(fact):
    """Compose stand alone record content from fact plus context."""
    parts = [fact["fact_text"]]
    context = []
    if fact.get("reference_period"):
        context.append("Reference period: %s" % fact["reference_period"])
    if fact.get("geography"):
        context.append("Geography: %s" % fact["geography"])
    if fact.get("population"):
        context.append("Population: %s" % fact["population"])
    if context:
        parts.append("[%s]" % "; ".join(context))
    if fact.get("limitations"):
        parts.append("Limitation: %s" % fact["limitations"])
    return " ".join(parts)


def extract_denominator(fact_text):
    """Recover the denominator folded into the fact text at rebuild."""
    match = DENOM_RE.search(fact_text or "")
    return match.group(1) if match else None


def _parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value[:10], pattern)
        except ValueError:
            continue
    raise ValueError("unparseable date %r (use YYYY-MM-DD)" % value)


def build_documents(pkg, decisions):
    """Build normalized documents for approved facts.

    Returns (documents, provenance, metadata_pairs, skipped, warnings)
    where provenance maps (doc_index, identity) to provenance payloads.
    """
    pages_by_pair = {(r["cancer_id"], r["canonical_url"]): r
                     for r in pkg["pages"]}
    facts_by_pair = {}
    for fact in pkg["facts"]:
        if not fact.get("source_url"):
            continue
        facts_by_pair.setdefault((fact["cancer_id"], fact["source_url"]),
                                 []).append(fact)
    cancers = {}
    for row in pkg["pages"]:
        cancers[row["cancer_id"]] = (row["cancer_slug"], row["cancer_name"])

    documents, provenance = [], {}
    metadata_pairs, skipped, warnings = [], [], []
    for (cid, url), facts in sorted(facts_by_pair.items()):
        page = pages_by_pair.get((cid, url))
        if page is None or page["relevance_class"] == "not_relevant":
            skipped.append((cid, url, "outside qualifying checks"))
            continue
        sheet = decisions.get(url, {})
        decision = (sheet.get("decision") or "").strip()
        if decision == REJECT:
            skipped.append((cid, url, "rejected by approver"))
            continue
        if decision != APPROVE:
            metadata_pairs.append((cid, url))
            continue
        if not (sheet.get("reviewer") or "").strip() or not (
                sheet.get("reviewed_at") or "").strip():
            warnings.append("%s %s approval unsigned; metadata only"
                            % (cid, url))
            metadata_pairs.append((cid, url))
            continue
        slug, name = cancers[cid]
        namespace = page_namespace(url)
        used, sections, payloads = set(), [], []
        for fact in facts:
            heading = fact["heading_path"] or fact["source_locator"] or ""
            key = fact_key(heading, fact["category"], namespace, used)
            sections.append(NormalizedSection(
                category=fact["category"],
                content=enrich_content(fact),
                subcategory=key,
                audience=AUDIENCE,
                disagreement_status="CONSISTENT",
                quote_snippet=None,
                source_url=url,
                source_locator=heading or None))
            payloads.append(((fact["category"], key, AUDIENCE), {
                "heading_path": fact["heading_path"],
                "source_locator": fact["source_locator"],
                "match_locations": page["match_locations"],
                "geography": fact["geography"],
                "population": fact["population"],
                "reference_period": fact["reference_period"],
                "units": fact["units"],
                "denominator": extract_denominator(fact["fact_text"]),
                "limitations": fact["limitations"],
                "rights_review_status": fact["rights_review_status"],
                "retrieved_at_utc": fact["retrieved_at_utc"]}))
        digest = hashlib.sha256(json.dumps(
            [[s.category, s.subcategory, s.content] for s in sections],
            ensure_ascii=False).encode("utf-8")).hexdigest()
        index = len(documents)
        documents.append(NormalizedDocument(
            source_id=SOURCE_ID, original_url=url, canonical_url=url,
            title=page["page_title"] or url, cancer_slug=slug,
            source_cancer_name=name, language="en", country_code="GLOBAL",
            jurisdiction_scope="GLOBAL", content_hash=digest, sections=sections,
            published_at=_parse_date(page["published_at"]),
            source_updated_at=None))
        for identity, payload in payloads:
            provenance[(index, identity)] = payload

    for row in pkg["pages"]:
        pair = (row["cancer_id"], row["canonical_url"])
        if pair in facts_by_pair or row["relevance_class"] == "not_relevant":
            continue
        sheet = decisions.get(row["canonical_url"], {})
        if (sheet.get("decision") or "").strip() == REJECT:
            skipped.append((pair[0], pair[1], "rejected by approver"))
        else:
            metadata_pairs.append(pair)
    return documents, provenance, metadata_pairs, skipped, warnings
# --- part 2: load execution with rights enforcement ---
def _stamp_rights(doc, sheet, approved, third_party):
    """Apply decision sheet rights onto a document. Never sets ELIGIBLE."""
    reviewer = (sheet.get("reviewer") or "").strip() or None
    reviewed = _parse_date(sheet.get("reviewed_at"))
    doc.publication_status = PublicationStatus.REVIEW_REQUIRED.value
    doc.permissible_use = (sheet.get("permissible_use") or "").strip() or None
    doc.rights_evidence_url = (sheet.get("rights_evidence_url") or "").strip() or None
    doc.rights_reviewer = reviewer
    doc.rights_reviewed_at = reviewed
    doc.redistribution_allowed = False
    doc.commercial_redistribution_allowed = False
    doc.full_text_storage_allowed = False
    doc.derived_summary_allowed = True
    doc.attribution_required = True
    if not doc.attribution_text:
        doc.attribution_text = ("Source: World Health Organization (WHO). "
                                "Licensed under CC BY-NC-SA 3.0 IGO.")
    if third_party:
        doc.third_party_permission_status = (
            ThirdPartyPermissionStatus.REQUIRED_NOT_SUBMITTED.value)
        doc.third_party_permission_notes = (
            "Third party components excluded; summaries only pending "
            "separate treatment.")
    else:
        doc.third_party_permission_status = (
            ThirdPartyPermissionStatus.NOT_APPLICABLE.value)
        doc.third_party_permission_notes = None
    if approved:
        doc.quarantine_reason = None
    else:
        note = (sheet.get("notes") or "").strip()
        doc.quarantine_reason = note or "No recorded approval for content."


def run_import(db, pkg, decisions, parser_version="who-handoff-v1"):
    """Execute the load inside the caller transaction. Returns a manifest."""
    documents, provenance, metadata_pairs, skipped, warnings = \
        build_documents(pkg, decisions)
    cancers = {}
    for row in pkg["pages"]:
        cancers[row["cancer_id"]] = (row["cancer_slug"], row["cancer_name"])
    page_by_pair = {(r["cancer_id"], r["canonical_url"]): r
                    for r in pkg["pages"]}
    source = db.query(Source).filter(Source.id == SOURCE_ID).one()

    manifest = {"documents": 0, "created": 0, "updated": 0, "retired": 0,
                "provenance_rows": 0, "metadata_docs": 0,
                "skipped": ["%s %s (%s)" % item for item in skipped],
                "warnings": list(warnings)}
    for index, document in enumerate(documents):
        cancer = db.query(Cancer).filter(
            Cancer.slug == document.cancer_slug).one()
        result = refresh_document(db, document, parser_version=parser_version)
        manifest["documents"] += 1
        manifest["created"] += result["created"]
        manifest["updated"] += result["updated"]
        manifest["retired"] += result["retired"]
        doc = db.query(SourceDocument).filter_by(
            source_id=source.id, original_url=document.original_url,
            canonical_cancer_id=cancer.id).one()
        pair = next(cid for cid in cancers
                    if cancers[cid][0] == document.cancer_slug)
        page = page_by_pair[(pair, document.canonical_url)]
        sheet = decisions.get(document.canonical_url, {})
        _stamp_rights(doc, sheet, True,
                      page["third_party_content_flag"] == "TRUE")
        links = db.query(ContentSource).filter_by(
            source_id=source.id, source_document_id=doc.id).all()
        for link in links:
            record = db.get(ContentRecord, link.content_record_id)
            key = (record.category, record.subcategory or record.category,
                   record.audience)
            payload = provenance.get((index, key))
            if payload is None:
                continue
            existing = db.query(WhoFactProvenance).filter_by(
                content_record_id=record.id).one_or_none()
            if existing is None:
                db.add(WhoFactProvenance(content_record_id=record.id,
                                         **payload))
                manifest["provenance_rows"] += 1
            else:
                for field, value in payload.items():
                    setattr(existing, field, value)

    seen_meta = set()
    for cid, url in metadata_pairs:
        if (cid, url) in seen_meta:
            continue
        seen_meta.add((cid, url))
        slug, name = cancers[cid]
        cancer = db.query(Cancer).filter(Cancer.slug == slug).one()
        page = page_by_pair[(cid, url)]
        doc = db.query(SourceDocument).filter_by(
            source_id=source.id, original_url=url,
            canonical_cancer_id=cancer.id).one_or_none()
        if doc is None:
            doc = SourceDocument(
                source_id=source.id, original_url=url, canonical_url=url,
                title=page["page_title"] or url,
                canonical_cancer_id=cancer.id, source_cancer_name=name,
                language="en", country_code="GLOBAL",
                jurisdiction_scope="GLOBAL",
                content_hash=hashlib.sha256(
                    ("metadata-only|%s|%s" % (url, cid)).encode("utf-8")
                ).hexdigest(),
                license_status=source.license_status,
                processing_status="METADATA_ONLY")
            db.add(doc)
            db.flush()
            manifest["metadata_docs"] += 1
        sheet = decisions.get(url, {})
        _stamp_rights(doc, sheet, False,
                      page["third_party_content_flag"] == "TRUE")
        if doc.publication_status == PublicationStatus.REVIEW_REQUIRED.value:
            doc.publication_status = PublicationStatus.QUARANTINED.value
    return manifest
