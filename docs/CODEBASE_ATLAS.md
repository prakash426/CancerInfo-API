# CancerInfo API: codebase atlas and launch assessment

## Current route update, November 4, 2026

This atlas preserves its September architecture assessment below. The current runtime OpenAPI has 18 paths: 15 public GET routes, including `GET /v1/facts`, and 3 administrative routes. The checked in marketplace export contains the 15 public paths and excludes admin operations. See [fact ID lookup](FACT_ID_LOOKUP.md) and [public response contract](PUBLIC_RESPONSE_CONTRACT.md) for the current consumer contract. Older path counts and launch status statements below are historical snapshots.

Source reviewed: `1199f735e3d77b5c1ada35e6451c7a5b4e36d063` on `fix/CIAPI-001-ci-dependency-setup`. Review date: September 22, 2026. This is an implementation map and launch assessment, not a deployment certificate.

## Current system context

CancerInfo API is now a Python/FastAPI service for structured cancer-information retrieval. app.main creates the application, middleware, developer landing page and API router. Endpoints validate requests and serialize Pydantic models; repositories read SQLAlchemy data; ingestion and source adapters write the same relational model.

The active tree is app/api/v1/endpoints (HTTP routes), app/core (settings/constants/errors/security), app/database (session), app/models (nine tables), app/repositories (queries), app/schemas (responses), app/normalization (text/taxonomy/hash), app/sources (four adapters), app/ingestion (seed/pipeline), tests, docs and rapidapi. Dockerfile and CI use Python. The root package.json only wraps Python commands; its old lockfile and Firebase/environment scaffolding remain follow-up cleanup.

cancerinfo-explorer-ui and cancerinfo-explorer-ui.zip contain an archived React/Vite client. They are not started by the API image and are not launch requirements. The API still serves /docs, /redoc, /openapi.json and an HTML root portal. No LLM inference, vector database, scheduler or production monitoring service was identified in the Python core.

The primary risks now lie in data correctness, publication controls and release evidence rather than duplicate runtime maintenance. The owner’s target remains October 4, conditional on acceptance.

## Architecture decision record

Accepted owner decision: use Python/FastAPI as the API core and archive the unsolicited Node/React application for future consideration. Bob implemented this at the reviewed SHA. The public service and ingestion now use SQLAlchemy rather than separate Node JSON and Python SQL paths.

Consequences: preserve the 13-route public surface where intended, explicitly review response/validation differences, finish production persistence and migrations, and keep the UI out of API release acceptance. FastAPI’s built-in docs and root HTML portal remain useful developer surfaces and are not a second backend.

Unresolved decisions are the production host/database, migration strategy, publication-state model, exact launch dataset and gateway boundary. PostgreSQL remains the durable target proposed by the earlier plan, not a deployed fact. This documentation branch begins at main and includes the refactor before documentation changes; main itself is not being merged or modified.

## Storage and search

Serving repositories and ingestion share SQLAlchemy models and DATABASE_URL. The default is SQLite, with the committed database copied into the image. PostgreSQL support is configured in code/dependencies, but migrations, operational deployment and restore evidence are absent.

Search is deterministic application logic over SQL substring queries: tokenize lowercased input, infer a category from known tokens, match cancer names/slugs and aliases, query active content with optional filters, assign heuristic scores, then sort/limit. It is not embeddings, vector search or an LLM. Cancer-entity matches are not constrained like filtered content records; review the documented meaning of filters.

Category retrieval includes requested country plus GLOBAL and orders GLOBAL first by its descending boolean expression, despite a contrary comment. Query/pagination stability, case handling, ambiguous aliases and database-dialect behavior need targeted tests. Do not promise full-text performance from the existing ordinary indexes.

## Ingestion architecture

Current flow: source lookup -> registered adapter -> create RUNNING job -> discover finite targets -> fetch HTML -> hash -> skip unchanged document -> parse sections -> resolve/create cancer -> save document -> match/update/create records -> save versions/citations -> commit -> mark source/job healthy/successful. Adapter close runs in finally.

Identity is currently cancer + normalized category + country + active. It omits source, document and section identity, so distinct material can overwrite a record. Citations are only created for new records; updated text can retain the old citation. Removed sections are not retired. Current dates are substituted when source dates are absent.

Unchanged HTML updates document verification time without revalidating all publication requirements. Fetch and parse failures do not necessarily fail the job; all-fetch failure was reproduced as SUCCESS. The exception path commits error state without a rollback after database failure. Version updates archive an existing version number without a uniqueness constraint or historical provenance snapshot.

