#!/usr/bin/env bash
# ==============================================================================
# scripts/validate_container.sh
# CIAPI-L003: Container Portability, Endpoints, Migrations & Durability Validation
# ==============================================================================
set -euo pipefail

IMAGE_NAME="cancerinfo-api:ciapi-l003-test"
RAND_ID="${RANDOM}_$$"
CONTAINER_DEFAULT="ciapi_cnt_default_${RAND_ID}"
CONTAINER_CUSTOM="ciapi_cnt_custom_${RAND_ID}"
CONTAINER_PERSIST_A="ciapi_cnt_persist_a_${RAND_ID}"
CONTAINER_PERSIST_B="ciapi_cnt_persist_b_${RAND_ID}"
VOLUME_DEFAULT="ciapi_vol_default_${RAND_ID}"
VOLUME_CUSTOM="ciapi_vol_custom_${RAND_ID}"
VOLUME_PERSIST="ciapi_vol_persist_${RAND_ID}"

PORT_DEFAULT=3000
PORT_CUSTOM=8081

cleanup() {
    echo ""
    echo "=== Running Validation Cleanup ==="
    docker rm -f "$CONTAINER_DEFAULT" 2>/dev/null || true
    docker rm -f "$CONTAINER_CUSTOM" 2>/dev/null || true
    docker rm -f "$CONTAINER_PERSIST_A" 2>/dev/null || true
    docker rm -f "$CONTAINER_PERSIST_B" 2>/dev/null || true
    docker volume rm -f "$VOLUME_DEFAULT" 2>/dev/null || true
    docker volume rm -f "$VOLUME_CUSTOM" 2>/dev/null || true
    docker volume rm -f "$VOLUME_PERSIST" 2>/dev/null || true
    echo "=== Cleanup Complete ==="
}
trap cleanup EXIT INT TERM

wait_for_endpoint() {
    local port="$1"
    local endpoint="$2"
    local name="$3"
    local max_attempts=30
    local attempt=1
    echo "Waiting for ${name} at http://127.0.0.1:${port}${endpoint}..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "http://127.0.0.1:${port}${endpoint}" > /dev/null 2>&1; then
            echo "-> ${name} is responding at port ${port} (attempt ${attempt})."
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    echo "ERROR: ${name} failed to respond at http://127.0.0.1:${port}${endpoint} within ${max_attempts}s."
    docker logs "$name" || true
    return 1
}

echo "======================================================================"
echo " Starting CIAPI-L003 Container & Migration Validation Suite"
echo "======================================================================"

# -----------------------------------------------------------------------------
# 1. Build Docker Image
# -----------------------------------------------------------------------------
echo ""
echo "[Step 1/5] Building Docker image: ${IMAGE_NAME}..."
docker build -t "$IMAGE_NAME" .

echo "Verifying image structural requirements:"
# A: Verify cancerinfo.db is NOT baked into the image
echo -n "  - Checking absence of baked SQLite database (/app/cancerinfo.db)... "
if docker run --rm "$IMAGE_NAME" sh -c "test -f /app/cancerinfo.db"; then
    echo "FAILED! /app/cancerinfo.db was found baked into the image."
    exit 1
fi
echo "PASSED (not present in image)."

# B: Verify /app/data directory exists
echo -n "  - Checking /app/data directory exists... "
if ! docker run --rm "$IMAGE_NAME" sh -c "test -d /app/data"; then
    echo "FAILED! /app/data directory does not exist."
    exit 1
fi
echo "PASSED."

# C: Verify tests/ is NOT packaged into image
echo -n "  - Checking absence of unit tests (/app/tests)... "
if docker run --rm "$IMAGE_NAME" sh -c "test -d /app/tests"; then
    echo "FAILED! /app/tests was found in the production image."
    exit 1
fi
echo "PASSED (not present in image)."

# D: Verify Alembic migrations, bootstrap CLI, and schema adoption CLI are packaged into image
echo -n "  - Checking presence of Alembic migrations, bootstrap, and adoption CLI... "
docker run --rm "$IMAGE_NAME" sh -c "test -d /app/alembic && test -f /app/alembic.ini && test -f /app/scripts/bootstrap.py && test -f /app/scripts/adopt_existing_schema.py"
echo "PASSED."

# E: Verify Python 3.11 runtime inside image
echo -n "  - Checking Python runtime inside image... "
PY_VER=$(docker run --rm "$IMAGE_NAME" python -c 'import sys; assert sys.version_info[:2] == (3, 11), sys.version; print(sys.version.split()[0])')
echo "PASSED (${PY_VER})."

