# CancerInfo API Validation & Quality Assurance Guide

## Current guidance, September 22, 2026

This guide applies to Python refactor `1199f735e3d77b5c1ada35e6451c7a5b4e36d063`. Current guidance below supersedes the prior draft retained at the end.

### Acceptance evidence baseline

Validation on the reviewed refactor: dependency installation succeeded in an isolated environment; Python 3.12.2 pytest completed with 28 passed and 425 warnings in 0.24 seconds. Warnings include deprecated datetime and client APIs. The run does not provide coverage percentage, Python 3.10 CI evidence, Python 3.11 image evidence, PostgreSQL compatibility or clinical validation.

The runtime OpenAPI generates 15 paths: 13 public GET routes plus 2 administrative POST routes. The committed marketplace specification still has only 8 paths. Diagnostic probes reproduced invalid-category fallback, restricted-source exposure, false ingestion success and missing request/disclaimer headers on 429 responses. Invalid page=0 correctly returned 422, with the framework detail envelope.

GitHub returned zero workflow runs for this source SHA at the review check. CI triggers main/master pushes or pull requests targeting those branches; the refactor is on the task branch. Docker is unavailable in this environment, so image build/boot is unverified. No deployed revision, public URL, RapidAPI import or consumer acceptance was established. Launch acceptance remains open.

### Test strategy

The service under test is app.main:app. The archived React client is outside API release gates. Existing tests now total 28 and all pass locally, but reproduced defects show the suite does not enforce the full launch acceptance criteria.

Use four layers: pure normalization/parser fixtures; transaction-level ingestion and provenance tests; FastAPI HTTP contract and publication tests; deployed-image/database/gateway acceptance. Include rights-denied content, no citations, removed sections, unavailable sources, rollback, unknown dates, source collisions, ambiguous aliases and error headers. Validate migration and restore on the chosen production database.

Keep fixtures deterministic and separate from the startup seed database. Record source SHA, dependency versions, interpreter, commands, output, dataset identity and any skipped gate. Unit or local API success cannot substitute for deployed-image or marketplace verification.

### Data and provenance test matrix

The active data path is SQLAlchemy, not the removed JSON server. Read-only inspection of the committed SQLite file and an independently seeded temporary SQLite database both found 7 cancers, 22 aliases, 5 sources, 20 source documents, 21 content records, 21 citation links, 21 content versions, 5 source-health rows and 0 ingestion jobs before diagnostic probes. Equal row counts do not establish identical content, clinical accuracy or permission to publish.

A controlled probe set an existing source inactive, reuse disallowed and license RESTRICTED. Its breast-cancer symptoms still returned HTTP 200 with one record and RESTRICTED provenance. A mocked adapter with one discovered URL and no successful fetch returned SUCCESS and HEALTHY. These are reproduced failures, not hypothetical requirements.

Retain the original fixture matrix below. Add assertions for publication exclusion across category, search, sections, sources, history and coverage; timestamp nullability; duplicate version numbers; source-specific record identity; stale citations; and removed sections. Fixture-based tests must use a temporary database and never the committed database or production content.

### API contract test matrix

The current contract baseline is generated from FastAPI. Record the exact 13 public GET routes, query bounds and response models; separately record the two admin POST routes so they cannot accidentally enter a public marketplace export. Test both normal and error envelopes and all documented headers.

Observed behavior: /health and /api/health return {"status":"ok"}; /v1/health returns registry/database metadata without the standard data envelope. An unknown category on a known cancer returns overview with HTTP 200. page=0 returns 422 with detail[], while custom API errors use error.code/message/details. The early 429 path omits request ID and disclaimer headers.

Cancer resolution uses exact normalized slug, ID, canonical name, then exact alias, unlike the earlier Node partial matcher. Duplicate aliases remain ambiguous because first match wins without review-status filtering. Country filters include GLOBAL records. Add explicit compatibility decisions for these behaviors, determinism at pagination boundaries, source filtering, missing content and zero-result search before freezing the contract.

### Performance and reliability plan

Performance remains unmeasured for the deployment candidate. The 0.24-second pytest result is suite execution time on local fixtures, not endpoint latency or load capacity. No production load, soak, database outage, restart, backup or restore test was run in this assessment.

Measure the Python service and selected database together: cold start, first request, category lookup, filtered search, coverage, concurrency, p50/p95/p99 latency, error rate, memory and connection usage. Set thresholds against expected launch demand and hosting limits before executing the test. Search uses SQL substring matching and Python ranking; coverage performs multiple queries. Neither an indexed full-text engine nor a distributed cache is implemented.