Implement stable identity, atomic text/provenance/history updates, honest status accounting, rollback-safe logging, nullable unknown dates and a publication gate before a controlled live refresh. These changes are proposed remediation, not part of the current refactor.

## Data dictionary and taxonomy

The implemented schema contains nine SQLAlchemy tables. The refactor did not change those model definitions. The detailed field inventory below is extracted from the reviewed models, including SQL types, nullability, primary keys and foreign-key targets. Application defaults and business requirements must not be confused with database constraints.

Fresh seed and committed SQLite counts match structurally: 7 cancers, 22 aliases, 5 sources, 20 documents, 21 content records, 21 citations, 21 versions, 5 source-health rows and 0 ingestion jobs. Five cancers and five categories have content; 37 category definitions do not mean 37 populated sections. Taxonomy codes already exist as JSON fields; their correctness and source provenance still require review.

Cancer resolution checks exact slug/ID, normalized canonical name, then exact alias. Alias review_status is not enforced by the resolver. Category normalization falls back to overview for unknown input, which currently defeats the endpoint’s category-not-found check. The database has no versioned migration chain in this branch.

### Implemented tables and fields

#### cancers

| Field | SQL type | Nullable | Key |
| :--- | :--- | :--- | :--- |
| id | VARCHAR(36) | no | primary key |
| slug | VARCHAR(128) | no | none |
| canonical_name | VARCHAR(255) | no | none |
| description | TEXT | yes | none |
| anatomical_site | VARCHAR(128) | yes | none |
| parent_cancer_id | VARCHAR(36) | yes | FK cancers.id |
| taxonomy_codes | JSON | yes | none |
| created_at | DATETIME | yes | none |
| updated_at | DATETIME | yes | none |

#### sources

| Field | SQL type | Nullable | Key |
| :--- | :--- | :--- | :--- |
| id | VARCHAR(64) | no | primary key |
| organization_name | VARCHAR(255) | no | none |
| source_name | VARCHAR(255) | no | none |
| base_url | VARCHAR(512) | no | none |
| country_code | VARCHAR(10) | no | none |
| region | VARCHAR(100) | yes | none |
| source_type | VARCHAR(100) | no | none |
| trust_tier | VARCHAR(100) | no | none |
| authority_type | VARCHAR(100) | no | none |
| default_language | VARCHAR(10) | yes | none |
| supported_languages | JSON | yes | none |
| license_type | VARCHAR(255) | no | none |
| license_status | VARCHAR(50) | no | none |
| reuse_allowed | BOOLEAN | yes | none |
| full_text_storage_allowed | BOOLEAN | yes | none |
| derived_summary_allowed | BOOLEAN | yes | none |
| attribution_required | BOOLEAN | yes | none |
| attribution_text | VARCHAR(512) | yes | none |
| reuse_policy_url | VARCHAR(512) | yes | none |
| terms_url | VARCHAR(512) | yes | none |
| robots_url | VARCHAR(512) | yes | none |
| ingestion_method | VARCHAR(50) | yes | none |
| crawl_frequency | VARCHAR(50) | yes | none |
| priority | INTEGER | yes | none |
| active | BOOLEAN | yes | none |
| date_added | DATETIME | yes | none |
| last_reviewed | DATETIME | yes | none |
| notes | TEXT | yes | none |

#### cancer_aliases

| Field | SQL type | Nullable | Key |
| :--- | :--- | :--- | :--- |
| id | VARCHAR(36) | no | primary key |
| cancer_id | VARCHAR(36) | no | FK cancers.id |
| alias | VARCHAR(255) | no | none |
| language | VARCHAR(10) | yes | none |
| alias_type | VARCHAR(64) | yes | none |
| country_code | VARCHAR(10) | yes | none |
| confidence | FLOAT | yes | none |
| review_status | VARCHAR(32) | yes | none |

#### content_records

