# Access, rate-limit and readiness validation

Candidate targets `launch_blockers` from `codex/access-rate-readiness`. This change is proposed only; production has not been migrated, merged or deployed.

## Local verification, November 2, 2026

- Full suite against SQLite and disposable PostgreSQL 18: 389 passed, one existing Starlette/httpx deprecation warning; no skipped tests in the PostgreSQL-enabled full run.
- Focused access/readiness suite: 44 passed, including production-mode HTTP behavior, WHO exclusion, worker restart continuity and refusal to start with a damaged schema.
- Shared PostgreSQL concurrency: three limiter instances and 35 concurrent checks permit exactly seven requests under a seven-request window. A new instance inherits the exhausted allowance. Independent addresses retain independent allowances.
- Expiry, bounded cleanup, one-second lock timeout, forged/duplicate/malformed proxy chains, default-secret refusal, administrator denial and consistent success/error headers passed. Allowed browser origins can read 429, 503 and 500 responses with the configured CORS headers.
- Database connection, registry, schema and revision failures return sanitized 503 readiness results; static liveness stays available. A managed table dropped after startup is detected.
- The existing container validation suite passed image packaging, Python 3.11, OpenAPI generation, default/custom ports, migrations, bootstrap and repeat refusal, endpoint probes and data persistence across container destruction/recreation. The production OpenAPI container receives an explicit disposable test admin key.
- Dependency consistency, tracked-private-artifact guard and whitespace checks passed.

## Data preservation

An isolated restore of the retained pre-publication production backup was upgraded to revision 0005, then tested through 0006 upgrade, downgrade and reupgrade. Every corpus value and every legacy row stayed unchanged: 347 original records, their 347 citations and 347 versions, 60 WHO provenance rows and 5,628 legacy rows. Alembic drift and physical schema parity checks passed. The new request-accounting table was empty after migration.

All 82 local database/research file fingerprints matched before and after validation. The ten earlier release fingerprints also matched. No production connection or data transition was used during this fix. The new production-mode regression confirms WHO search remains empty, and no publication policy or approval plan changes are included.

## Review and future rollout

CI runs SQLite, PostgreSQL 15, drift/bootstrap and built-image checks on the PR candidate. GitHub's check result is the authoritative final remote result; local passing tests do not substitute for it.

Migration 0006 adds only operational rate accounting. Corpus manifests explicitly exclude that changing accounting state while schema and integrity inventories retain the table. A future release requires a strong deployment admin secret, verified proxy peer configuration, the reviewed additive migration and an explicit deployment decision. External alerts and full staging load/capacity acceptance remain separate launch work. See [operational instructions](ACCESS_RATE_READINESS.md).
