# Content Rights, Redistribution, and Attribution Guide (CIAPI-L004)

## 1. Executive Summary & Policy Overview

The CancerInfo API aggregates cancer clinical information, patient guides, and epidemiological statistics from authoritative public health organizations worldwide. However, public availability on the open web does **not** equal unrestricted redistribution rights for downstream API consumers, commercial entities, or derivative works.

Under **CIAPI-L004**, CancerInfo API enforces a **fail-closed, document-level rights architecture**. Every individual source document, raw scraped content record, and consensus citation must possess an explicit, audited rights decision before it may be published or redistributed.

---

## 2. Source-Level vs. Document-Level Clearance

### The Fallacy of Blanket Source Clearance
In legacy systems, an organization like the National Cancer Institute (NCI) or Centers for Disease Control and Prevention (CDC) was often labeled `license_status = "APPROVED"` or `trust_tier = "Tier 1"` at the source level. It was incorrectly assumed that every page or document under that domain inherited the same unrestricted rights.

**This assumption is legally invalid.**

### Why Source-Level Flags Cannot Grant Document Clearance
1. **Third-Party Embedded Materials**: Government public health sites regularly license diagrams, anatomical illustrations, clinical photography, and video tutorials from private medical illustrators, academic publishers, or stock agencies under restrictive terms that prohibit downstream API syndication.
2. **Multi-Jurisdictional Guidelines**: Joint guidelines (e.g., screening recommendations jointly published by state and federal bodies) frequently retain separate proprietary carve-outs.
3. **Non-Commercial Restrictions (NC)**: Global health authorities (such as the World Health Organization) publish extensive open-access materials under Creative Commons licenses containing Non-Commercial (`-NC`) or Share-Alike (`-SA`) restrictions that are incompatible with public commercial API syndication without written agreements.
4. **Crown Copyright Exceptions**: Crown copyright materials (e.g., UK Open Government Licence or Australian Crown copyright) explicitly exclude third-party rights, departmental logos, press photography, and certain software/datasets.

> **Absolute Rule**: An individual document's publication status is evaluated strictly on its own verified legal merits. `source.license_status == "APPROVED"`, `source.trust_tier == "Tier 1"`, or `source.source_type == "government"` **never** confers publication eligibility upon a `SourceDocument`.

---

## 3. Fail-Closed Rights Model & Lifecycle States (`PublicationStatus`)

CancerInfo API models publication clearance using the `PublicationStatus` enum:

