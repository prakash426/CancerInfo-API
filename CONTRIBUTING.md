# Contributing to CancerInfo API

Thank you for your interest in contributing to **CancerInfo API**! Every pull request, clinical source citation check, and code contribution helps make cancer information more transparent, reliable, and accessible for everyone in the world.

---

## How You Can Contribute

1. **Suggest or Add New Authoritative Health Sources**:
   - We strictly aggregate from **Tier 1 (Government & Multilateral Public Health Bodies)** and **Tier 2 (Premier Accredited Cancer Centers & Societies)**.
   - We do _not_ ingest private sponsored content, unverified forums, or commercial blogs.
2. **Expand Canonical Cancer Mappings & Aliases**:
   - Add international colloquial names, abbreviations (e.g. `NSCLC`, `ALL`, `CML`), or ICD-O-3 codes in `app/ingestion/seed.py`.
3. **Enhance Taxonomy & Classification**:
   - Help refine extraction rules across our 37 standardized categories in `app/core/constants.py` and `app/normalization/taxonomy.py`.
4. **Develop Client SDKs & Community Templates**:
   - Build client libraries in Python, JavaScript/TypeScript, Go, Swift, Rust, or Kotlin.

---

## Development Setup & Workflow

The core service is Python/FastAPI. The supported launch runtime is Python 3.11 across local development, Docker, and CI.

```bash
# 1. Clone repository
git clone https://github.com/prakash426/CancerInfo-API.git
cd CancerInfo-API

# 2. Set up Python virtual environment & dependencies
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-cache-dir --require-hashes -r requirements.txt

# 3. Run the automated test suite
DATABASE_URL=sqlite:////tmp/cancerinfo-tests.db python -m pytest tests/ -v

# 4. Initialize a separate, empty development database explicitly
export DATABASE_URL=sqlite:////tmp/cancerinfo-development.db
alembic upgrade head
python scripts/bootstrap.py

# 5. Start local development server with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

### Pre-PR Validation Commands

Before opening a pull request, ensure all CI validation gates pass locally:

1. `python -m pip install --no-cache-dir --require-hashes -r requirements.txt` — Python dependencies install cleanly from the reproducible lock.
2. `python -m pip check` — Ensure dependency graph consistency.
3. `DATABASE_URL=sqlite:////tmp/cancerinfo-tests.db python -m pytest tests/ -v -ra -W default` — Run the full existing suite and meaningful regression tests for the changed behavior.
4. `python -c "from app.main import app; app.openapi()"` — OpenAPI 3.1 schema generates without error.
5. `curl -f http://localhost:3000/v1/health` — Local server health check returns 200 OK.
6. `./scripts/validate_container.sh` — Docker container builds cleanly without baked state, boots on dynamic PORT, passes all endpoint checks, and verifies data durability across container recreation.

---

## Code Quality Standards

- All new endpoints must include corresponding `pytest` tests under `tests/`.
- Ensure responses pass type validation in Pydantic schemas under `app/schemas/`.
- Every added medical fact **must** include its primary source URL and organization attribution.
- Respect our [Code of Conduct](CODE_OF_CONDUCT.md).

## Pull request checklist

- Branch from `main` and keep each pull request focused on one change.
- Describe what changed, any schema or data impact, and the exact tests you ran.
- Do not add a second dataset or serving implementation; the FastAPI service is the single source of truth.

## Data safety

- Application startup never creates or seeds tables. Run migrations and the controlled bootstrap explicitly against an empty development database.
- Local corpora, backups and private research stay untracked. `python scripts/check_local_artifacts.py` verifies the Git index without reading their contents.
- Use a disposable database for tests. Never run seed or ingestion against valuable data without an approved data procedure.
- Public content must pass exact-document rights and citation review. See [Content rights and attribution](docs/CONTENT_RIGHTS_AND_ATTRIBUTION.md) and [Publication by content type](docs/publication-use-policy.md).
