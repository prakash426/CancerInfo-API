# CIAPI-L003 Candidate Report: Versioned PostgreSQL Migrations & Controlled Initialization

> Working-tree candidate report updated after local and owner-approved disposable Neon validation.
> See `docs/L003_LOCAL_VALIDATION.md` for the detailed chronological evidence record.
> Historical restore snippets and destructive restore instructions are superseded and are not approved runbooks.

- **Repository:** `Prakash-Merepala/CancerInfo-API`
- **Review Branch:** `CIAPI-L003-postgresql-migrations-controlled-initialization`
- **Historical Base Commit:** `7ae049310198b62d0b1812cad453471d403c65d3`
- **Historical Implementation Commit:** `d5ed5caedeeeef76af28c8de1eb6c2c4d03b84f4`
- **Current Correction Base Checkout:** `7f9f23b3e8af8351d2ef3b1cd05da68ab0571f0c`
- **Current Candidate Commit:** Pending owner-authorized commit
- **Status:** **Working-tree validation complete; commit-specific GitHub CI pending**

---

## 1. Executive Summary & Objective Realization

CIAPI-L003 implements versioned database migrations (Alembic) and strict, controlled baseline initialization for the CancerInfo API. The service guarantees that production startup **never** silently creates tables, migrates schemas, seeds content, overwrites data, or falls back to SQLite.

### Key Governance Guarantees
1. **Zero Production Startup Mutation:** In `ENVIRONMENT=production`, FastAPI lifespan verifies that the database schema is at migration head (`0001_initial_schema`) without executing DDL, DML, or seeding. If unmigrated or unreachable, it fails fast.
2. **Deterministic Manifest Validation:** A two-start validation protocol inspects all 11 current-model tables (PKs, FKs, aliases, citations, content hashes, version numbers, created/updated timestamps, consensus facts, and consensus source relationships) and computes a deterministic SHA-256 digest. Across consecutive production startups, this digest is bit-for-bit identical.
3. **Foreign-Key Integrity Verification:** `verify_foreign_key_integrity` explicitly verifies that 0 orphaned foreign-key records exist across all relationships in the current model.
4. **Legacy Preservation (`cancer_content`):** The 5,628-row legacy table is explicitly excluded from Alembic schema management (`alembic/env.py:include_object`) and protected against mutations. Cryptographic legacy audit verifies 22 column specs, index definitions, and a deterministic content digest across all 22 columns of all 5,628 rows. Executable CLI `scripts/audit_legacy_table.py` enables automated verification and comparison.
5. **Pre-Alembic Fail-Closed Schema Adoption:** For existing unversioned PostgreSQL environments containing all 11 tables without an `alembic_version` tracker, `scripts/adopt_existing_schema.py` and `app/database/adoption.py` validate 100% schema parity (types, bidirectional nullability, extra/missing columns, PKs, ordered FK mappings, unique constraints, and index uniqueness) against SQLAlchemy `Base.metadata` and stamp the pinned `0001_initial_schema` baseline without destructive DDL. Databases with any drift or already-managed versions fail closed.
6. **Safe Credential & URL Handling:** Alembic configuration safely handles percent-encoded credentials (`set_alembic_url_safe` escaping `%` as `%%`) preventing ConfigParser interpolation syntax errors, while unmasked credentials are used internally without logging secrets.
7. **Single-Transaction Controlled Bootstrap:** Seeding occurs solely via explicit CLI invocation (`python scripts/bootstrap.py`). The `--force` flag has been removed; bootstrap safely refuses to run on any populated database.

---

## 2. Review Corrections Implemented