The rate limiter is process-local and retains client keys. Test multiple workers and gateway forwarding, not just sequential requests from one client. Readiness must fail for unavailable storage or an unusable published dataset. The current /health and /api/health routes only report process liveness.

### Launch acceptance checklist

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

### Reproduce the local regression baseline

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
DATABASE_URL=sqlite:////tmp/cancerinfo-tests.db python -m pytest tests/ -v
python -c 'from app.main import app; print(len(app.openapi()["paths"]))'
```

For an HTTP smoke test, start the service using a separate database and inspect GET responses with headers. A HEAD response does not prove the GET route contract.

```bash
curl -i http://localhost:3000/v1/health
curl -i 'http://localhost:3000/v1/cancers/breast-cancer/symptoms?country=US'
curl -i 'http://localhost:3000/v1/cancers?page=0'
curl -i http://localhost:3000/openapi.json
```

The checked-in unit suite uses an in-memory SQLite fixture, while application lifespan can also initialize DATABASE_URL. Set the environment variable before importing the app to keep startup away from the committed database. The diagnostic review used mocked failed fetches and isolated SQLite; it did not fetch live medical pages.

## Historical draft, not current instructions or verified claims

The following original draft is retained to preserve review history. It may contain obsolete commands, unsupported numbers, clinical examples and unverified readiness claims. Do not execute or publish those claims without replacing them with the current accepted implementation and evidence.

## CancerInfo API Validation & Quality Assurance Guide

This guide describes how to validate the CancerInfo API codebase, test endpoints, check OpenAPI schemas, and ensure compliance prior to publishing.

---

### 1. Automated Test Suite (pytest)

The codebase includes a comprehensive pytest suite testing every endpoint, normalizer, and adapter.

#### Run all tests:

```bash
python3 -m pytest tests/ -v
```

#### Coverage by test module:

- `tests/test_health.py`: Database connectivity, uptime counter, and registry count verification.
- `tests/test_cancers.py`: Canonical cancer retrieval, alias resolution, pagination, section availability.
- `tests/test_consensus_facts.py`: Decoupled biological consensus facts, multi-source corroboration, and presentation search.
- `tests/test_search.py`: Term matching, multi-word matching, clinical abbreviation resolution (`CRC` -> `colorectal-cancer`).
- `tests/test_sources.py`: Trust tier verification, license compliance, URL validation.
- `tests/test_taxonomy_and_normalization.py`: 37-category schema validation, HTML stripping, bullet point extraction.
- `tests/test_admin_and_pipeline.py`: Ingestion pipelines and seed scripts.
- `tests/test_migrations.py`: Alembic schema migration, head revision matching, idempotency, legacy `cancer_content` preservation, production configuration validation.
- `tests/test_bootstrap.py`: Explicit CLI bootstrap, dry-run mode, single-transaction execution, rollback on error, repeated execution refusal, non-mutating startup verification.

---

### 2. API Endpoint Health & Smoke Testing

To test the live running server:

```bash
## 1. Health & Database Check
curl -s http://localhost:3000/v1/health | jq .

## 2. Breast Cancer Symptoms (US Provenance)
curl -s "http://localhost:3000/v1/cancers/breast-cancer/symptoms?country=US" | jq .

## 3. Colorectal Cancer Screening (UK NHS Provenance)
curl -s "http://localhost:3000/v1/cancers/colorectal-cancer/screening?country=GB" | jq .

## 4. Search Acronym Resolution
curl -s "http://localhost:3000/v1/search?q=CRC" | jq .

## 5. Global Coverage Transparency
curl -s "http://localhost:3000/v1/coverage" | jq .
```

---

### 3. Response Headers Validation

Confirm that required auditing and safety headers are present on every HTTP response:

```bash
curl -s -I "http://localhost:3000/v1/cancers"
```

Verify these headers:

- `x-request-id`: Unique UUID4 generated per request.
- `x-response-time-ms`: Server execution latency in milliseconds.
- `x-ratelimit-limit` & `x-ratelimit-remaining`: Sliding window rate limit status.
- `x-disclaimer`: Medical safety disclaimer (`Informational API only. Not medical advice.`).

---

### 4. OpenAPI Specification Validation

Validate the OpenAPI schema using standard Python-native verification:

```bash
## Verify openapi.json is served with valid JSON
curl -s http://localhost:3000/openapi.json | jq .info.title

## Python-native OpenAPI route and schema generation check:
python -c "from app.main import app; import json; spec = app.openapi(); print(f'Successfully generated OpenAPI spec with {len(spec[\"paths\"])} routes.')"