| Field | SQL type | Nullable | Key |
| :--- | :--- | :--- | :--- |
| id | VARCHAR(36) | no | primary key |
| canonical_cancer_id | VARCHAR(36) | no | FK cancers.id |
| category | VARCHAR(64) | no | none |
| subcategory | VARCHAR(64) | yes | none |
| content | TEXT | no | none |
| content_type | VARCHAR(64) | yes | none |
| country_code | VARCHAR(10) | no | none |
| region_code | VARCHAR(32) | yes | none |
| jurisdiction_scope | VARCHAR(32) | yes | none |
| language | VARCHAR(10) | yes | none |
| audience | VARCHAR(32) | yes | none |
| disagreement_status | VARCHAR(32) | yes | none |
| disagreement_notes | TEXT | yes | none |
| active | BOOLEAN | yes | none |
| version_number | INTEGER | yes | none |
| created_at | DATETIME | yes | none |
| updated_at | DATETIME | yes | none |

#### ingestion_jobs

| Field | SQL type | Nullable | Key |
| :--- | :--- | :--- | :--- |
| id | VARCHAR(36) | no | primary key |
| source_id | VARCHAR(64) | no | FK sources.id |
| start_time | DATETIME | yes | none |
| end_time | DATETIME | yes | none |
| status | VARCHAR(32) | yes | none |
| pages_discovered | INTEGER | yes | none |
| pages_retrieved | INTEGER | yes | none |
| pages_changed | INTEGER | yes | none |
| records_created | INTEGER | yes | none |
| records_updated | INTEGER | yes | none |
| records_rejected | INTEGER | yes | none |
| parser_failures | INTEGER | yes | none |
| error_details | JSON | yes | none |

#### source_documents

| Field | SQL type | Nullable | Key |
| :--- | :--- | :--- | :--- |
| id | VARCHAR(36) | no | primary key |
| source_id | VARCHAR(64) | no | FK sources.id |
| original_url | VARCHAR(1024) | no | none |
| canonical_url | VARCHAR(1024) | yes | none |
| title | VARCHAR(512) | no | none |
| source_document_type | VARCHAR(64) | yes | none |
| source_cancer_name | VARCHAR(255) | yes | none |
| canonical_cancer_id | VARCHAR(36) | yes | FK cancers.id |
| language | VARCHAR(10) | yes | none |
| country_code | VARCHAR(10) | no | none |
| jurisdiction_scope | VARCHAR(32) | yes | none |
| published_at | DATETIME | yes | none |
| source_updated_at | DATETIME | yes | none |
| retrieved_at | DATETIME | yes | none |
| last_verified_at | DATETIME | yes | none |
| content_hash | VARCHAR(64) | no | none |
| http_etag | VARCHAR(128) | yes | none |
| http_last_modified | VARCHAR(128) | yes | none |
| parser_version | VARCHAR(32) | yes | none |
| processing_status | VARCHAR(32) | yes | none |
| license_status | VARCHAR(32) | yes | none |

#### source_health

| Field | SQL type | Nullable | Key |
| :--- | :--- | :--- | :--- |
| id | VARCHAR(36) | no | primary key |
| source_id | VARCHAR(64) | no | FK sources.id |
| last_check | DATETIME | yes | none |
| is_reachable | BOOLEAN | yes | none |
| http_status | INTEGER | yes | none |
| consecutive_failures | INTEGER | yes | none |
| last_successful_crawl | DATETIME | yes | none |
| alert_status | VARCHAR(32) | yes | none |

#### content_sources

| Field | SQL type | Nullable | Key |
| :--- | :--- | :--- | :--- |
| id | VARCHAR(36) | no | primary key |
| content_record_id | VARCHAR(36) | no | FK content_records.id |
| source_id | VARCHAR(64) | no | FK sources.id |
| source_document_id | VARCHAR(36) | yes | FK source_documents.id |
| source_url | VARCHAR(1024) | no | none |
| source_updated_at | DATETIME | yes | none |
| retrieved_at | DATETIME | yes | none |
| last_verified_at | DATETIME | yes | none |
| quote_snippet | TEXT | yes | none |
| attribution_text | VARCHAR(512) | yes | none |

#### content_versions

| Field | SQL type | Nullable | Key |
| :--- | :--- | :--- | :--- |
| id | VARCHAR(36) | no | primary key |
| content_record_id | VARCHAR(36) | no | FK content_records.id |
| version_number | INTEGER | no | none |
| content | TEXT | no | none |
| change_type | VARCHAR(32) | yes | none |
| change_reason | TEXT | yes | none |
| content_hash | VARCHAR(64) | no | none |
| created_at | DATETIME | yes | none |

### Defined category slugs