| # | Review Requirement | Implementation & Verification Status |
|---|---|---|
| **1** | Complete fail-closed schema adoption with comprehensive parity check | **Fixed**: `verify_schema_parity` checks all 11 tables across column presence, unexpected extra columns, type affinity, bidirectional nullability (NOT NULL vs NULLABLE), primary keys, exact ordered foreign-key mappings, unique constraints, and index uniqueness. Refuses and does not stamp if drift is detected or if `alembic_version` already exists. Added `test_adoption_negative_drift_cases` covering missing table, extra column, missing column, type mismatch, and nullability mismatch. |
| **2** | Safe URL handling for percent-encoded credentials | **Fixed**: Added `set_alembic_url_safe` in `app/database/migration_check.py` and applied across `alembic/env.py` and `app/database/adoption.py` to escape `%` as `%%`, eliminating ConfigParser `InterpolationSyntaxError`. Added regression test `test_percent_encoded_credentials_url_handling` validating passwords containing `@`, `%`, `#`. |
| **3** | Populated baseline, failing CLI result, transactional rollback & true backup recovery | **Fixed**: `test_migration_failure_and_recovery` upgraded to populate 191 baseline rows, capture baseline manifest, create pre-migration backup, execute upgrade via CLI subprocess with isolated faulty revision to prove nonzero exit code, prove transactional rollback to `0001_initial_schema`, restore pre-migration backup, and prove bit-for-bit manifest match with zero data loss. |
| **4** | 22-column legacy table cryptographic audit & dedicated audit CLI | **Fixed**: `audit_legacy_cancer_content` computes a deterministic SHA-256 digest across all 22 columns of all 5,628 rows. Created `scripts/audit_legacy_table.py` CLI supporting audit extraction and bit-for-bit baseline comparison. Clarified earlier 4-field Neon audit as historical context. |
| **5** | Isolate PostgreSQL test fixtures from bootstrap CLI smoke DB | **Fixed**: In `.github/workflows/ci.yml`, created a dedicated `cancerinfo_pytest` database for pytest execution, leaving `cancerinfo_test` pristine for the bootstrap CLI smoke tests. Added `assert_safe_test_database` safeguards blocking destructive resets on remote/cloud hosts. |
| **6** | Precise classification of verified vs. pending acceptance checks | **Fixed**: Evidence is now separated into local working-tree validation, owner-approved disposable Neon validation, container validation, and the still-pending commit-specific GitHub CI gate. Historical destructive restore snippets are explicitly superseded. |

---

## 3. Current Validation Summary

### A. Local SQLite / Default Suite

- **Environment:** local Python 3.11 virtual environment.
- **Result:** `74 passed, 1 warning in 3.21s`.
- **Status:** PASSED on the current uncommitted working tree.
- The remaining warning is the existing Starlette/httpx test-client deprecation warning.

The current default suite covers application behavior, migration guards,
controlled initialization, schema-adoption protections and the additional
offline Neon target-guard tests.

### B. Local PostgreSQL 15.19 Gate

The dedicated L003 PostgreSQL validation runner was executed against the
owner-controlled local PostgreSQL 15.19 instance.

- PostgreSQL server: `15.19`
- PostgreSQL client tools used for the local backup/restore tests: `15.19`
- Runner: `scripts/validate_local_postgres.py`
- Result: `104 passed, 1 warning in 10.79s`
- Final runner status:

`L003 LOCAL VALIDATION PASSED. Neon, CI and deployment are separate gates.`

The passing PostgreSQL gate includes:

- migration upgrade/downgrade behavior
- model/migration drift detection
- controlled bootstrap behavior and rollback
- pre-Alembic schema-adoption validation
- failure/recovery testing
- custom-format PostgreSQL backup and restore
- schema/data manifest comparison
- legacy-data preservation
- foreign-key verification
- fixture ingestion against PostgreSQL
- serving the ingested fixture from the same database
- repeated application lifespan/startup manifest preservation

PostgreSQL 18.6 client tools were intentionally used only for the Neon
PostgreSQL 17.11 backup/restore validation. PostgreSQL 15.19 client tools are
used for the local PostgreSQL 15 test gate.

### C. Container Validation

The complete L003 Docker/container validation suite passed locally using
Docker Desktop 4.92.0 / Docker Engine 29.8.0 on arm64.

Final result:

`ALL CIAPI-L003 CONTAINER & MIGRATION VALIDATIONS PASSED`

Verified container behaviors include:

- dynamic `PORT` handling
- absence of a baked SQLite database
- absence of unit tests from the production image
- packaging of Alembic migrations
- packaging of controlled bootstrap and schema-adoption CLIs
- Python 3.11 runtime
- OpenAPI generation
- default port 3000 startup
- custom port 8081 startup
- `/v1/health`
- `/v1/cancers`
- `/`
- `/docs`
- `/redoc`
- `/openapi.json`
- uvicorn runtime/PID behavior
- explicit migration execution
- controlled bootstrap
- repeated-bootstrap refusal
- SQLite durability across complete container destruction and recreation

Two validation-harness defects were discovered and corrected during this gate:

1. `.dockerignore` excluded all of `scripts/` even though the Dockerfile
   requires `scripts/bootstrap.py` and `scripts/adopt_existing_schema.py`.
   Only those required production CLIs are now included from `scripts/`.