| Status | Code | Redistribution Allowed | Description |
|---|---|---|---|
| `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | **No** (Fail-closed) | Default state for all newly ingested or unreviewed documents. Awaiting human legal audit. |
| `PERMISSION_PENDING` | `PERMISSION_PENDING` | **No** (Quarantined) | Document requires explicit third-party copyright clearance or a formal commercial waiver. |
| `QUARANTINED` | `QUARANTINED` | **No** (Quarantined) | Document contains known license violations, proprietary restrictions, or disputed ownership. |
| `REJECTED` | `REJECTED` | **No** (Permanent stop) | Material explicitly refused for API redistribution. |
| `ELIGIBLE` | `ELIGIBLE` | **Yes** (Subject to attribution) | Document has passed manual item-level audit with verified evidence and recorded reviewer. |

### The Invariant of `is_publication_eligible()`
A `SourceDocument` is considered publication-eligible **only if all** of the following conditions are simultaneously met:
1. `publication_status == "ELIGIBLE"`
2. `rights_evidence_url` is non-empty and points to the authoritative legal policy or license grant.
3. `rights_reviewed_at` contains a valid ISO timestamp.
4. `rights_reviewer` contains the name or ID of the human auditor who performed the audit.
5. `redistribution_allowed is True`
6. `commercial_redistribution_allowed is True`
7. `quarantine_reason is None` (or empty)
8. `third_party_permission_status in (None, "", "NOT_APPLICABLE", "GRANTED")`

If any single condition fails, `is_publication_eligible()` evaluates to `False`, and calling `assert_publication_eligible()` raises a `PublicationEligibilityError`.

---

## 4. Source-by-Source Policy & Candidate URL Audit Requirements

The launch candidate inventory comprises **32 unique URLs** across 5 health authorities (20 normal content URLs, 20 consensus URLs, 8 overlapping, 12 consensus-only). Currently, **0 of 32 documents are marked `ELIGIBLE`**; all 32 remain fail-closed awaiting manual verification.

```
Total Candidate URLs: 32
├── Review Required:    28 documents
├── Permission Pending:  4 documents (WHO)
└── Eligible:            0 documents
```

### 1. National Cancer Institute (NCI, U.S. NIH) — 14 URLs
* **Governing Policy**: [NCI Copyright and Reuse Policy](https://www.cancer.gov/policies/copyright-reuse)
* **General Doctrine**: Most text created by NCI employees is in the U.S. public domain (17 U.S.C. § 105).
* **Quarantine Risk / Exceptions**:
  * Medical illustrations and infographics are often licensed from external medical artists.
  * PDQ® Cancer Information Summaries are written by independent editorial boards and may incorporate tables or guidelines from private clinical societies (e.g., ASCO, NCCN).
  * Photos and patient stories may carry individual privacy or publicity releases that do not permit API syndication.
* **Audit Requirement**: Every NCI URL must be reviewed to verify that the specific extracted text, symptoms, and staging do not include proprietary illustrations or third-party editorial extracts.

### 2. National Health Service (NHS England) — 9 URLs
* **Governing Policy**: [NHS Open Government Licence](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
* **General Doctrine**: NHS digital content is generally available under OGL v3.0.
* **Attribution Requirement**: Mandatory attribution statement: *"Contains public sector information licensed under the Open Government Licence v3.0."*
* **Quarantine Risk / Exceptions**:
  * Departmental logos, NHS trade marks, and branding are excluded.
  * Embedded images and clinical videos frequently belong to third-party medical trusts or commercial agencies.
* **Audit Requirement**: Ensure that API responses extract only the textual clinical guidance and that standard OGL v3.0 attribution is attached to all distributed payloads.

### 3. World Health Organization (WHO) — 4 URLs
* **Governing Policy**: [WHO Open Access Policy](https://www.who.int/about/policies/publishing/open-access)
* **General Doctrine**: WHO fact sheets are published under **CC BY-NC-SA 3.0 IGO** (Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Intergovernmental Organizations).
* **Quarantine Status**: **`PERMISSION_PENDING` (Quarantined)**.
* **Why CC BY-NC-SA 3.0 IGO Is Blocked**:
  1. *Non-Commercial Restriction*: Downstream consumers of CancerInfo API may operate commercial services, SaaS platforms, or sponsored patient applications. Distributing `-NC` content in a general-purpose API introduces legal risk to downstream consumers. A free API service itself cannot legally presume that all downstream uses qualify as non-commercial.
  2. *Share-Alike Requirement*: Any derivative or compilation may be subject to copyleft obligations.
* **Resolution Workflow**: WHO documents cannot be marked `ELIGIBLE` without a formal written agreement or commercial waiver from the WHO permissions committee.

### 4. Cancer Australia (Australian Government) — 4 URLs
* **Governing Policy**: [Cancer Australia Copyright](https://www.canceraustralia.gov.au/copyright)
* **General Doctrine**: Material is published under Creative Commons Attribution 4.0 International (CC BY 4.0), subject to Commonwealth Crown Copyright.
* **Quarantine Status**: **`REVIEW_REQUIRED`**.
* **Quarantine Risk / Exceptions**:
  * Excludes Commonwealth coat of arms, agency logos, and proprietary screening guidelines developed in conjunction with regional state colleges.
  * Melanoma clinical staging and symptom guides frequently incorporate diagnostic images owned by private dermatological colleges.
* **Audit Requirement**: Audit each URL to confirm that symptom lists and recommendations are purely statutory guidance free from third-party clinical copyright.

### 5. Centers for Disease Control and Prevention (CDC, U.S.) — 1 URL
* **Governing Policy**: [CDC Copyright Information](https://www.cdc.gov/other/agencymaterials.html)
* **General Doctrine**: Most federal CDC materials are in the public domain.
* **Quarantine Status**: **`REVIEW_REQUIRED`**.
* **Quarantine Risk / Exceptions**:
  * CDC policies explicitly state that many campaigns (e.g., screening guides, *Screen for Life*) use copyrighted photos, logos, or slogans owned by outside contractors.
* **Audit Requirement**: Verify that the colorectal screening guide text does not include proprietary campaign slogans or contracted media assets.

---

## 5. Third-Party Media, Images, and Embedded Proprietary Assets

1. **Text vs. Media Isolation**: The parser and ingestion engine only ingest raw text, structured tables, and semantic metadata. Binary image downloads and media file caching are strictly prohibited until an asset-level licensing subsystem is built.
2. **Quarantine of Mixed-License Pages**: If a source document contains public text but embeds a proprietary clinical diagram, the `quarantine_reason` must document the mixed status, and `third_party_permission_status` must be set to `REVIEW_REQUIRED` or `NOT_APPLICABLE` (if images are stripped during parsing).
3. **Derived Summaries**: When synthesizing summaries from public facts, the compilation must adhere to fair use / fair dealing doctrines and cite the underlying source document explicitly.

---

## 6. Consensus Fact Source Linkage & Attribution Architecture

Consensus facts synthesize corroborated clinical agreement across multiple health authorities (e.g., NCI, NHS, WHO, Cancer Australia).

### Relational Linkage
Prior to L004, `ConsensusFactSource` stored a freeform `source_name` and `source_url`, without a relational connection to the underlying ingested document. 

In **CIAPI-L004**, `ConsensusFactSource` includes a required foreign key:
```sql
consensus_fact_sources.source_document_id -> source_documents.id
```
- Every consensus citation points directly to an existing `SourceDocument` row.
- If a consensus source references an authoritative URL not part of the standard scraped content set, the seed engine creates a dedicated `SourceDocument` record with status `REVIEW_REQUIRED` or `PERMISSION_PENDING`.
- Repeated citations to the same URL share the exact same `SourceDocument` row (preventing duplication).

### Direct Quotation Snippet Policy
1. **Substantiality Limit**: Consensus fact citations store a `quote_snippet` of 50–250 characters directly reflecting the clinical text corroborating the fact.
2. **Attribution Requirement**: Every citation retains `attribution_text` specifying the exact publishing authority and license conditions.
3. **No Standalone Redistribution**: Quotation snippets are provided for clinical verification and corroboration tracing; they are never redistributed as independent content blocks outside their consensus fact context.

---

## 7. Schema, Database, & API Provenance Surfaces

### Alembic Migration: `0002_document_rights_and_consensus_linkage`
The migration adds 15 columns and 2 indexes across `source_documents` and `consensus_fact_sources`:

```python
# source_documents additions
Column("publication_status", String(32), server_default="REVIEW_REQUIRED", nullable=False, index=True)
Column("rights_evidence_url", String(1024), nullable=True)
Column("rights_reviewed_at", DateTime, nullable=True)
Column("rights_reviewer", String(255), nullable=True)
Column("permissible_use", String(255), nullable=True)
Column("commercial_redistribution_allowed", Boolean, nullable=True)
Column("redistribution_allowed", Boolean, nullable=True)
Column("full_text_storage_allowed", Boolean, nullable=True)
Column("derived_summary_allowed", Boolean, nullable=True)
Column("attribution_required", Boolean, nullable=True)
Column("attribution_text", String(512), nullable=True)
Column("reuse_restrictions", Text, nullable=True)
Column("quarantine_reason", Text, nullable=True)
Column("third_party_permission_status", String(64), nullable=True)
Column("third_party_permission_notes", Text, nullable=True)

