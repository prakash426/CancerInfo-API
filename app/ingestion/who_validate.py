"""Validate the reviewed WHO handoff package before any staging load.

Checks IDs and slugs against the approved taxonomy, confirms every fact
traces to a reviewed page and section, rejects invented dates, duplicate
facts, and unsupported category mappings, and lists brief mention sourced
facts for reviewer attention. Also builds the per URL rights decision sheet.
"""
import csv
import json
import re
import sqlite3
from pathlib import Path

from app.core.constants import CANONICAL_CATEGORIES

PAGE_FIELDS = ["cancer_id", "cancer_slug", "cancer_name", "original_url",
               "canonical_url", "page_title", "h1", "publisher", "language",
               "published_at", "updated_at", "retrieved_at_utc", "page_type",
               "match_locations", "relevance_class", "relevance_reason",
               "third_party_content_flag", "rights_review_status",
               "review_notes"]
SECTION_FIELDS = ["section_id", "cancer_id", "canonical_url", "heading_path",
                  "heading_level", "fragment_or_locator", "topic",
                  "section_summary", "content_available",
                  "reason_if_withheld"]
FACT_FIELDS = ["cancer_id", "cancer_slug", "category", "subcategory",
               "fact_text", "fact_type", "source_url", "source_locator",
               "heading_path", "source_published_at", "source_updated_at",
               "retrieved_at_utc", "geography", "population",
               "reference_period", "units", "limitations", "transformation",
               "verification_status", "rights_review_status"]
COVERAGE_FIELDS = ["cancer_id", "cancer_slug", "cancer_name", "status",
                   "dedicated_pages", "substantial_sections",
                   "brief_mentions", "not_relevant_checked", "reviewed_facts",
                   "reviewed_sections", "best_url", "best_classification",
                   "detail"]
RELEVANCE = {"dedicated_page", "substantial_section", "brief_mention",
             "not_relevant"}
