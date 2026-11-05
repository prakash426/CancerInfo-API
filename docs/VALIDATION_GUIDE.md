# Testing and Validation Guide

How to verify CancerInfo API locally, in a container and in CI.

## Automated test suite

The suite runs against an isolated database. PostgreSQL-specific tests are skipped unless `POSTGRES_TEST_URL` points at a disposable PostgreSQL database.

```bash
python -m pip install --no-cache-dir --require-hashes -r requirements.txt
python -m pip check
DATABASE_URL=sqlite:////tmp/cancerinfo-tests.db python -m pytest tests/ -v -ra -W default
```

Covered areas include cancer and category resolution, search ranking and pagination, the public response and error envelopes, fact-level provenance, document-level publication gates, WHO noncommercial gating, Alembic migrations and drift, controlled bootstrap, shared rate limiting, CORS and readiness behavior. A regression test also checks that `rapidapi/rapidapi-openapi.json` matches the runtime contract (15 public paths, no admin routes).

## Continuous integration

`.github/workflows/ci.yml` runs on every pull request to `main`. It rejects tracked local data and credentials, installs the hash-locked dependencies, runs the full suite on SQLite, re-runs the database-sensitive tests against PostgreSQL 15, applies migrations with an `alembic check` drift test, exercises the bootstrap CLI (including repeat refusal) and validates the Docker image.

## HTTP smoke test

Start a local server against a development database (see the README quickstart), then:

```bash
BASE=http://localhost:3000
curl -i "$BASE/v1/health"
curl -i "$BASE/v1/ready"
curl -i "$BASE/v1/cancers/breast-cancer/symptoms?country=US"
curl -i "$BASE/v1/search?q=CRC"
curl -i "$BASE/v1/cancers?page=0"   # expect 422 VALIDATION_ERROR
curl -i "$BASE/openapi.json"
```

Set `BASE=https://cancerinfo-api.onrender.com` to run the same checks against the hosted service. A HEAD response does not prove the GET contract.

To lint the public specification with an external tool (optional, not part of CI):

```bash
npx @stoplight/spectral-cli lint rapidapi/rapidapi-openapi.json
```

---

## Container portability and persistence

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

## Migrations, controlled initialization and legacy preservation

For detailed deployment runbooks, Render configuration, and Neon operator workflows, see [MIGRATIONS_AND_INITIALIZATION.md](MIGRATIONS_AND_INITIALIZATION.md).

### Alembic versioned migrations
```bash
# Verify current migration status
alembic current

# Run migrations to head
alembic upgrade head
```
- Migrates all 11 current-model tables without altering or dropping legacy tables.
- Legacy table `cancer_content` (5,628 rows, 22 columns) is strictly preserved and excluded from Alembic autogenerate schema changes via `include_object` filters.

### Controlled CLI bootstrap
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

### Production startup safety
- Startup `lifespan` in `app/main.py` is strictly non-mutating: it never calls `Base.metadata.create_all` and never calls `seed_database`.
- When `ENVIRONMENT=production` or `CHECK_MIGRATIONS_ON_STARTUP=true`, the API validates that the connected database schema is at Alembic head revision before serving traffic. If unmigrated or unreachable, startup fails with a clean, actionable error.
- Production environment requires PostgreSQL (`postgresql+psycopg2://`); SQLite and missing connection URLs are rejected at configuration load time.
- In-flight admin seed endpoint `POST /v1/admin/seed` returns HTTP 403 Forbidden in production, directing operators to use the controlled CLI bootstrap script.