`overview`, `types_and_subtypes`, `symptoms`, `signs`, `causes`, `risk_factors`, `prevention`, `screening`, `early_detection`, `diagnosis`, `diagnostic_tests`, `grading`, `staging`, `biomarkers`, `genetics`, `treatment`, `surgery`, `chemotherapy`, `radiation_therapy`, `immunotherapy`, `targeted_therapy`, `hormone_therapy`, `stem_cell_transplant`, `supportive_care`, `side_effects`, `prognosis`, `survival`, `recurrence`, `follow_up`, `palliative_care`, `living_with_cancer`, `caregiver_information`, `childhood_cancer`, `research`, `statistics`, `clinical_trials`, `terminology`.


### Seed coverage verified locally

| Cancer | Records | Populated categories |
| :--- | :--- | :--- |
| breast-cancer | 9 | overview, risk_factors, screening, symptoms, treatment |
| colorectal-cancer | 5 | overview, screening, symptoms |
| lung-cancer | 3 | overview, risk_factors, symptoms |
| prostate-cancer | 2 | overview, symptoms |
| pancreatic-cancer | 2 | overview, symptoms |
| cervical-cancer | 0 | none |
| melanoma | 0 | none |


## Provenance schema

The implemented relational chain is Source -> SourceDocument -> ContentSource -> ContentRecord, with ContentVersion linked to ContentRecord. A content record can have multiple citation links; a citation’s source_document_id is nullable. Documents carry URLs/hash/parser and date metadata, while citation links carry exact source_url, attribution and quote snippet.

The schema does not enforce reviewed publication state, unique document/section record identity or unique (content_record_id, version_number). ContentVersion stores text/hash/change metadata without a citation snapshot. Existing ingestion can therefore leave current text and cited provenance out of sync and cannot reconstruct every historical citation state.

SourceDocument and ContentSource have distinct retrieval and verification fields, but current seed/adapters/pipeline fill dates from the current clock. Do not equate these fields with evidence of publisher updates or clinical review. The data dictionary below is the implementation reference; proposed migration and constraints require tests and an explicit schema version.

## Source registry status

The seed registers five sources: NCI, WHO, NHS, Cancer Australia and CDC. Only four adapters are registered: nci-us, who-global, nhs-uk and cancer-australia. CDC registration does not imply a working CDC ingestion adapter or published content.

Registry rights booleans and APPROVED labels are seed/configuration values. Their presence is not proof of exact-document clearance. Source health is also not reliable evidence yet: the mocked all-fetch-failure run finished HEALTHY.

Keep source identity, document permissions, adapter support, successful retrieval and publication eligibility as separate statuses. Do not advertise global or multi-country completeness from these registry names. The launch source list must follow the reviewed corpus and enforced gates.

## Ingestion profiles

Adapters use finite, hardcoded discovery lists rather than broad crawling: NCI 5 URLs, WHO 4, NHS 5 and Cancer Australia 4 in the reviewed code. Each uses HTTP fetching and HTML normalization into a document with sections. No scheduled refresh job is committed.

The base client follows redirects, uses a 20-second timeout and returns empty values for non-200 responses or exceptions. The pipeline skips empty fetches and currently records overall success. ETag and Last-Modified values are fetched but not passed through to the stored document. Publisher dates fall back to current time in adapters.

For each source, maintain fixtures representing actual page structure, missing headings/dates, redirects, changed and removed sections, empty/invalid HTML and permission boundaries. A controlled live freshness run should follow rights and parser review; none was performed in this assessment.

### Discovery targets in code

#### nci-us

- https://www.cancer.gov/types/breast (breast-cancer)
- https://www.cancer.gov/types/lung (lung-cancer)
- https://www.cancer.gov/types/colorectal (colorectal-cancer)
- https://www.cancer.gov/types/prostate (prostate-cancer)
- https://www.cancer.gov/types/pancreatic (pancreatic-cancer)

#### who-global

- https://www.who.int/news-room/fact-sheets/detail/breast-cancer (breast-cancer)
- https://www.who.int/news-room/fact-sheets/detail/lung-cancer (lung-cancer)
- https://www.who.int/news-room/fact-sheets/detail/colorectal-cancer (colorectal-cancer)
- https://www.who.int/news-room/fact-sheets/detail/cervical-cancer (cervical-cancer)

#### nhs-uk

- https://www.nhs.uk/conditions/breast-cancer/ (breast-cancer)
- https://www.nhs.uk/conditions/lung-cancer/ (lung-cancer)
- https://www.nhs.uk/conditions/bowel-cancer/ (colorectal-cancer)
- https://www.nhs.uk/conditions/prostate-cancer/ (prostate-cancer)
- https://www.nhs.uk/conditions/pancreatic-cancer/ (pancreatic-cancer)