# F: Verify OpenAPI generation inside image
echo -n "  - Checking OpenAPI spec generation inside image... "
docker run --rm \
    -e ENVIRONMENT=production \
    -e DATABASE_URL="postgresql+psycopg2://openapi_check:openapi_check@127.0.0.1:5432/openapi_check" \
    "$IMAGE_NAME" \
    python -c "from app.main import app; spec = app.openapi(); assert len(spec['paths']) > 0; print(f'OK ({len(spec[\"paths\"])} paths)')"

# -----------------------------------------------------------------------------
# 2. Test Default Port (3000) Boot, Migrations, Bootstrap & HTTP Endpoints
# -----------------------------------------------------------------------------
echo ""
echo "[Step 2/5] Testing default port (3000) container boot, migrations, and endpoints..."
docker volume create "$VOLUME_DEFAULT" > /dev/null
docker run -d \
    --name "$CONTAINER_DEFAULT" \
    -p "${PORT_DEFAULT}:${PORT_DEFAULT}" \
    -v "${VOLUME_DEFAULT}:/app/data" \
    -e ENVIRONMENT=development \
    -e DATABASE_URL=sqlite:////app/data/cancerinfo.db \
    "$IMAGE_NAME"

echo "Applying migrations and controlled bootstrap in default container..."
docker exec "$CONTAINER_DEFAULT" alembic upgrade head
docker exec "$CONTAINER_DEFAULT" python scripts/bootstrap.py

wait_for_endpoint "$PORT_DEFAULT" "/v1/health" "$CONTAINER_DEFAULT"

echo "Validating core HTTP endpoints on default port (${PORT_DEFAULT}):"

# GET /v1/health
echo -n "  - GET /v1/health (HTTP 200)... "
HEALTH_RESP=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:${PORT_DEFAULT}/v1/health")
STATUS_CODE=$(echo "$HEALTH_RESP" | tail -n1)
BODY=${HEALTH_RESP%$'\n'*}
if [ "$STATUS_CODE" != "200" ]; then
    echo "FAILED! Expected HTTP 200, got ${STATUS_CODE}."
    exit 1
fi
echo "PASSED."

# GET /v1/cancers
echo -n "  - GET /v1/cancers (HTTP 200 & valid JSON list)... "
CANCERS_RESP=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:${PORT_DEFAULT}/v1/cancers")
STATUS_CODE=$(echo "$CANCERS_RESP" | tail -n1)
BODY=${CANCERS_RESP%$'\n'*}
if [ "$STATUS_CODE" != "200" ]; then
    echo "FAILED! Expected HTTP 200, got ${STATUS_CODE}."
    exit 1
fi
echo "$BODY" | grep -q "canonical_name" || { echo "FAILED! Missing canonical_name in response."; exit 1; }
echo "PASSED."

# GET / with Accept: text/html
echo -n "  - GET / [Accept: text/html] (HTTP 200 & HTML)... "
HTML_RESP=$(curl -s -w "\n%{http_code}" -H "Accept: text/html" "http://127.0.0.1:${PORT_DEFAULT}/")
STATUS_CODE=$(echo "$HTML_RESP" | tail -n1)
BODY=${HTML_RESP%$'\n'*}
if [ "$STATUS_CODE" != "200" ]; then
    echo "FAILED! Expected HTTP 200, got ${STATUS_CODE}."
    exit 1
fi
echo "$BODY" | grep -qi "CancerInfo API" || { echo "FAILED! HTML missing title."; exit 1; }
echo "PASSED."

# GET / with Accept: application/json
echo -n "  - GET / [Accept: application/json] (HTTP 200 & JSON metadata)... "
JSON_RESP=$(curl -s -w "\n%{http_code}" -H "Accept: application/json" "http://127.0.0.1:${PORT_DEFAULT}/")
STATUS_CODE=$(echo "$JSON_RESP" | tail -n1)
BODY=${JSON_RESP%$'\n'*}
if [ "$STATUS_CODE" != "200" ]; then
    echo "FAILED! Expected HTTP 200, got ${STATUS_CODE}."
    exit 1
fi
echo "$BODY" | grep -q "\"name\":" || { echo "FAILED! JSON missing name key."; exit 1; }
echo "PASSED."

# GET /docs
echo -n "  - GET /docs (HTTP 200 Swagger UI)... "
DOCS_RESP=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:${PORT_DEFAULT}/docs")
STATUS_CODE=$(echo "$DOCS_RESP" | tail -n1)
if [ "$STATUS_CODE" != "200" ]; then
    echo "FAILED! Expected HTTP 200, got ${STATUS_CODE}."
    exit 1
fi
echo "PASSED."

# GET /redoc
echo -n "  - GET /redoc (HTTP 200 ReDoc UI)... "
REDOC_RESP=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:${PORT_DEFAULT}/redoc")
STATUS_CODE=$(echo "$REDOC_RESP" | tail -n1)
if [ "$STATUS_CODE" != "200" ]; then
    echo "FAILED! Expected HTTP 200, got ${STATUS_CODE}."
    exit 1