2. The OpenAPI smoke check imported the application in production mode without
   supplying a PostgreSQL-shaped `DATABASE_URL`. L003 correctly failed closed
   because production SQLite fallback is forbidden. The smoke test now uses a
   non-secret placeholder PostgreSQL URL solely for OpenAPI generation and does
   not connect to a database.

### D. Owner-Approved Disposable Neon Validation

Neon validation was executed only against owner-approved disposable targets.
No production database was modified.

#### Clean migration/bootstrap target

The clean Neon validation used PostgreSQL 17.11 and demonstrated:

- migrations created all eleven current-model tables
- Alembic revision reached `0001_initial_schema`
- `alembic check` showed no model/migration drift
- controlled bootstrap created 191 baseline rows
- repeated bootstrap safely refused without mutation
- foreign-key integrity checks passed
- two production-configured application starts succeeded without mutation

Recorded clean-model digest:

`61b2bf194eaa8a67d24f7c2b47eae307577e1f2ce5ac707fe0c85ae2f944ce7c`

Clean baseline current-model counts:

- sources: 5
- source_health: 5
- cancers: 7
- cancer_aliases: 22
- source_documents: 20
- content_records: 21
- content_sources: 21
- content_versions: 21
- ingestion_jobs: 0
- consensus_facts: 21
- consensus_fact_sources: 48

#### Upgrade / backup / isolated restore target

The existing restore-test `neondb` was explicitly treated as nonempty.

Pre-restore inventory established:

- legacy `public.cancer_content`: 5,628 rows
- no `alembic_version` table

A safety backup was created before restore work.

SHA-256 backup evidence:

- upgraded-source dump:
  `7513731fe0baec2211c60c35348e9ef771eeaa2b097b3465cb37a7fb0f2d67c5`
- original restore-test baseline dump:
  `8821ddb431278639b87f6b5f25a4bed17957954823757b0ce3e7534cde39f568`

The upgraded source backup was restored into the separately created database:

`ciapi_l003_restore_sandbox`

The original restore-test `neondb` was not used as the restore destination.

Source-versus-restored comparison result:

`OVERALL: MATCH`

The comparison covered:

- public table set
- exact row counts
- deterministic table-data digests
- column definitions
- constraints
- indexes
- schema digest

The original restore-test `neondb` remained unchanged after the isolated
restore:

- `cancer_content`: 5,628 rows
- `alembic_version`: absent

#### Restored-database Alembic evidence

On `ciapi_l003_restore_sandbox`:

- `alembic current`: `0001_initial_schema (head)`
- `alembic heads`: `0001_initial_schema (head)`
- `alembic check`: `No new upgrade operations detected.`
- repeated `alembic upgrade head`: exit code 0
- before/after legacy row count: 5,628
- before/after revision: `0001_initial_schema`

#### Restored-database production-start evidence

Before two production-configured FastAPI lifespan starts:

`c3789f61b8a111c311663e4ead07d8a6a3b126c98e063a07bc57f4cd3041fca3`

Rows represented by the validation snapshot:

`5820`

Both starts succeeded:

- `PRODUCTION_START_1: OK`
- `PRODUCTION_START_2: OK`

After both starts:

`c3789f61b8a111c311663e4ead07d8a6a3b126c98e063a07bc57f4cd3041fca3`

Rows remained:

`5820`

Final result:

- `STARTUP_MUTATION: NONE`
- `RESULT: PASS`

---

## 4. Remaining Acceptance / Execution Gates

The previously documented clean-Neon and backup/restore owner operations are
no longer pending; they have been executed against disposable owner-approved
targets and are recorded above and in `docs/L003_LOCAL_VALIDATION.md`.

The historical `pg_restore --clean` instructions are superseded and must not
be used as an approved L003 restore procedure.

### Commit-specific GitHub CI

The primary remaining acceptance gate is CI tied to the exact eventual
candidate commit SHA.

The repository CI workflow is designed to exercise:

- Python 3.11 dependency installation
- dependency graph verification
- SQLite/default pytest
- PostgreSQL 15 service lifecycle
- isolated PostgreSQL test database creation
- PostgreSQL migration/bootstrap tests
- migration drift checks
- OpenAPI validation
- controlled bootstrap lifecycle
- Docker/container portability and durability validation

Current local and Neon results are working-tree evidence only until an
owner-authorized candidate commit exists and CI runs against that exact SHA.

### Pre-Alembic schema-adoption live rehearsal

Schema adoption is covered by the local SQLite and PostgreSQL test gates.
A separate live Neon rehearsal of adoption against an intentionally
unversioned eleven-table database has not been recorded in this checkpoint.