## Optional external tool (NOT required for API build/CI):
# npx @stoplight/spectral-cli lint rapidapi/rapidapi-openapi.json
```

---

### 5. Container Portability & Persistence Validation (CIAPI-L002)

Automated script:
```bash
./scripts/validate_container.sh
```

This automated test suite verifies:
1. **Docker Image Build & Structure:**
   - Image builds cleanly using Python 3.11-slim base.
   - Mutable SQLite database (`/app/cancerinfo.db`) is **not** baked into the image.
   - Development test files (`/app/tests`) are **not** packaged into the release image.
   - Durable data mount point `/app/data` is created within the image.
   - Python 3.11 runtime and OpenAPI spec generation succeed inside the built image.
2. **Dynamic Runtime Port:**
   - Container honors runtime `PORT` variable via `exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-3000}`.
   - Default port (`3000`) boots and responds to all endpoints.
   - Non-default port (`PORT=8081`) boots and responds to `/v1/health` and `/v1/cancers`; the full endpoint smoke checks run on port 3000.
   - The script verifies Uvicorn runs as PID 1 after replacing the shell with `exec`. It does not assert graceful-shutdown timing or in-flight request completion.
3. **Core Endpoints Contract:**
   - `/v1/health`: Returns HTTP 200. The script does not assert the JSON database-status field.
   - `/v1/cancers`: Returns HTTP 200 with a `canonical_name` marker in the response. This is a smoke check, not full JSON/schema validation.
   - `/`: Returns HTTP 200 HTML portal or JSON metadata depending on `Accept` header.
   - `/docs`: Returns HTTP 200 Swagger UI.
   - `/redoc`: Returns HTTP 200 ReDoc UI.
   - `/openapi.json`: Returns HTTP 200 with an `openapi` marker. Container import also generates a non-empty paths map; the script does not validate the complete OpenAPI contract.
4. **Data Durability Across Container Lifecycle:**
   - Container A starts with a uniquely named disposable `ciapi_vol_persist_*` test volume mounted at `/app/data` with `DATABASE_URL=sqlite:////app/data/cancerinfo.db`.
   - A probe record is written to the database in Container A.
   - Container A is stopped and removed (testing replacement, not abrupt crash recovery).
   - Fresh Container B starts attached to the same volume.
   - The probe record is verified to persist via both HTTP endpoint and direct database session.
5. **Production Database Contract:**
   - Production deployment requires external PostgreSQL via:
     ```bash
     ENVIRONMENT=production
     DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:<port>/<dbname>
     ```
   - No persistent container volume is needed when external PostgreSQL is used. Container-local SQLite is strictly for local development and validation. Production credentials must never be committed to Git.

---

### 6. Migrations, Controlled Initialization & Legacy Preservation (CIAPI-L003)

For detailed deployment runbooks, Render configuration, and Neon operator workflows, see [MIGRATIONS_AND_INITIALIZATION.md](MIGRATIONS_AND_INITIALIZATION.md).

#### 1. Alembic Versioned Migrations
```bash
# Verify current migration status
alembic current

# Run migrations to head
alembic upgrade head
```
- Migrates all 11 current-model tables without altering or dropping legacy tables.
- Legacy table `cancer_content` (5,628 rows, 22 columns) is strictly preserved and excluded from Alembic autogenerate schema changes via `include_object` filters.

#### 2. Controlled CLI Bootstrap
```bash
# Dry run inspection (non-mutating report of schema and row counts)
python scripts/bootstrap.py --validate-only

# Execute baseline seeding (single-transaction, safe rollback on failure)
python scripts/bootstrap.py
```
- The bootstrap script validates that the database is at Alembic head revision.
- Refuses to run against populated current-model databases to prevent data corruption or duplicate rows.
- Runs entirely within a single atomic database transaction. If any error occurs, the entire operation is rolled back with zero leftover rows.
- Seeds all 191 baseline records across sources, cancers, aliases, source documents, content records, citations, and consensus facts with full provenance.

#### 3. Production Startup Safety
- Startup `lifespan` in `app/main.py` is strictly non-mutating: it never calls `Base.metadata.create_all` and never calls `seed_database`.
- When `ENVIRONMENT=production` or `CHECK_MIGRATIONS_ON_STARTUP=true`, the API validates that the connected database schema is at Alembic head revision before serving traffic. If unmigrated or unreachable, startup fails with a clean, actionable error.
- Production environment requires PostgreSQL (`postgresql+psycopg2://`); SQLite and missing connection URLs are rejected at configuration load time.
- In-flight admin seed endpoint `POST /v1/admin/seed` returns HTTP 403 Forbidden in production, directing operators to use the controlled CLI bootstrap script.