COVERAGE_STATUS = {"found", "partial", "no_qualifying_page_found"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CL_RE = re.compile(r"^CL\d\d$")
SLUG_RE = re.compile(r"^[a-z0-9-]+$")


def parse_taxonomy_register(path):
    """Return (id_to_name_slug, id_to_aliases) from the approved taxonomy."""
    register, aliases = {}, {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line.startswith("|"):
                continue
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) < 5 or not CL_RE.match(cols[0]):
                continue
            cid = cols[0]
            if cols[1] in ("common", "rare") and SLUG_RE.match(cols[3]):
                register[cid] = (cols[2], cols[3])
            elif SLUG_RE.match(cols[1]) and cid not in aliases:
                aliases[cid] = [a.strip() for a in cols[2].split(";")
                                if a.strip()]
    return register, aliases


def _read_csv(path, expected, label):
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected:
            raise ValueError("%s header mismatch: %s" % (label,
                                                         reader.fieldnames))
        return list(reader)


def load_package(pkg_dir):
    """Read the four handoff files into lists of dicts."""
    pkg = Path(pkg_dir)
    pages = _read_csv(pkg / "who_pages.csv", PAGE_FIELDS, "who_pages.csv")
    sections = _read_csv(pkg / "who_sections.csv", SECTION_FIELDS,
                         "who_sections.csv")
    facts = []
    with open(pkg / "who_facts.ndjson", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                facts.append(json.loads(line))
    coverage = _read_csv(pkg / "who_coverage.csv", COVERAGE_FIELDS,
                         "who_coverage.csv")
    return {"pages": pages, "sections": sections, "facts": facts,
            "coverage": coverage}
# --- part 2: validation, report, decision sheet ---
def _norm_text(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def validate_package(pkg, register, live_db_path=None):
    """Validate a loaded package. Returns a report dict."""
    errors, warnings = [], []
    pages, sections = pkg["pages"], pkg["sections"]
    facts, coverage = pkg["facts"], pkg["coverage"]

    cov_ids = [r["cancer_id"] for r in coverage]
    want_ids = ["CL%02d" % i for i in range(1, 26)]
    if sorted(cov_ids) != want_ids:
        errors.append("coverage must hold exactly CL01 through CL25")
    for row in coverage:
        cid = row["cancer_id"]
        if cid in register:
            name, slug = register[cid]
            if row["cancer_slug"] != slug:
                errors.append("%s slug %s differs from taxonomy %s"
                              % (cid, row["cancer_slug"], slug))
            if row["cancer_name"] != name:
                errors.append("%s name %s differs from taxonomy %s"
                              % (cid, row["cancer_name"], name))
        else:
            errors.append("coverage row %s not in approved taxonomy" % cid)
        if row["status"] not in COVERAGE_STATUS:
            errors.append("%s has invalid status %s" % (cid, row["status"]))

    page_dates, page_class = {}, {}
    for row in pages:
        url = row["canonical_url"]
        if "www.who.int" not in (url or ""):
            errors.append("off domain page row for %s: %s"
                          % (row["cancer_id"], url))
        if row["relevance_class"] not in RELEVANCE:
            errors.append("invalid relevance %s for %s %s"
                          % (row["relevance_class"], row["cancer_id"], url))
        if row["published_at"] and not DATE_RE.match(row["published_at"]):
            errors.append("bad page date %s on %s"
                          % (row["published_at"], url))
        if url in page_dates and page_dates[url] != row["published_at"]:
            errors.append("conflicting dates for %s" % url)
        page_dates[url] = row["published_at"]
        page_class[(row["cancer_id"], url)] = row["relevance_class"]

    sections_by_pair = {}
    seen_section_ids = set()
    for row in sections:
        if row["section_id"] in seen_section_ids:
            errors.append("duplicate section_id %s" % row["section_id"])
        seen_section_ids.add(row["section_id"])
        if row["topic"] not in CANONICAL_CATEGORIES:
            errors.append("unsupported section topic %s in %s"
                          % (row["topic"], row["section_id"]))
        key = (row["cancer_id"], row["canonical_url"])
        sections_by_pair.setdefault(key, []).append(row["heading_path"])

    seen_facts = {}
    brief_mention_facts = []
    for pos, fact in enumerate(facts):
        if sorted(fact.keys()) != sorted(FACT_FIELDS):
            errors.append("fact %d has wrong keys" % pos)
            continue
        cid, url = fact["cancer_id"], fact["source_url"]
        if fact["category"] not in CANONICAL_CATEGORIES:
            errors.append("fact %d has unsupported category %s"
                          % (pos, fact["category"]))
        if fact["fact_type"] != "summary":
            errors.append("fact %d is not a declared summary" % pos)
        cls = page_class.get((cid, url))
        if cls is None:
            errors.append("fact %d points outside reviewed checks: %s %s"
                          % (pos, cid, url))
        elif cls == "not_relevant":
            errors.append("fact %d drawn from not_relevant page: %s"
                          % (pos, url))
        elif cls == "brief_mention":
            brief_mention_facts.append((pos, cid, url))
        pair_sections = sections_by_pair.get((cid, url), [])
        if not pair_sections:
            errors.append("fact %d has no section for %s %s" % (pos, cid, url))
        else:
            heading = fact["heading_path"] or fact["source_locator"] or ""
            if heading and not any(heading in path for path in pair_sections):
                warnings.append("fact %d heading not matched in sections: %s"
                                % (pos, heading[:80]))
        want_date = page_dates.get(url, "")
        got_date = fact["source_published_at"] or ""
        if got_date and got_date != want_date:
            errors.append("fact %d carries invented date %s (page shows %s)"
                          % (pos, got_date, want_date or "none"))
        key = (cid, _norm_text(fact["fact_text"]))
        if key in seen_facts:
            errors.append("duplicate fact text for %s at positions %d and %d"
                          % (cid, seen_facts[key], pos))
        else:
            seen_facts[key] = pos

    if brief_mention_facts:
        warnings.append("%d facts rest on brief mentions and need reviewer "
                        "approval as list level statistics, not profiles"
                        % len(brief_mention_facts))

    computed = {}
    for row in pages:
        bucket = computed.setdefault(row["cancer_id"],
                                     {"d": 0, "s": 0, "b": 0, "n": 0,
                                      "f": 0, "sec": 0})
        bucket[{"dedicated_page": "d", "substantial_section": "s",
                "brief_mention": "b", "not_relevant": "n"}
               [row["relevance_class"]]] += 1
    for fact in facts:
        computed.setdefault(fact["cancer_id"],
                            {"d": 0, "s": 0, "b": 0, "n": 0,
                             "f": 0, "sec": 0})["f"] += 1
    for row in sections:
        computed.setdefault(row["cancer_id"],
                            {"d": 0, "s": 0, "b": 0, "n": 0,
                             "f": 0, "sec": 0})["sec"] += 1
    for row in coverage:
        bucket = computed.get(row["cancer_id"], {})
        pairs = [("dedicated_pages", "d"), ("substantial_sections", "s"),
                 ("brief_mentions", "b"), ("not_relevant_checked", "n"),
                 ("reviewed_facts", "f"), ("reviewed_sections", "sec")]
        for col, key in pairs:
            if int(row[col]) != bucket.get(key, 0):
                errors.append("%s coverage column %s says %s but package "
                              "holds %d" % (row["cancer_id"], col, row[col],
                                             bucket.get(key, 0)))

    live_overlap = []
    if live_db_path:
        conn = sqlite3.connect("file:%s?mode=ro" % live_db_path, uri=True)
        try:
            rows = conn.execute(
                "SELECT cs.source_url, cr.category "
                "FROM content_sources cs "
                "JOIN content_records cr "
                "ON cr.id = cs.content_record_id "
                "WHERE cs.source_id = 'who-global'").fetchall()
        finally:
            conn.close()
        live_pairs = {(u, c) for u, c in rows}
        for pos, fact in enumerate(facts):
            if (fact["source_url"], fact["category"]) in live_pairs:
                live_overlap.append((pos, fact["cancer_id"],
                                     fact["source_url"], fact["category"]))
        if live_overlap:
            warnings.append("%d facts overlap live WHO records by URL and "
                            "category and need reviewer dedup"
                            % len(live_overlap))

    return {"errors": errors, "warnings": warnings,
            "brief_mention_facts": brief_mention_facts,
            "live_overlap": live_overlap,
            "stats": {"pages": len(pages), "sections": len(sections),
                      "facts": len(facts), "coverage": len(coverage)}}


def write_report(report, out_path):
    """Write a human readable validation report."""
    lines = ["# WHO package validation report",
             "",
             "Counts: %(pages)d page checks, %(sections)d sections, "
             "%(facts)d facts, %(coverage)d coverage rows." % report["stats"],
             "",
             "Errors: %d. Warnings: %d." % (len(report["errors"]),
                                            len(report["warnings"])),
             ""]
    lines.append("## Errors (blocking)")
    lines.append("")
    if report["errors"]:
        for item in report["errors"]:
            lines.append("- " + item)
    else:
        lines.append("None.")
    lines.append("")
    lines.append("## Warnings (reviewer attention)")
    lines.append("")
    if report["warnings"]:
        for item in report["warnings"]:
            lines.append("- " + item)
    else:
        lines.append("None.")
    lines.append("")
    if report["brief_mention_facts"]:
        lines.append("## Brief mention sourced facts")
        lines.append("")
        for pos, cid, url in report["brief_mention_facts"]:
            lines.append("- fact %d: %s %s" % (pos, cid, url))
        lines.append("")
    if report["live_overlap"]:
        lines.append("## Live database overlap")
        lines.append("")
        for pos, cid, url, cat in report["live_overlap"]:
            lines.append("- fact %d: %s %s %s" % (pos, cid, url, cat))
        lines.append("")
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    return out_path


SHEET_FIELDS = ["canonical_url", "page_title", "cancers",
                "best_classification", "third_party_content_flag",
                "suggested_decision", "suggestion_reason", "decision",
                "reviewer", "reviewed_at", "permissible_use",
                "rights_evidence_url", "notes"]
RANK = {"dedicated_page": 0, "substantial_section": 1, "brief_mention": 2,
        "not_relevant": 3}
SUGGESTED_USE = ("Non-commercial research and educational use only under "
                 "CC BY-NC-SA 3.0 IGO; confirm before load.")
SUGGESTED_EVIDENCE = "https://www.who.int/about/policies/publishing/open-access"


def make_decision_sheet(pkg, out_path):
    """Build one decision row per deduplicated URL."""
    by_url = {}
    for row in pkg["pages"]:
        slot = by_url.setdefault(row["canonical_url"],
                                 {"title": row["page_title"], "cancers": [],
                                  "classes": [], "third_party": "FALSE",
                                  "page_type": row["page_type"]})
        slot["cancers"].append("%s=%s" % (row["cancer_id"],
                                          row["relevance_class"]))
        slot["classes"].append(row["relevance_class"])
        if row["third_party_content_flag"] == "TRUE":
            slot["third_party"] = "TRUE"
    rows = []
    for url in sorted(by_url):
        slot = by_url[url]
        best = sorted(slot["classes"], key=RANK.get)[0]
        if slot["page_type"] in ("not_found_probe", "soft_404_shell"):
            suggestion, reason = ("REJECT",
                                  "Probe URL holds no WHO content.")
        elif best in ("dedicated_page", "substantial_section"):
            if slot["third_party"] == "TRUE":
                reason = ("Reviewed qualifying coverage; reviewer confirms "
                          "each summary and number and the treatment of "
                          "third party derived statistics.")
            else:
                reason = ("Reviewed qualifying coverage; reviewer confirms "
                          "each summary and number.")
            suggestion = "APPROVE_SUMMARIES"
        elif slot["third_party"] == "TRUE":
            suggestion, reason = ("METADATA_ONLY",
                                  "Brief mention level with third party "
                                  "material; needs separate treatment before "
                                  "any content load.")
        else:
            suggestion, reason = ("METADATA_ONLY",
                                  "Brief mention level only; reviewer may "
                                  "upgrade list level statistics.")
        rows.append({"canonical_url": url, "page_title": slot["title"],
                     "cancers": ";".join(slot["cancers"]),
                     "best_classification": best,
                     "third_party_content_flag": slot["third_party"],
                     "suggested_decision": suggestion,
                     "suggestion_reason": reason, "decision": "",
                     "reviewer": "", "reviewed_at": "",
                     "permissible_use": SUGGESTED_USE,
                     "rights_evidence_url": SUGGESTED_EVIDENCE, "notes": ""})
    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_FIELDS,
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return out_path