Such a rehearsal is not to be performed against production or any valuable
database. If the owner later chooses to run it, it must use a disposable,
explicitly approved unversioned database and the fail-closed
`scripts/adopt_existing_schema.py` workflow.

No production migration, deployment, merge, or task-tracker update is
authorized by this report.

---

## 5. Precise File-Change Summary

| File | Change Description |
|---|---|
| `alembic.ini` | Root Alembic configuration pointing to `alembic/` migration tree. |
| `alembic/README` | Alembic documentation placeholder. |
| `alembic/script.py.mako` | Migration template. |
| `alembic/env.py` | Migration runner; configures online/offline migrations, dialect conversion, safe `%` URL escaping, and excludes `cancer_content` (`include_object`). |
| `alembic/versions/0001_initial_schema.py` | Baseline migration creating all 11 current-model tables with indexes and foreign keys in a single transaction. |
| `app/api/v1/endpoints/admin.py` | Disables `/seed` endpoint in production (HTTP 403). |
| `app/core/config.py` | Normalizes database URLs (`postgresql+psycopg2`), strictly forbids SQLite in production, redacts secrets from exception strings. |
| `app/database/adoption.py` | Pre-Alembic schema adoption engine; pins `0001_initial_schema`, checks types/bidirectional nullability/PKs/ordered FKs/unique constraints/indexes, fails closed on versioned DBs, preserves unmasked credentials internally with safe URL escaping. |
| `app/database/bootstrap.py` | Controlled single-transaction bootstrap; removed `--force`, safely refuses execution if data exists. |
| `app/database/legacy_audit.py` | Legacy `cancer_content` auditor; hashes all 22 columns across all rows, compares column specs and indexes. |
| `app/database/manifest.py` | Current-model manifest engine; captures exact ordered manifests for all 11 tables, computes SHA-256 digest, verifies FK integrity (0 orphans). |
| `app/database/migration_check.py` | Inspects database schema against Alembic head revision without executing mutations; includes `set_alembic_url_safe`. |
| `app/database/session.py` | Preserves `cancerinfo.db` fallback for local dev, respects `DATABASE_URL`. |
| `app/ingestion/seed.py` | Updated `seed_database` to accept `commit=False` for caller transaction control. |
| `app/main.py` | FastAPI lifespan startup check enforcing schema verification at Alembic head in production. |
| `candidate_report_CIAPI-L003.md` | Formal candidate report documenting architecture, working-tree validation, disposable Neon evidence, container validation, and the remaining commit-specific CI gate. |
| `docs/MIGRATIONS_AND_INITIALIZATION.md` | Complete architectural documentation, schema design, and operational procedures. |
| `docs/VALIDATION_GUIDE.md` | Step-by-step runbook for all 11 validation operations. |
| `scripts/adopt_existing_schema.py` | CLI tool for safe pre-Alembic schema adoption (`--validate-only` dry run). |
| `scripts/audit_legacy_table.py` | CLI tool for legacy `cancer_content` cryptographic integrity audit and comparison. |
| `scripts/bootstrap.py` | CLI tool for controlled baseline bootstrap (`--validate-only` dry run). |
| `scripts/validate_container.sh` | Container validation script testing production mode, non-root user, and durability. |
| `tests/test_bootstrap.py` | 9 bootstrap tests; includes safe DB assertions, mid-write rollback test, unmasked credentials in two-start restart, and FK integrity check. |
| `tests/test_migrations.py` | 13 migration tests; includes safe DB assertions, unversioned adoption path with fail-closed check, 5 negative drift cases, URL escaping regression test, and CLI migration failure/backup recovery test. |
| `.github/workflows/ci.yml` | CI matrix with PostgreSQL 15 service; isolates `cancerinfo_pytest` from `cancerinfo_test`, tests migrations, drift, adoption, and test suite. |
| `Dockerfile` | Multi-stage production container configuration. |
| `README.md` | Updated developer quickstart and migration commands. |

---

## 6. GitHub Review & PR Link

- **Review Branch:** [`CIAPI-L003-postgresql-migrations-controlled-initialization`](https://github.com/Prakash-Merepala/CancerInfo-API/tree/CIAPI-L003-postgresql-migrations-controlled-initialization)
- **PR Compare URL:** [Compare `main`...`CIAPI-L003-postgresql-migrations-controlled-initialization`](https://github.com/Prakash-Merepala/CancerInfo-API/compare/main...CIAPI-L003-postgresql-migrations-controlled-initialization?expand=1)