fi
echo "PASSED."

# GET /openapi.json
echo -n "  - GET /openapi.json (HTTP 200 OpenAPI schema)... "
OPENAPI_RESP=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:${PORT_DEFAULT}/openapi.json")
STATUS_CODE=$(echo "$OPENAPI_RESP" | tail -n1)
BODY=${OPENAPI_RESP%$'\n'*}
if [ "$STATUS_CODE" != "200" ]; then
    echo "FAILED! Expected HTTP 200, got ${STATUS_CODE}."
    exit 1
fi
echo "$BODY" | grep -q "\"openapi\":" || { echo "FAILED! Missing openapi key."; exit 1; }
echo "PASSED."

# Clean up default container & volume
docker rm -f "$CONTAINER_DEFAULT" > /dev/null
docker volume rm -f "$VOLUME_DEFAULT" > /dev/null
echo "Default port tests completed and container removed cleanly."

# -----------------------------------------------------------------------------
# 3. Test Custom Port (8081) Boot & HTTP Endpoints
# -----------------------------------------------------------------------------
echo ""
echo "[Step 3/5] Testing custom runtime port (PORT=${PORT_CUSTOM})..."
docker volume create "$VOLUME_CUSTOM" > /dev/null
docker run -d \
    --name "$CONTAINER_CUSTOM" \
    -e PORT="${PORT_CUSTOM}" \
    -e ENVIRONMENT=development \
    -e DATABASE_URL=sqlite:////app/data/cancerinfo.db \
    -p "${PORT_CUSTOM}:${PORT_CUSTOM}" \
    -v "${VOLUME_CUSTOM}:/app/data" \
    "$IMAGE_NAME"

docker exec "$CONTAINER_CUSTOM" alembic upgrade head
docker exec "$CONTAINER_CUSTOM" python scripts/bootstrap.py

wait_for_endpoint "$PORT_CUSTOM" "/v1/health" "$CONTAINER_CUSTOM"

echo "Validating endpoints on custom port (${PORT_CUSTOM}):"

# GET /v1/health on 8081
echo -n "  - GET /v1/health on port ${PORT_CUSTOM} (HTTP 200)... "
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT_CUSTOM}/v1/health")
if [ "$STATUS_CODE" != "200" ]; then
    echo "FAILED! Expected HTTP 200, got ${STATUS_CODE}."
    exit 1
fi
echo "PASSED."

# GET /v1/cancers on 8081
echo -n "  - GET /v1/cancers on port ${PORT_CUSTOM} (HTTP 200)... "
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT_CUSTOM}/v1/cancers")
if [ "$STATUS_CODE" != "200" ]; then
    echo "FAILED! Expected HTTP 200, got ${STATUS_CODE}."
    exit 1
fi
echo "PASSED."

# Check exec pattern / signal handling (uvicorn runs as PID 1, replacing shell)
echo -n "  - Verifying uvicorn process running as PID 1 in container... "
PID1_CMD=$(docker exec "$CONTAINER_CUSTOM" cat /proc/1/cmdline | tr '\0' ' ')
if echo "$PID1_CMD" | grep -q "uvicorn"; then
    echo "PASSED (PID 1 is uvicorn)."
else
    echo "FAILED! Expected uvicorn as PID 1, got: ${PID1_CMD}"
    exit 1
fi

# Clean up custom container & volume
docker rm -f "$CONTAINER_CUSTOM" > /dev/null
docker volume rm -f "$VOLUME_CUSTOM" > /dev/null
echo "Custom port tests completed and container removed cleanly."

# -----------------------------------------------------------------------------
# 4. Test Local SQLite Durability / Persistence Across Container Re-creation
# -----------------------------------------------------------------------------
echo ""
echo "[Step 4/5] Testing SQLite data persistence across container destruction & recreation..."

# Create dedicated persistent volume
docker volume create "$VOLUME_PERSIST" > /dev/null
echo "Created dedicated test volume: ${VOLUME_PERSIST}"

# Boot Container A attached to the volume
echo "Starting Container A (${CONTAINER_PERSIST_A})..."
docker run -d \
    --name "$CONTAINER_PERSIST_A" \
    -p "${PORT_DEFAULT}:${PORT_DEFAULT}" \
    -v "${VOLUME_PERSIST}:/app/data" \
    -e ENVIRONMENT=development \
    -e DATABASE_URL=sqlite:////app/data/cancerinfo.db \
    "$IMAGE_NAME"

# Apply migrations and bootstrap in Container A
echo "Applying migrations and controlled bootstrap in Container A..."
docker exec "$CONTAINER_PERSIST_A" alembic upgrade head
docker exec "$CONTAINER_PERSIST_A" python scripts/bootstrap.py

wait_for_endpoint "$PORT_DEFAULT" "/v1/health" "$CONTAINER_PERSIST_A"

