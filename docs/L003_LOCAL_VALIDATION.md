# L003 local correction checkpoint

Base checkout: `7f9f23b3e8af8351d2ef3b1cd05da68ab0571f0c`.
The corrections in the working tree are not yet an accepted release.

## Implemented

- Adoption uses Alembic dialect-aware type, server-default, nullability,
  constraint and index comparison, plus explicit ordered primary-key checks.
- Adoption refuses versioned databases and refuses use after the baseline head
  changes, until the adoption contract is reviewed.
- PostgreSQL fixtures create unique databases and only delete databases created
  by that fixture. They never reset the supplied control database.
- Eleven schema-drift cases execute on each selected database dialect.
- The faulty-migration subprocess must report the intended SQL error. PostgreSQL
  additionally requires DDL rollback, retained revision, and unchanged manifests.
- PostgreSQL recovery uses custom-format pg_dump and pg_restore to another
  unique database. It checks schema, data in all eleven model tables, legacy
  data, foreign-key integrity, revision, and legacy sequence advancement.
- Ingestion uses a local HTML fixture with external fetching explicitly forbidden.
  The API reads the ingested fixture from the same database and two lifespan
  starts preserve the post-ingestion manifest.
- Missing tables no longer masquerade as empty tables in model manifests.

## Verified at this checkpoint

The SQLite-only suite ran locally: **67 passed**, one existing Starlette test
client deprecation warning. Whitespace validation passed.

Owner-executed PostgreSQL result supplied in chat: **97 passed, 1 warning in
10.89s** using `scripts/validate_local_postgres.py`. The runner confirmed
`ciapi_l003_test` at `127.0.0.1:55432` and printed `L003 LOCAL VALIDATION PASSED`.
This is evidence for the current uncommitted working tree, not a GitHub CI run
or proof of any Neon/production operation.

Owner-executed read-only Neon preflight confirmed database `ciapi_l003_clean`,
role `neondb_owner`, endpoint `ep-winter-heart-anc19kzu.c-6.us-east-1.aws.neon.tech`,
PostgreSQL 17.11, read-only transaction on, and zero user tables. No migration
was performed by that preflight. Use `scripts/validate_neon_clean.py` only after
confirming this remains the selected disposable branch in Neon. It requires a
typed confirmation, refuses any other target and refuses a nonempty database.
The new guard tests are offline tests, not evidence of Neon execution.

Owner subsequently executed `scripts/validate_neon_clean.py` successfully:
11 current-model tables, no model/migration drift, 191 baseline rows, repeat
bootstrap refusal without mutation, and two production-configured in-process
API starts with passing endpoints and unchanged manifests. Foreign-key checks
passed before the runner printed `NEON CLEAN GATE PASSED`.

Reported model digest:
`61b2bf194eaa8a67d24f7c2b47eae307577e1f2ce5ac707fe0c85ae2f944ce7c`.
Counts: sources 5; source_health 5; cancers 7; cancer_aliases 22;
source_documents 20; content_records 21; content_sources 21;
content_versions 21; ingestion_jobs 0; consensus_facts 21;
consensus_fact_sources 48. This is owner-supplied working-tree evidence,
not deployed HTTP verification or a Neon ingestion run.

## Run the PostgreSQL gate

Prerequisites: PostgreSQL 15 server bound to `127.0.0.1:55432`, role
`ciapi_test_admin` with permission to create databases, control database
`ciapi_l003_test`, and PostgreSQL 15 client tools on PATH.

```bash
cd "/Users/prakash/VS Code/CancerInfo-API"
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
.venv/bin/python scripts/validate_local_postgres.py
```

Enter only the local test password at the hidden prompt. Do not enter a Neon
password. The runner does not save the password or place it in command arguments.
Stop on failure. Do not use this test suite against Neon or production.

Expected successful ending: `L003 LOCAL VALIDATION PASSED` followed by a reminder
that Neon, CI and deployment are separate gates. The owner observed this result
as recorded above.

## Still pending

- Safe owner-specific Neon baseline/restore procedure and evidence.
- Complete CI, including PostgreSQL CLI lifecycle and container validation.
- Final candidate evidence tied to the resulting commit.

