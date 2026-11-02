# Public response contract: CIAPI-L010

This change freezes response behavior for the existing Python API. It does not certify publication eligibility, clinical review, source rights, or release readiness. The pending profile, comparison and trial endpoints remain separate tasks.

## Identity and category resolution

Exact cancer ID and slug take precedence. Canonical names and space/hyphen variations resolve deterministically. Only aliases with `review_status=APPROVED` may resolve. Multiple reviewed aliases identifying different cancers return HTTP 409 with `AMBIGUOUS_CANCER`; use a canonical ID or slug. Unknown or unreviewed-only identifiers return 404 `CANCER_NOT_FOUND`.

Public category parameters accept canonical categories, their space/hyphen forms, and explicit entries in `CATEGORY_ALIASES`. Unknown categories return 404 `CATEGORY_NOT_FOUND`. Document-heading heuristics remain confined to ingestion. A valid category without content returns 200 with empty collections and zero record totals.

## Country and filtering

Raw category records and search records use requested-country plus GLOBAL fallback. Country values are trimmed and uppercased. Requested-country records precede GLOBAL when their ranking is otherwise equal. Without a country filter, GLOBAL precedes other countries in category records; ties use creation time and record ID.

Consensus represents universal facts in the current model: country personalizes corroborating citations rather than hiding facts. Matching country and GLOBAL citations are selected when available, with matching country first; if none exists, citations from other jurisdictions are retained. This is citation selection, not proof of universal clinical applicability. Jurisdiction-sensitive content validation and publication labels remain L008/L012 responsibilities.

Search source filters apply to records and consensus facts. Consensus citations are restricted to the selected source before country personalization. Explicit category, country, source or audience filters exclude untyped cancer-entity search hits. Audience-filtered search excludes consensus facts, because the current consensus model has no audience field. Unknown source/audience filters return no matching evidence. Category responses retain their legacy universal consensus collection, while country/audience/source/language filters apply to their raw records.

## Pagination

Search adds optional `page` (default 1, minimum 1) while retaining `limit` (default 20, 1 through 50). All matching cancer, consensus and record results are ranked together before page slicing. Order is score descending, requested-country rank for raw records, match type, cancer ID, then result ID. Totals refer to the complete filtered result set. A page beyond the end is empty. Pagination is stable for an unchanged database; it is not a snapshot across concurrent refreshes.

Category `page` and `limit` paginate `records`. Legacy `items` remain a separate unpaginated consensus collection, with `consensus_summary.total_items` recording its size. Category pagination totals count records; `meta.result_count` counts returned records plus returned consensus items. Duplicate citations cannot duplicate record totals. Cancer-list order uses canonical name then ID.

Current search ranking materializes matching results before slicing. Large-corpus optimization and performance acceptance belong to L014/L030; these tests do not establish load performance.

## Errors and compatibility changes

Errors use `error.code`, `error.message`, and `error.details`. Domain errors retain their named codes. Request validation returns 422 `VALIDATION_ERROR` with locations, types and messages, without submitted inputs or request bodies. Router errors return 404 `NOT_FOUND` or 405 `METHOD_NOT_ALLOWED`, preserving the Allow header. Unexpected failures return a generic 500 without exception names or messages. Rate-limit responses retain 429 `RATE_LIMIT_EXCEEDED` and retry headers.

Intentional corrections: unknown categories no longer silently return overview; unreviewed aliases no longer resolve; colliding aliases return 409; search filters now apply across evidence types; pagination metadata counts the collection actually paginated; validation and router errors now use the API envelope. Existing successful response fields and routes remain available.

Handlers follow the [official FastAPI error-handling guidance](https://fastapi.tiangolo.com/tutorial/handling-errors/). Runtime OpenAPI references the error schema. Committed consumer specification generation and RapidAPI import remain L013 acceptance work.

## Root, probes and headers

Root `/` returns JSON when Accept contains application/json without text/html. Otherwise it returns the HTML developer portal. `/health` and `/api/health` return the lightweight `status: ok` probe; `/v1/health` returns the versioned application health envelope. Probes are not database persistence or launch-readiness evidence.

Ordinary application responses carry request ID, response time, rate limits, disclaimer and API-version headers from the existing middleware. The middleware's early rate-limit response retains retry/rate headers; completing its broader header and trust controls belongs to L011.

## Runtime route inventory

The current runtime OpenAPI contains 15 paths: 13 public and 2 administrative. Framework documentation, root and probe aliases are separate routes excluded from that inventory.

- Administrative: `POST /v1/admin/ingest`
- Administrative: `POST /v1/admin/seed`
- Public: `GET /v1/cancers`
- Public: `GET /v1/cancers/{cancer}`
- Public: `GET /v1/cancers/{cancer}/sections`
- Public: `GET /v1/cancers/{cancer}/sources`
- Public: `GET /v1/cancers/{cancer}/versions`
- Public: `GET /v1/cancers/{cancer}/{category}`
- Public: `GET /v1/categories`
- Public: `GET /v1/countries`
- Public: `GET /v1/coverage`
- Public: `GET /v1/health`
- Public: `GET /v1/search`
- Public: `GET /v1/sources`
- Public: `GET /v1/sources/{id}`
