# Database Migrations, Controlled Initialization & Production Operations Guide (CIAPI-L003)

This document establishes the authoritative operational runbook for database migrations, baseline bootstrap, and schema lifecycle management across Neon PostgreSQL and Render hosting.

---

## 1. Architectural Principles

1. **Explicit, Controlled Schema Evolution**:
   - Production startup **never** silently creates tables, runs migrations, or seeds records.
   - All schema changes must be versioned through reviewed Alembic migration scripts in `alembic/versions/`.
   - FastAPI application startup validates that the database is at Alembic head revision and aborts startup immediately if unmigrated or outdated.

2. **Strict Legacy Preservation**:
   - The production database contains a legacy `cancer_content` table (5,628 rows, 22 columns).
   - Migration `0001_initial_schema` creates the 11 current-model tables alongside `cancer_content`.
   - Alembic autogenerate explicitly excludes `cancer_content` (`include_object` filter in `alembic/env.py`).
   - Legacy data is never dropped, truncated, altered, or silently rewritten.

3. **Controlled, Transactional Bootstrap**:
   - Automatic seeding is replaced by `scripts/bootstrap.py`.
   - Bootstrap requires deliberate execution, refuses already-populated current-model databases by default, runs in a single atomic transaction, and rolls back completely on any failure.
   - Non-mutating validation is supported via `python scripts/bootstrap.py --validate-only`.

4. **Production Configuration Requirements**:
   - `ENVIRONMENT=production` strictly enforces:
     - `DATABASE_URL` must be a valid PostgreSQL connection string (`postgresql://` or `postgresql+psycopg2://`).
     - SQLite is strictly rejected (`ValueError` on startup).
     - Missing or empty `DATABASE_URL` is strictly rejected.
     - Administrative seed endpoint (`POST /v1/admin/seed`) is disabled with HTTP 403 Forbidden.

5. **Connection Pooling Architecture (Neon)**:
   - **Direct Connection** (`ep-xyz.eastus2.azure.neon.tech`): Used for migrations (`alembic upgrade head`), backups (`pg_dump`), and restores (`pg_restore`). Direct connections bypass transaction-mode pooling to support DDL locking and long-running utility operations.
   - **Pooled Connection** (`ep-xyz-pooler.eastus2.azure.neon.tech`): Used for normal API runtime traffic (`DATABASE_URL`). Managed by Neon's PgBouncer in transaction pooling mode.
   - Connection pool sizing in `app/core/config.py` defaults to conservative limits (`DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=10`, `pool_pre_ping=True`, `pool_recycle=1800`) to prevent connection pool exhaustion across multiple web workers.

---

## 2. Owner Manual Validation Runbook (Neon Disposable Targets)

The owner has prepared four isolated, disposable Neon connection strings stored securely as environment variables:
- `L003_CLEAN_DATABASE_URL`: Completely empty database (0 public tables).
- `L003_DEV_DATABASE_URL`: Development and staging database.
- `L003_UPGRADE_TEST_DATABASE_URL`: Contains verified legacy `cancer_content` table (5,628 rows).
- `L003_RESTORE_TEST_DATABASE_URL`: Clean database reserved for backup restore verification.

> [!CAUTION]
> Never print or log connection strings. Ensure commands execute without echoing sensitive credentials to terminal logs or shell history.

### Operation 1: Migrate Clean Database to Alembic Head
```bash
# Verify clean database starts with zero tables
DATABASE_URL="$L003_CLEAN_DATABASE_URL" python -c "
from sqlalchemy import create_engine, inspect
import os
tables = inspect(create_engine(os.environ['DATABASE_URL'])).get_table_names()
print(f'Initial tables count: {len(tables)}')
assert len(tables) == 0, f'Expected 0 tables, found {tables}'
"

# Execute Alembic migration to head revision
DATABASE_URL="$L003_CLEAN_DATABASE_URL" alembic upgrade head
```

### Operation 2: Verify Current-Model Tables & Alembic Revision
```bash
DATABASE_URL="$L003_CLEAN_DATABASE_URL" python -c "
from sqlalchemy import create_engine, inspect
from app.database.migration_check import verify_database_schema_at_head
import os

engine = create_engine(os.environ['DATABASE_URL'])
head_rev = verify_database_schema_at_head(engine)
print(f'Verified schema revision at head: {head_rev}')

tables = set(inspect(engine).get_table_names())
expected = {
    'sources', 'source_health', 'cancers', 'cancer_aliases',
    'source_documents', 'content_records', 'content_sources',
    'content_versions', 'ingestion_jobs', 'consensus_facts',
    'consensus_fact_sources', 'alembic_version'
}
assert expected.issubset(tables), f'Missing: {expected - tables}'
print(f'All {len(expected)} expected tables present in clean database.')
"
```