The older candidate report is historical. Its manual restore snippets are not
approved instructions. No merge, deployment, production mutation, or tracker
update is part of this local checkpoint.

---

## Superseding validation update · September 26, 2026

This section supersedes the earlier pass counts and the earlier statement that
Neon restore evidence was still pending. Earlier sections are retained as
historical checkpoints.

### Working-tree identity

Base Git HEAD remains:

`7f9f23b3e8af8351d2ef3b1cd05da68ab0571f0c`

The validated L003 corrections remain local, uncommitted and unpushed.

Current implementation diff before this documentation update:

- `alembic/env.py`
- `app/database/adoption.py`
- `app/database/manifest.py`
- `candidate_report_CIAPI-L003.md`
- `tests/test_bootstrap.py`
- `tests/test_migrations.py`

No merge, deployment, production mutation, or tracker update is authorized by
this checkpoint.

### Current local regression results

SQLite/default suite:

`74 passed, 1 warning in 3.21s`

Local PostgreSQL 15.19 validation:

`104 passed, 1 warning in 10.79s`

Runner result:

`L003 LOCAL VALIDATION PASSED. Neon, CI and deployment are separate gates.`

The PostgreSQL gate was executed with PostgreSQL 15 client tools placed first
on PATH. PostgreSQL 18.6 client tools remain appropriate for the Neon
PostgreSQL 17.11 backup/restore checks and were not used for the local
PostgreSQL 15 restore test.

The passing PostgreSQL suite includes the L003 migration-failure/recovery path,
schema-drift coverage, controlled bootstrap behavior, PostgreSQL backup/restore,
fixture ingestion, serving from the same database, and restart manifest checks.

### Neon clean-database validation

The previously recorded disposable Neon clean-database validation remains
valid for the current working tree:

- PostgreSQL 17.11
- eleven current-model tables created through migrations
- Alembic revision `0001_initial_schema`
- no migration/model drift
- controlled bootstrap created 191 baseline rows
- repeat bootstrap refused without mutation
- two production-configured application starts succeeded
- foreign-key checks passed
- ingestion job count remained zero for the clean baseline

Recorded clean model digest:

`61b2bf194eaa8a67d24f7c2b47eae307577e1f2ce5ac707fe0c85ae2f944ce7c`

### Neon upgrade and isolated restore validation

Read-only inventory was performed before restore work.

The existing `ciapi-l003-restore-test` database was not assumed empty. Its
baseline `neondb` contained the legacy `public.cancer_content` table with
5,628 rows and no `alembic_version` table.

A safety backup of that original baseline was created before isolated restore
testing.

Backup SHA-256 values:

Upgrade-source backup:

`7513731fe0baec2211c60c35348e9ef771eeaa2b097b3465cb37a7fb0f2d67c5`

Original restore-test baseline backup:

`8821ddb431278639b87f6b5f25a4bed17957954823757b0ce3e7534cde39f568`

The upgraded source backup was restored into the separately created database:

`ciapi_l003_restore_sandbox`

on the disposable `ciapi-l003-restore-test` Neon branch.

The original `neondb` database was not used as the restore destination.

Source-versus-restored validation reported:

`OVERALL: MATCH`

The comparison covered:

- public table set
- table row counts
- deterministic table data digests
- column definitions
- constraints
- indexes
- schema digest

The original restore-test `neondb` remained unchanged after the isolated
restore: the legacy `cancer_content` row count remained 5,628 and
`alembic_version` remained absent.

### Restored-database Alembic proof

On `ciapi_l003_restore_sandbox`:

Alembic current:

`0001_initial_schema (head)`

Alembic heads:

`0001_initial_schema (head)`

Autogenerate drift check:

`No new upgrade operations detected.`

Before `alembic upgrade head`:

- revision: `0001_initial_schema`
- legacy `cancer_content` rows: `5628`

`alembic upgrade head` exited successfully with:

`ALEMBIC_EXIT=0`

After `alembic upgrade head`:

- revision: `0001_initial_schema`
- legacy `cancer_content` rows: `5628`