# Verify that the SQLite database file exists in /app/data
echo -n "  - Checking SQLite DB exists at /app/data/cancerinfo.db in Container A... "
docker exec "$CONTAINER_PERSIST_A" test -f /app/data/cancerinfo.db
echo "PASSED."

# Insert a unique probe record into the database via Container A
echo "  - Inserting durability test probe record into Container A..."
docker exec "$CONTAINER_PERSIST_A" python -c "
from app.database.session import SessionLocal
from app.models import Cancer
db = SessionLocal()
probe = Cancer(
    slug='durability-probe-cancer',
    canonical_name='Durability Probe Cancer',
    anatomical_site='Validation System',
    description='Created during container durability verification'
)
db.add(probe)
db.commit()
db.close()
print('Probe cancer record inserted into SQLite database.')
"

# Verify probe cancer record is immediately retrievable via HTTP from Container A
echo -n "  - Verifying probe record via HTTP GET from Container A... "
PROBE_RESP=$(curl -s -f "http://127.0.0.1:${PORT_DEFAULT}/v1/cancers/durability-probe-cancer")
echo "$PROBE_RESP" | grep -q "Durability Probe Cancer" || { echo "FAILED! Record not found in Container A."; exit 1; }
echo "PASSED."

# Destroy Container A completely
echo "Destroying Container A completely (simulating failure / replacement)..."
docker stop "$CONTAINER_PERSIST_A" > /dev/null
docker rm "$CONTAINER_PERSIST_A" > /dev/null
echo "Container A has been stopped and deleted."

# Start fresh Container B attached to the SAME named volume
echo "Starting fresh Container B (${CONTAINER_PERSIST_B}) on the same volume..."
docker run -d \
    --name "$CONTAINER_PERSIST_B" \
    -p "${PORT_DEFAULT}:${PORT_DEFAULT}" \
    -v "${VOLUME_PERSIST}:/app/data" \
    -e ENVIRONMENT=development \
    -e DATABASE_URL=sqlite:////app/data/cancerinfo.db \
    "$IMAGE_NAME"

wait_for_endpoint "$PORT_DEFAULT" "/v1/health" "$CONTAINER_PERSIST_B"

# Verify probe record persisted into Container B via HTTP without re-running bootstrap
echo -n "  - Verifying probe record persists via HTTP GET in Container B... "
PROBE_RESP_B=$(curl -s -f "http://127.0.0.1:${PORT_DEFAULT}/v1/cancers/durability-probe-cancer")
echo "$PROBE_RESP_B" | grep -q "Durability Probe Cancer" || { echo "FAILED! Record did NOT persist into Container B!"; exit 1; }
echo "PASSED."

# Verify probe record directly in SQLite database inside Container B
echo -n "  - Verifying probe record in SQLite database session in Container B... "
docker exec "$CONTAINER_PERSIST_B" python -c "
from app.database.session import SessionLocal
from app.models import Cancer
db = SessionLocal()
probe = db.query(Cancer).filter(Cancer.slug == 'durability-probe-cancer').first()
assert probe is not None, 'Probe record missing in Container B database!'
assert probe.canonical_name == 'Durability Probe Cancer', f'Unexpected name: {probe.canonical_name}'
db.close()
print('Confirmed record matches expected values.')
"
echo "PASSED."

# Verify repeated bootstrap refusal inside Container B
echo -n "  - Verifying repeated bootstrap refusal inside Container B... "
if docker exec "$CONTAINER_PERSIST_B" python scripts/bootstrap.py > /dev/null 2>&1; then
    echo "FAILED! Repeated bootstrap did not refuse on populated database!"
    exit 1
fi
echo "PASSED (refused safely)."

# Clean up Container B & persistent volume
docker rm -f "$CONTAINER_PERSIST_B" > /dev/null
docker volume rm -f "$VOLUME_PERSIST" > /dev/null
echo "Persistence test completed successfully."

# -----------------------------------------------------------------------------
# 5. Final Summary
# -----------------------------------------------------------------------------
echo ""
echo "======================================================================"
echo " ALL CIAPI-L003 CONTAINER & MIGRATION VALIDATIONS PASSED"
echo " - Dynamic PORT runtime configuration: PASSED"
echo " - Absence of baked SQLite database: PASSED"
echo " - Absence of unit tests in production image: PASSED"
echo " - Packaging of Alembic migrations and bootstrap CLI: PASSED"
echo " - Default port (3000) & custom port (8081) boot: PASSED"
echo " - HTTP endpoints (/v1/health, /v1/cancers, /, /docs, /redoc, /openapi.json): PASSED"
echo " - Controlled bootstrap execution & repeated refusal: PASSED"
echo " - Local SQLite durability across container destruction & recreation: PASSED"
echo "======================================================================"