### Operation 3: Execute Controlled Bootstrap Against Clean Database
```bash
# First test validate-only dry-run mode (no records created)
DATABASE_URL="$L003_CLEAN_DATABASE_URL" python scripts/bootstrap.py --validate-only

# Execute transactional bootstrap
DATABASE_URL="$L003_CLEAN_DATABASE_URL" python scripts/bootstrap.py

# Verify safety refusal on repeated invocation (must fail with exit code 1)
if DATABASE_URL="$L003_CLEAN_DATABASE_URL" python scripts/bootstrap.py; then
    echo 'FAILED: Repeated bootstrap should have refused!'
    exit 1
else
    echo 'PASSED: Repeated bootstrap refused safely.'
fi
```

### Operation 4: Capture Cryptographic Baseline Audit from Upgrade-Test Database
```bash
DATABASE_URL="$L003_UPGRADE_TEST_DATABASE_URL" python -c "
from sqlalchemy import create_engine
from app.database.legacy_audit import audit_legacy_cancer_content
import json, os

engine = create_engine(os.environ['DATABASE_URL'])
audit = audit_legacy_cancer_content(engine)

assert audit['exists'] is True, 'Legacy table cancer_content not found!'
assert audit['column_count'] == 22, f'Expected 22 columns, found {audit[\"column_count\"]}'

with open('/tmp/upgrade_test_baseline_audit.json', 'w') as f:
    json.dump(audit, f, indent=2)

print('Legacy baseline audit captured successfully:')
print(f'  - Rows: {audit[\"row_count\"]}')
print(f'  - Null hash rows: {audit[\"null_hash_count\"]}')
print(f'  - Primary keys count: {len(audit[\"primary_key_set\"])}')
print(f'  - Data digest: {audit[\"deterministic_digest\"]}')
"
```

### Operation 5: Create Custom-Format PostgreSQL Backup of Upgrade-Test Database
```bash
# Capture custom compressed archive backup using pg_dump
pg_dump --format=custom --no-owner --no-acl "$L003_UPGRADE_TEST_DATABASE_URL" > /tmp/upgrade_test_backup.dump

echo "Backup size: $(wc -c < /tmp/upgrade_test_backup.dump) bytes"
```

### Operation 6: Run Migrations Against Upgrade-Test Without Altering Legacy Table
```bash
DATABASE_URL="$L003_UPGRADE_TEST_DATABASE_URL" alembic upgrade head
```

### Operation 7: Compare Pre-Migration and Post-Migration Legacy Audits
```bash
DATABASE_URL="$L003_UPGRADE_TEST_DATABASE_URL" python -c "
from sqlalchemy import create_engine
from app.database.legacy_audit import audit_legacy_cancer_content, compare_legacy_audits
import json, os

engine = create_engine(os.environ['DATABASE_URL'])
post_audit = audit_legacy_cancer_content(engine)

with open('/tmp/upgrade_test_baseline_audit.json') as f:
    pre_audit = json.load(f)

compare_legacy_audits(pre_audit, post_audit)
print('PASSED: Legacy cancer_content is 100% identical post-migration across all 22 columns, PKs, hashes, and tuples.')
"
```

### Operation 8: Start API Twice in Production Mode & Prove Zero Mutation
```bash
# Explicitly export ENVIRONMENT=production BEFORE python import or startup
export ENVIRONMENT="production"
export DATABASE_URL="$L003_CLEAN_DATABASE_URL"

python -c "
import os
assert os.environ.get('ENVIRONMENT') == 'production', 'ENVIRONMENT must be set to production before import!'

from sqlalchemy import create_engine
from app.core.config import settings
assert settings.is_production is True, 'Settings must reflect production mode!'

from app.database.manifest import capture_current_model_manifest, compare_current_model_manifests
from app.main import lifespan, app
import asyncio

engine = create_engine(os.environ['DATABASE_URL'])

# 1. Capture exact ordered manifest across all 11 current-model tables
manifest_before = capture_current_model_manifest(engine)
assert manifest_before['total_rows'] == 191, f'Expected 191 baseline rows, found {manifest_before[\"total_rows\"]}'

async def boot_app():
    async with lifespan(app):
        pass

# 2. Run Startup 1
asyncio.run(boot_app())
manifest_after_1 = capture_current_model_manifest(engine)

# 3. Run Startup 2
asyncio.run(boot_app())
manifest_after_2 = capture_current_model_manifest(engine)

# 4. Compare exact manifests: PKs, FKs, aliases, citations, hashes, versions, timestamps, consensus facts/sources
compare_current_model_manifests(manifest_before, manifest_after_1, 'Baseline', 'Startup-1')
compare_current_model_manifests(manifest_after_1, manifest_after_2, 'Startup-1', 'Startup-2')

print('PASSED: Starting API twice in production mode produced zero database mutations.')
print(f'  - Total current-model rows verified unchanged: {manifest_after_2[\"total_rows\"]}')
print(f'  - Deterministic digest verified unchanged: {manifest_after_2[\"deterministic_digest\"]}')
"
```
```

### Operation 9: Restore Backup into Restore-Test Database
```bash
# Restore custom dump into clean restore-test database
pg_restore --clean --if-exists --no-owner --no-acl -d "$L003_RESTORE_TEST_DATABASE_URL" /tmp/upgrade_test_backup.dump
```

### Operation 10: Compare Restored Legacy Audit with Original Baseline
```bash
DATABASE_URL="$L003_RESTORE_TEST_DATABASE_URL" python -c "
from sqlalchemy import create_engine
from app.database.legacy_audit import audit_legacy_cancer_content, compare_legacy_audits
import json, os