#### cancer-australia

- https://www.canceraustralia.gov.au/cancer-types/breast-cancer (breast-cancer)
- https://www.canceraustralia.gov.au/cancer-types/lung-cancer (lung-cancer)
- https://www.canceraustralia.gov.au/cancer-types/bowel-cancer (colorectal-cancer)
- https://www.canceraustralia.gov.au/cancer-types/prostate-cancer (prostate-cancer)


## Endpoints and examples

The active API has 13 public GET paths and 2 admin POST paths. Public paths are listed below from app.openapi(); health aliases and documentation routes are intentionally outside that generated API path inventory.

Local examples: GET /v1/cancers; GET /v1/cancers/breast-cancer/symptoms?country=US; GET /v1/search?q=CRC; GET /v1/coverage. These exercise seeded demonstration content, not a certified clinical dataset. Valid empty coverage must remain distinguishable from malformed input and server failure.

Use /v1/health for database/registry metadata; /health and /api/health only return process liveness. Do not publish /v1/admin/ingest or /v1/admin/seed in the consumer listing. No aggregate view=full implementation was found.

### Generated path inventory

- `GET /v1/health`
- `GET /v1/cancers`
- `GET /v1/cancers/{cancer}`
- `GET /v1/cancers/{cancer}/sections`
- `GET /v1/cancers/{cancer}/sources`
- `GET /v1/cancers/{cancer}/versions`
- `GET /v1/cancers/{cancer}/{category}`
- `GET /v1/search`
- `GET /v1/sources`
- `GET /v1/sources/{id}`
- `GET /v1/categories`
- `GET /v1/countries`
- `GET /v1/coverage`
- `POST /v1/admin/ingest`
- `POST /v1/admin/seed`

## Authentication rate limits and errors

Public GET routes have no application API-key requirement in the reviewed code. Admin POST routes accept X-Admin-Key or Bearer authorization. The configuration’s development key must not be accepted in production. No RapidAPI proxy-secret/origin enforcement was identified.

The limiter defaults to 120 requests per minute per in-memory client key, trusts X-Forwarded-For and is not shared across workers. Its reset calculation yields a fixed 60-second value. Exempt paths include root, documentation, schema and health. The isolated limit probe returned 429 with Retry-After but without X-Request-ID or medical disclaimer headers.

Custom errors use error.code/message/details; invalid page=0 returned framework detail[] with HTTP 422. Health uses a direct response model. Agree and test the intended contract before claiming consistent errors. Production proxy trust, CORS origins, secret handling and rate behavior remain launch work.

## API specification status

FastAPI generates OpenAPI 3.1.0 with 15 paths: 13 public GET and 2 admin POST. The static rapidapi/rapidapi-openapi.json remains at 8 paths and includes an unverified example production hostname. It must not be imported as a complete release contract.

Generate a public-only artifact from the chosen candidate, removing admin operations and checking response/error schemas, query bounds, headers, server URL and examples against HTTP tests. Keep the full internal contract distinct. A successful app.openapi() call only proves generation, not marketplace compatibility or complete schema validation.

The Python CI now generates a schema but does not compare it against the committed marketplace file. Add a drift gate under CIAPI-014/013. The Postman collection also needs parity verification against the accepted contract before external sharing.

## Code verified audit reconciliation

The reviewed branch contains the owner-requested Python-core refactor. Node server.ts, src/server/api.ts, the JSON serving dataset and the old Google Drive service were removed. React assets were moved to cancerinfo-explorer-ui and a ZIP. Docker and CI now target Python. app/main.py adds health aliases, headers, CORS-exposed headers and an expanded HTML developer portal; two health/header tests bring the suite to 28.

Important correction to the schema-change assumption: the SQLAlchemy model definitions, ingestion pipeline, seed, repositories and adapters are unchanged by this refactor relative to the preceding merged tree. The runtime architecture is simpler, but the core data integrity defects persist. The root HTML docs portal still exists inside FastAPI and is separate from the archived React app.

Closed historical work: the earlier npm lockfile fix. Structurally removed concerns: Node JSON versus Python serving divergence, Node runtime dependencies in the API image and tracked bytecode. Partially improved: container packaging and single-store access. Still open: production durability/migrations, provenance identity/history, honest timestamps, source rights/publication, admin/proxy controls, contract drift, curated corpus, deployment and RapidAPI acceptance.