This demonstrates that the restored database is already at migration head and
that repeating `upgrade head` is a no-op for the validated state.

### Restored-database production startup proof

The complete restored-database manifest was captured before and after two
production-configured FastAPI lifespan starts.

Before:

`c3789f61b8a111c311663e4ead07d8a6a3b126c98e063a07bc57f4cd3041fca3`

Total rows represented by the validation snapshot:

`5820`

Both application starts succeeded:

- `PRODUCTION_START_1: OK`
- `PRODUCTION_START_2: OK`

After:

`c3789f61b8a111c311663e4ead07d8a6a3b126c98e063a07bc57f4cd3041fca3`

Total rows after startup:

`5820`

Result:

- `STARTUP_MUTATION: NONE`
- `RESULT: PASS`

Production-configured application startup therefore verified migration state
without silently creating, seeding, rewriting, or duplicating database data.

### Acceptance evidence status at this checkpoint

Locally and on owner-approved disposable Neon databases, evidence now covers:

- versioned migration of the current eleven-table model
- controlled bootstrap behavior
- clean PostgreSQL migration/bootstrap
- baseline-data upgrade validation
- aliases, citations, history and foreign-key preservation checks
- consensus facts and consensus source-link preservation checks
- local migration-failure/recovery behavior
- PostgreSQL backup/restore behavior
- isolated Neon restore with source/restored schema and data comparison
- production startup without automatic reseeding or mutation
- repeated Alembic upgrade-head idempotence
- serving and fixture ingestion against the same PostgreSQL database in the
  local PostgreSQL validation gate

### Still pending before CIAPI-L003 can be accepted

- Final CI on the eventual candidate commit.
- Any required PostgreSQL service lifecycle checks performed by CI.
- Required production-container validation not already represented by the local
  gate.
- Final evidence tied to the exact candidate commit SHA.
- Review of all working-tree changes before commit.
- Commit/push only after explicit owner authorization.
- Merge only after explicit owner authorization.
- Deployment and production changes remain unauthorized.
- Notion/task status updates remain unauthorized.

The current evidence belongs to the uncommitted working tree based on
`7f9f23b3e8af8351d2ef3b1cd05da68ab0571f0c`; it must not be represented as
commit-specific CI evidence.

### Container validation · September 26, 2026

The full local CIAPI-L003 container validation subsequently passed using
Docker Desktop 4.92.0 / Docker Engine 29.8.0 on arm64.

During validation, two container-packaging/test-harness defects were identified
and corrected in the working tree:

1. `.dockerignore` previously excluded the entire `scripts/` directory even
   though the production Dockerfile explicitly copies the controlled bootstrap
   and schema-adoption CLIs. The Docker context now continues to exclude local
   scripts while explicitly allowing:
   - `scripts/bootstrap.py`
   - `scripts/adopt_existing_schema.py`

2. The container OpenAPI-generation smoke test imported the application in its
   production-default configuration without a PostgreSQL-shaped DATABASE_URL.
   CIAPI-L003 correctly failed closed because production SQLite fallback is
   forbidden. The validation check now supplies a non-secret placeholder
   PostgreSQL URL solely for OpenAPI generation; it does not connect to a
   database or weaken production configuration validation.

The complete container suite then reported:

`ALL CIAPI-L003 CONTAINER & MIGRATION VALIDATIONS PASSED`

Verified container checks:

- dynamic PORT runtime configuration
- no baked SQLite database
- no unit tests packaged in the production image
- Alembic migrations and controlled bootstrap/adoption CLIs packaged
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
- uvicorn process/runtime behavior
- explicit migrations and controlled bootstrap
- repeated bootstrap refusal
- SQLite durability across complete container destruction and recreation

The container suite cleaned up its temporary containers and volumes after
execution.

The previously listed production-container validation item is therefore no
longer pending for this uncommitted working-tree checkpoint.

### Remaining gate

The primary remaining acceptance gate is final CI tied to the exact eventual
candidate commit SHA. Until such a commit is explicitly authorized, current
results remain working-tree evidence only.

No commit, push, merge, deployment, production mutation, or Notion/task update
is authorized by this checkpoint.