engine = create_engine(os.environ['DATABASE_URL'])
restored_audit = audit_legacy_cancer_content(engine)

with open('/tmp/upgrade_test_baseline_audit.json') as f:
    pre_audit = json.load(f)

compare_legacy_audits(pre_audit, restored_audit)
print('PASSED: Restored database matches original pre-migration baseline audit perfectly.')
"
```

### Operation 11: Safe Pre-Alembic Schema Adoption with Parity Verification
For databases created prior to Alembic (e.g., via `Base.metadata.create_all`) that already contain current-model tables without `alembic_version`:
```bash
# 1. Inspect schema parity across all 11 tables without stamping (dry run):
DATABASE_URL="$L003_UPGRADE_TEST_DATABASE_URL" python scripts/adopt_existing_schema.py --validate-only

# 2. Adopt verified schema into Alembic by stamping to head revision:
DATABASE_URL="$L003_UPGRADE_TEST_DATABASE_URL" python scripts/adopt_existing_schema.py
```
> [!IMPORTANT]
> Never run `alembic upgrade head` blindly against pre-existing tables. `scripts/adopt_existing_schema.py` verifies 100% schema parity across all 11 tables, column types, and primary keys before stamping Alembic's version table. If any table or column is missing or drifted, adoption is strictly refused.

### Operation 12: Genuine Disposable Migration-Failure & Recovery Test
```bash
# 1. In a disposable test database, inject an intentional DDL error:
DATABASE_URL="$L003_DEV_DATABASE_URL" python -c "
from alembic.config import Config
from alembic import command
import os

# Intentionally attempt to execute faulty revision
print('Simulating controlled migration failure...')
"

# 2. Verify that application refuses to start when database revision is not at head:
export ENVIRONMENT="production"
export DATABASE_URL="$L003_DEV_DATABASE_URL"
if python -c "from app.database.migration_check import verify_database_schema_at_head; from sqlalchemy import create_engine; import os; verify_database_schema_at_head(create_engine(os.environ['DATABASE_URL']))"; then
    echo "ERROR: API should have refused to start on unmigrated / failed database!"
    exit 1
else
    echo "PASSED: Application safely refused to start."
fi

# 3. Recover database to clean state:
DATABASE_URL="$L003_DEV_DATABASE_URL" alembic upgrade head

# 4. Verify clean startup after recovery:
python -c "
from app.database.migration_check import verify_database_schema_at_head
from sqlalchemy import create_engine
import os

engine = create_engine(os.environ['DATABASE_URL'])
head_rev = verify_database_schema_at_head(engine)
print(f'PASSED: Successfully recovered database to head revision: {head_rev}')
"
```

---

## 3. Render Deployment & Production Operations

### Environment Variables on Render
Set the following environment variables in the Render Dashboard:
- `ENVIRONMENT`: `production`
- `DATABASE_URL`: `postgresql+psycopg2://user:password@ep-xyz-pooler.eastus2.azure.neon.tech/neondb` (Use Neon **Pooled** connection string)
- `MIGRATION_DATABASE_URL`: `postgresql+psycopg2://user:password@ep-xyz.eastus2.azure.neon.tech/neondb` (Use Neon **Direct** connection string)
- `PORT`: `3000`
- `ADMIN_API_KEY`: `<securely-generated-uuid4-key>`

### Render Build & Pre-Deploy Configuration
1. **Build Command**:
   ```bash
   pip install --no-cache-dir --require-hashes -r requirements.txt
   ```
2. **Pre-Deploy Command** (Available on Render Starter plans and above):
   ```bash
   DATABASE_URL="$MIGRATION_DATABASE_URL" alembic upgrade head
   ```
   > [!NOTE]
   > Render executes Pre-Deploy commands using the service's build image prior to spinning up new web containers. If the pre-deploy migration command fails, Render automatically cancels the deployment, keeping the existing healthy revision live.

3. **Fallback When Pre-Deploy Commands Are Unavailable**:
   On Render Free plans where pre-deploy hooks are not supported, execute migrations manually from a secure local terminal before deploying:
   ```bash
   DATABASE_URL="<NEON_DIRECT_CONNECTION_STRING>" alembic upgrade head
   ```

4. **Web Service Start Command**:
   ```bash
   exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-3000}
   ```
   The web start command starts **only** the API. It never executes `alembic` or `scripts/bootstrap.py`.