Four isolated diagnostic failures were reproduced: unknown category returns overview (200); an inactive/restricted source still returns content (200); all fetches fail but ingestion reports SUCCESS/HEALTHY; 429 lacks request/disclaimer headers. Invalid pagination correctly returns 422. These results explain why the green 28-test suite cannot certify launch readiness.

The original audit and Recommended Plan remain unchanged historical inputs. This current assessment supersedes their runtime assumptions and any old estimate presented as current. Notion reconciliation is explicitly deferred.

### Reassessed launch work, proposed remaining hands-on hours

| ID | Current disposition | Hours |
| :--- | :--- | :--- |
| CIAPI-001 | Historical npm fix complete; Python candidate CI remains unverified under CIAPI-013. | 0–0 |
| CIAPI-002 | Python packaging improved; boot, port and persistence acceptance open. | 2–4 |
| CIAPI-003 | Python choice accepted; contract freeze open. | 1–2 |
| CIAPI-004 | Single data path achieved; migrations, durable deployment and restore open. | 3–5 |
| CIAPI-005 | Identity and citation-update defects remain. | 4–6 |
| CIAPI-006 | Current-time substitution remains. | 2–3 |
| CIAPI-007 | All-fetch failure reproduced as SUCCESS. | 2–4 |
| CIAPI-008 | Exact-document rights and quarantine open. | 3–5 |
| CIAPI-009 | 21 seed records are not a certified corpus. | 6–10 |
| CIAPI-010 | Restricted-source publication reproduced. | 2–4 |
| CIAPI-011 | Production key, proxy, CORS and limiter checks open. | 3–5 |
| CIAPI-012 | Unknown-category fallback reproduced; alias review needed. | 2–4 |
| CIAPI-013 | 28 tests pass; meaningful missing regression/image gates remain. | 3–5 |
| CIAPI-014 | 15 generated paths vs 8 static; public export must exclude admin. | 2–3 |
| CIAPI-015 | No staging or restore evidence. | 3–5 |
| CIAPI-016 | Account, import and consumer acceptance not performed. | 2–3 |
| CIAPI-017 | History uniqueness/provenance and controlled refresh open. | 3–5 |
| CIAPI-018 | Final candidate acceptance and release approval open. | 3–4 |

Total proposed remaining effort: 46–77 hours before contingency; with 20 percent contingency, about 55–92 hours. This is a planning estimate, not a measured completion forecast. Tasks overlap in verification, so revise after implementation evidence. Source permissions and marketplace waiting time are excluded.


## Launch acceptance checklist

Release remains NOT READY. All gates require evidence on the final candidate, not on this documentation branch alone.

1. One Python serving entry point and an agreed public contract, including deliberate changes from the removed Node API.
2. Green CI for the candidate; image build, isolated boot, port, shutdown and dependency reproducibility checks.
3. Durable database, versioned migration, controlled seed behavior, restart persistence and successful restore.
4. Correct source/document/section identity, atomic citation updates, honest timestamps, accurate ingestion failure states and coherent history.
5. Document-level rights and content review for every published record, enforced across every public output path.
6. Production secrets, admin isolation, trusted proxy/rate behavior and consistent error/safety headers.
7. Complete public OpenAPI and working consumer examples with no unverified readiness or clinical guarantees.
8. Staging/live readiness, monitoring, gateway checks and independent RapidAPI consumer acceptance.

The 28 passing local tests satisfy a regression baseline only. Reproduced publication, ingestion, category and 429-header defects keep the relevant acceptance gates open.

## Roadmap and capacity

October 4, 2026 remains the launch target. September 27 is the planned accepted-candidate/RapidAPI submission checkpoint for a full week of lead time; September 28 is the adjustable fallback and leaves six days. This plan is conditional on evidence, not a commitment that the remaining work fits.

Proposed sequence: September 22–23 finalize Python contract and deployment decisions, source-rights shortlist, CI trigger/run and startup/durability fixes. September 23–25 repair ingestion identity, citations, dates, failures/history and enforce publication controls. September 25–26 curate the actual launch corpus, finish production configuration, public OpenAPI, image/staging tests and restore. September 27 run final acceptance and submit the listing if all gates pass. September 28–October 3 handle review feedback, independent consumer tests, monitoring and remediation. October 4 launch only the accepted release.