# consensus_fact_sources additions
Column("source_document_id", String(36), ForeignKey("source_documents.id"), nullable=True, index=True)
```

### Consumer API Response Models
Both `ProvenanceSourceOut` (attached to content records) and `CorroboratingSourceOut` (attached to consensus items) expose document-level provenance fields:

```json
{
  "source_name": "National Cancer Institute",
  "document_title": "Breast Cancer Symptoms - NCI",
  "url": "https://www.cancer.gov/types/breast/symptoms",
  "publication_status": "REVIEW_REQUIRED",
  "reuse_conditions": "May contain medical illustration diagrams subject to third-party medical animator licensing.",
  "commercial_redistribution_allowed": false,
  "rights_evidence_url": "https://www.cancer.gov/policies/copyright-reuse"
}
```

---

## 8. Machine-Readable Rights Inventory & Audit Tools

The authoritative inventory of all 32 candidate URLs is maintained in:
`app/ingestion/rights_inventory.py`

### Python API
```python
from app.ingestion.rights_inventory import (
    RIGHTS_INVENTORY,
    get_rights_inventory_entry,
    list_rights_inventory,
    export_rights_audit_report
)

# Retrieve a single decision
decision = get_rights_inventory_entry("https://www.cancer.gov/types/breast/symptoms")