The prior 52–85-hour estimate belongs to the dual-runtime baseline and is retained below as history. The revised task-level estimate below is an engineering planning range, not measured effort. It credits runtime consolidation but does not assume data-integrity work disappeared. It excludes external review waits and assumes a limited reviewed corpus. Re-estimate after the first two substantive fixes; the owner’s available hours have not been reconfirmed.

Do not assign a lower bug count merely because the directory is cleaner. Keep existing task IDs, retire obsolete implementation details and test the remaining acceptance outcomes. Notion dates/statuses will be reconciled in the next phase.

### Reassessed launch work, proposed remaining hands-on hours

| ID | Current disposition | Hours |
| :--- | :--- | :--- |
| CIAPI-001 | Historical npm fix complete; Python candidate CI remains unverified under CIAPI-013. | 0–0 |
| CIAPI-002 | Python packaging improved; boot, port and persistence acceptance open. | 2–4 |
| CIAPI-003 | Python choice accepted; contract freeze open. | 1–2 |
| CIAPI-004 | Single data path achieved; migrations, durable deployment and restore open. | 3–5 |
| CIAPI-005 | Identity and citation-update defects remain. | 4–6 |
| CIAPI-006 | Current-time substitution remains. | 2–3 |
| CIAPI-007 | All-fetch failure reproduced as SUCCESS. | 2–4 |
| CIAPI-008 | Exact-document rights and quarantine open. | 3–5 |
| CIAPI-009 | 21 seed records are not a certified corpus. | 6–10 |
| CIAPI-010 | Restricted-source publication reproduced. | 2–4 |
| CIAPI-011 | Production key, proxy, CORS and limiter checks open. | 3–5 |
| CIAPI-012 | Unknown-category fallback reproduced; alias review needed. | 2–4 |
| CIAPI-013 | 28 tests pass; meaningful missing regression/image gates remain. | 3–5 |
| CIAPI-014 | 15 generated paths vs 8 static; public export must exclude admin. | 2–3 |
| CIAPI-015 | No staging or restore evidence. | 3–5 |
| CIAPI-016 | Account, import and consumer acceptance not performed. | 2–3 |
| CIAPI-017 | History uniqueness/provenance and controlled refresh open. | 3–5 |
| CIAPI-018 | Final candidate acceptance and release approval open. | 3–4 |

Total proposed remaining effort: 46–77 hours before contingency; with 20 percent contingency, about 55–92 hours. This is a planning estimate, not a measured completion forecast. Tasks overlap in verification, so revise after implementation evidence. Source permissions and marketplace waiting time are excluded.


## Source rights assessment

These are project publication decisions based on official policy pages reviewed on September 22, not blanket legal clearance. Exact documents and intended redistribution still require approval evidence.

NCI’s reuse policy generally permits its text unless otherwise indicated and requires source credit; graphics and trademarks have separate conditions. NHS permits specified reuse under its terms/OGL with exceptions and rules for attribution, freshness and adaptation. WHO’s publication licenses include noncommercial conditions and item-specific exceptions; free API access alone does not settle downstream rights. The retrieved Cancer Australia copyright page reserves rights beyond specified uses and does not support the seed’s blanket CC BY label; its retrieved page is an older cached representation and exact current-document permission remains unresolved.

Retain unresolved material outside the published corpus until reviewed. Record document URL, policy URL, checked date, allowed storage/redistribution/derivation, attribution, restrictions and evidence of permission. Source APPROVED flags and trust tiers must not substitute for that record.

### Official policy references

- [NCI reuse policy](https://www.cancer.gov/policies/copyright-reuse)
- [NHS terms](https://www.nhs.uk/our-policies/terms-and-conditions/)
- [WHO copyright and permissions](https://www.who.int/about/policies/publishing/copyright)
- [Cancer Australia copyright](https://www.canceraustralia.gov.au/copyright)


## Learning and verification sequence

Trace a request from `app/main.py` through `app/api/v1/router.py`, the endpoint, repository, model and response schema. Then follow one fixture from source adapter through normalization, pipeline, document, record, citation and version. Compare actual stored values with endpoint output and generated OpenAPI. Finally inspect container startup, CI and deployment evidence as separate layers.

For each module record its callers, inputs, outputs, database writes, error handling and tests. The schema inventory is exhaustive for model columns; it is not a claim that every execution branch was tested. The current gaps are explicitly listed above so source understanding and runtime proof remain distinguishable.