# Export complete relational audit report including quotes and consensus citations
report = export_rights_audit_report(db_session)
```

---

## 9. Operational Verification & Transition Workflow

To transition an individual document from `REVIEW_REQUIRED` to `ELIGIBLE`:

### Step-by-Step Transition Checklist:
1. **URL Inspection**: Open the exact URL and inspect the page footer, sidebar, and embedded credits for third-party copyright notices.
2. **Media Audit**: Confirm that no proprietary stock images, animated medical illustrations, or vendor logos are included in the scraped content fields.
3. **Statutory Exemption**: Confirm whether the content was authored by civil servants in their official duties (e.g., 17 U.S.C. § 105 for U.S. Federal Government, Crown Copyright OGL v3.0 for NHS England).
4. **Attribution Formulation**: Draft an accurate attribution string (e.g., *"Source: National Cancer Institute (cancer.gov). Public domain."*).
5. **Database / Inventory Update**:
   Update `app/ingestion/rights_inventory.py` or use the durable review API:
   ```python
   from app.ingestion.rights_inventory import record_owner_rights_review

   record_owner_rights_review(
       url="<candidate URL>",
       reviewer="<auditor name>",
       reviewed_at=datetime.utcnow(),
       publication_status="ELIGIBLE",
       rights_evidence_url="<authoritative policy URL>",
       permissible_use="<justification>",
       commercial_redistribution_allowed=True,
       redistribution_allowed=True,
       quarantine_reason=None,
       third_party_permission_status="NOT_APPLICABLE",
       db=db_session,
       commit=True,
   )
   ```
6. **Populated Database Transition Execution**:
   For existing populated environments, run the transactional transition tool instead of reseeding or bootstrapping (which can overwrite quotes, attributions, or content history):
   ```bash
   # 1. Validate changes without mutating records:
   python scripts/transition_l004.py --dry-run

   # 2. Apply repeat-safe transition in a single atomic transaction:
   python scripts/transition_l004.py
   ```

---

## 10. Downstream Publication Gate Integration Guide

Future publication gates, indexing pipelines, or public API filters should enforce publication eligibility using the built-in model methods:

```python
from app.core.rights_validation import assert_publication_eligible, PublicationEligibilityError
from app.models import SourceDocument

# Fail-closed check before serving or exporting a document:
doc = db.query(SourceDocument).filter_by(id=doc_id).one()

if not doc.is_publication_eligible():
    # Quarantine: exclude from public search index or omit full text
    logger.warning("Omitting quarantined document %s from public syndication", doc.id)
```

Or enforce via exception:
```python
try:
    doc.assert_publication_eligible()
except PublicationEligibilityError as err:
    # Handle gate rejection
    ...
```

---

## 11. Developer Golden Rules

1. **Never Assume Clearance**: Never mark a URL `ELIGIBLE` based on the domain name, authority tier, or open-access label alone.
2. **Never Infer Commercial Rights**: A Creative Commons license with `-NC` is **not** eligible for general API syndication.
3. **Preserve Relational Integrity**: Never add a consensus citation without linking it to its corresponding `SourceDocument`.
4. **Keep Quarantine Reasons Explicit**: When quarantining a document, always state the exact legal ambiguity or restriction in `quarantine_reason`.
5. **No Runtime Schema Mutations**: Always use Alembic migrations for schema updates; never reintroduce `Base.metadata.create_all()`.

---

## 12. Consumer, Marketplace, and Public Directory Listing Rules

When publishing or documenting the CancerInfo API on public portals (such as RapidAPI, Postman Public Workspace, OpenAPI hub catalogs, GitHub README, or product websites), developers and marketers must strictly adhere to the following consumer-listing rules:

### 1. Coverage Claims Restricted to Actually Eligible Corpus
- Public directory listings, API documentation, and marketplace descriptions must advertise coverage based **strictly on documents that have achieved `publication_status == "ELIGIBLE"`**.
- Documents held under `REVIEW_REQUIRED`, `QUARANTINED`, or `PERMISSION_PENDING` must **never** be advertised as commercially cleared or unrestricted API coverage.

### 2. Truthful Representation of Current Clearance Status
- In the current pre-launch stage, exactly **0 of 32 candidate documents are marked `ELIGIBLE`**; all 32 remain quarantined or in review pending manual audit by the repository owner (Prakash).
- Marketplace listings and documentation must truthfully state this pre-cleared quarantine state and must not make misleading claims of full commercial clearance.

### 3. Downstream Redistribution & Commercial Restrictions Must Not Be Concealed
- Downstream developers must be informed of redistribution constraints.
- Because the API exposes `publication_status`, `reuse_conditions`, `commercial_redistribution_allowed`, and `rights_evidence_url` on both `ProvenanceSourceOut` and `CorroboratingSourceOut` response models, API consumers must respect these fields when syndicating or incorporating data into commercial applications.

### 4. Attribution Requirements Must Remain Prominent
- Upstream licenses requiring attribution (such as NHS Open Government Licence v3.0 and Cancer Australia CC BY 4.0) must be prominently documented.
- Downstream applications consuming the API are legally required to pass through the specified `attribution_text`.

### 5. Prohibited Claims Regarding WHO and Non-Commercial Sources
- Content originating from the World Health Organization (governed by CC BY-NC-SA 3.0 IGO) must **never** be marketed as commercially reusable while third-party permission remains unresolved (`REQUIRED_NOT_SUBMITTED`).

### 6. Strict Prohibition of Endorsement Inferences
- Marketplace listings and client documentation must explicitly state that the CancerInfo API is an independent data aggregation service.
- Listing language must never claim, imply, or suggest that the National Cancer Institute, National Health Service, World Health Organization, Cancer Australia, or Centers for Disease Control and Prevention endorse the CancerInfo API, its maintainers, or downstream client applications.

### 7. Trademarks, Logos, and Media Assets Require Separate Rights
- Departmental crests, NHS blue lozenges, WHO emblem, U.S. Federal seals, Commonwealth coats of arms, and clinical photography are protected trademarks and intellectual property.
- They are excluded from API payloads and must never be used in marketplace promotional collateral without explicit licensing from each respective trademark owner.

