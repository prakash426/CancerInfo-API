<div align="center">

# 🎗️ CancerInfo API

### _A Python API for structured cancer information with source metadata_

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![OpenAPI 3.1](https://img.shields.io/badge/OpenAPI-3.1-6BA539?style=for-the-badge&logo=openapiinitiative&logoColor=white)](rapidapi/rapidapi-openapi.json)
[![RapidAPI](https://img.shields.io/badge/RapidAPI-launch_planned-0052CC?style=for-the-badge&logo=rapidapi&logoColor=white)](rapidapi/RAPIDAPI_LISTING_GUIDE.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Tests: pytest suite](https://img.shields.io/badge/pytest-passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](#automated-testing)
[![Docker](https://img.shields.io/badge/Docker-portable_%26_durable-2496ED?style=for-the-badge&logo=docker&logoColor=white)](docker-compose.yml)

<p align="center">
  <b>Built with code. Powered by love. Serving humanity free of charge.</b><br>
  <i>"Because when someone you love is fighting cancer, finding trustworthy medical knowledge shouldn't be another battle."</i>
</p>

[Quickstart](#-local-quickstart) • [Why This Exists](#-why-this-exists-the-story-behind-the-code) • [API Reference](#-api-endpoints) • [RapidAPI Guide](rapidapi/RAPIDAPI_LISTING_GUIDE.md) • [Architecture](#-architecture) • [App Ideas](docs/APP_IDEAS_GUIDE.md)

---

</div>

## Current project status

Reviewed September 22, 2026 against Python refactor `1199f735e3d77b5c1ada35e6451c7a5b4e36d063`. The API product is FastAPI with SQLAlchemy storage. The former Node JSON server is removed. React is archived in `cancerinfo-explorer-ui/` and its ZIP for a possible later demonstration; it is not required to run the API.

**Prelaunch, acceptance open.** The 28 existing tests pass locally on Python 3.12.2 with 425 warnings. This is not a coverage percentage, image test, PostgreSQL test or clinical approval. Isolated probes reproduced restricted-source publication, false ingestion success after every fetch failed, unknown-category fallback and missing safety/request headers on 429. See [validation evidence](docs/VALIDATION_GUIDE.md) and [architecture and launch assessment](docs/CODEBASE_ATLAS.md).

The seed contains 7 cancer entities, 5 with content, 21 records and 5 populated categories out of 37 defined. Source dates and rights labels need review before publication. No deployed URL or RapidAPI acceptance is verified. October 4 remains the launch target; September 27 is the intended submission checkpoint for seven days of lead time. September 28 is the adjustable six-day fallback.

## 💜 Why This Exists: The Story Behind the Code

> _"Code cannot cure cancer. But code can destroy the fog of misinformation, dismantle knowledge paywalls, and place verified, life-saving clinical facts directly into the hands of every developer, doctor, caregiver, and child fighting for their family."_

This project was not born out of a hackathon prompt or a venture pitch.

**It was born in hospital waiting rooms, holding my parents' hands.**

Within a span that felt like an eternity, **both my mother and my father were diagnosed with cancer.**

If you have ever loved someone walking through that valley, you know the suffocating weight that follows. The diagnosis hits like an earthquake. Then comes the second trauma: navigating the labyrinth of cancer information.

Late at night, while my parents slept between chemotherapy cycles, I found myself desperately searching online:

- Conflicting forum posts and algorithmic clickbait.
- Contradictory screening ages between different countries.
- Paywalled medical research papers written in opaque jargon.
- No direct way to know: _Where did this fact come from? Is this guideline current? Does this apply in our country?_

I am an engineer. In software, we demand immutability, cryptographic provenance, and single sources of truth. Yet in the fight for our parents' lives, the internet offered guesswork and uncertainty.

I made a silent promise: **I would build the public API I desperately needed on those dark nights.**

**CancerInfo API** is the project built toward that promise. Its goals are:

- **100% Free Forever**: No paywalls, no monetization gates, no commercial exploitation.
- **Record-Level Source Transparency**: Preserve the exact document, organization, jurisdiction and attribution behind each published record. The current model stores these links, but review and publication enforcement remain launch requirements. Registry entries include NCI, WHO, NHS, Cancer Australia and CDC; registration does not certify rights or supported ingestion.
- **Structured for Builders**: JSON retrieval, taxonomy resolution, country filtering and heuristic text search for informational integrations. The service does not calculate screening eligibility, provide treatment advice or guarantee that a downstream AI system avoids hallucinations.

_To my mom and dad: This code is dedicated to your courage, your grace, and every family still fighting._ 🕊️

---

## ⚡ Local quickstart

### Set up the Python service

Use a virtual environment and a separate local database. Database schema is versioned with Alembic migrations, and baseline data is initialized via controlled bootstrap. Production startup never silently creates tables or seeds data. No Node installation is needed. Supported launch runtime is Python 3.11.

```bash
git clone https://github.com/Prakash-Merepala/CancerInfo-API.git
cd CancerInfo-API
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --no-cache-dir --require-hashes -r requirements.txt
export DATABASE_URL=sqlite:////tmp/cancerinfo-local.db
alembic upgrade head
python scripts/bootstrap.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 3000
```

Check out the reviewed Python branch before running these commands if the repository default differs. The root `.env.example` documents the Python API settings only. Gemini and AI Studio hosting variables are not required. Set a unique admin secret in your deployment environment before exposing any administrative endpoint; never commit the real value.

### 1. Test via cURL

```bash
# Health check
curl -s http://localhost:3000/v1/health

# Inspect seeded symptoms and source metadata; not clinical approval
curl -s "http://localhost:3000/v1/cancers/breast-cancer/symptoms?country=US" | jq .

# Inspect available seeded screening content and each record jurisdiction
curl -s "http://localhost:3000/v1/cancers/colorectal-cancer/screening?country=GB" | jq .

# Search acronyms (CRC -> Colorectal Cancer)
curl -s "http://localhost:3000/v1/search?q=CRC" | jq .
```

### 2. Python

```python
import requests

# Fetch available records and inspect their source metadata
response = requests.get(
    "http://localhost:3000/v1/cancers/breast-cancer/symptoms",
    params={"country": "US"}, timeout=20
)
response.raise_for_status()
for record in response.json()["data"]["records"]:
    print(record["content"])
    for citation in record["sources"]:
        print(citation["organization"], citation["url"])
```

### 3. JavaScript / TypeScript

```typescript
const res = await fetch(
  "http://localhost:3000/v1/cancers/colorectal-cancer/screening?country=GB",
);
if (!res.ok) throw new Error(`API request failed: ${res.status}`);
const { data } = await res.json();
for (const record of data.records) {
  console.log(record.content, record.jurisdiction);
  for (const citation of record.sources)
    console.log(citation.organization, citation.url);
}
```

### 4. Container Development (Docker Compose)

```bash
git clone https://github.com/Prakash-Merepala/CancerInfo-API.git
cd CancerInfo-API
docker compose up -d
```

- **Dynamic Port:** Configured via `PORT` (default: `3000`). Example: `PORT=8080 docker compose up -d`.
- **Durable Local Storage:** In development, SQLite data is stored at `/app/data/cancerinfo.db` backed by the named volume `cancerinfo_data`, persisting across container restarts and recreation.
- **Production Database Contract:** In production, external PostgreSQL is required:
  ```bash
  ENVIRONMENT=production
  DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:<port>/<dbname>
  ```
  When using external PostgreSQL, no persistent local volume is needed. Container-local SQLite is strictly for development and validation. Never commit database credentials or connection secrets to Git.
- **Automated Container Validation:** Run `./scripts/validate_container.sh` to test container builds, dynamic port binding, endpoint availability, and SQLite durability across container destruction and recreation.

---

## 🔬 Core Architectural Principle: Fact-Level Provenance

```
                 UNVERIFIED INTERNET                        CANCERINFO API
             ┌─────────────────────────┐               ┌───────────────────────┐
             │ Unverified Health Blogs │               │  National Cancer Inst │
             │ Anonymous Forum Advice  │────► ❌       │  World Health Org     │
             │ AI Generated Guesswork  │               │  NHS UK & Cancer Aus  │
             └─────────────────────────┘               └───────────┬───────────┘
                                                                   │
                                                   Normalized Parsing & Validation
                                                                   │
                                                                   ▼
                                                       ┌───────────────────────┐
                                                       │ CANONICAL DATA RECORD │
                                                       ├───────────────────────┤
                                                       │ • Clean Markdown Fact │
                                                       │ • Direct Source URL   │
                                                       │ • Organization Name   │
                                                       │ • Trust Tier (Tier 1) │
                                                       │ • Legal Attribution   │
                                                       │ • Verification Date   │
                                                       │ • Country / Scope     │
                                                       └───────────────────────┘
```

The following is an illustrative response fragment, not a clinical example or a guarantee. The current implementation does not yet enforce every publication requirement. Unknown publisher dates should remain null rather than be inferred from retrieval time:

```json
{
  "category": "overview",
  "content": "Illustrative content omitted; use a reviewed source record.",
  "jurisdiction": { "scope": "COUNTRY", "country": "US" },
  "sources": [
    {
      "source_id": "nci-us",
      "organization": "National Cancer Institute",
      "url": "https://www.cancer.gov/",
      "source_updated_at": null
    }
  ]
}
```

This fragment is abbreviated. The homepage above is illustrative, not an acceptable exact-document citation for a published record. See the runtime schema and the provenance requirements in the architecture assessment.

---

## 🚀 API Endpoints

| Method | Endpoint                          | Description                                                                 |
| :----- | :-------------------------------- | :-------------------------------------------------------------------------- |
| `GET`  | `/v1/health`                      | System health, database connectivity, uptime, and loaded registry metrics   |
| `GET`  | `/v1/cancers`                     | List all canonical cancers with pagination and anatomical site filter       |
| `GET`  | `/v1/cancers/{cancer}`            | Detail view: canonical name, ICD codes, aliases, and available sections     |
| `GET`  | `/v1/cancers/{cancer}/sections`   | Summary of populated categories, record counts, and jurisdictions           |
| `GET`  | `/v1/cancers/{cancer}/sources`    | Sources linked to active records; source-rights gating remains open         |
| `GET`  | `/v1/cancers/{cancer}/versions`   | Stored version entries; uniqueness and historical provenance need repair    |
| `GET`  | `/v1/cancers/{cancer}/{category}` | **Core Knowledge**: Normalized facts with citation URLs and country filters |
| `GET`  | `/v1/search`                      | Multi-factor search resolving abbreviations (`CRC`), aliases, and symptoms  |
| `GET`  | `/v1/sources`                     | Seeded registry metadata; permission labels require document review         |
| `GET`  | `/v1/sources/{id}`                | Detailed profile for an individual health authority                         |
| `GET`  | `/v1/categories`                  | Catalog of all 37 standardized cancer knowledge categories                  |
| `GET`  | `/v1/countries`                   | Global jurisdictions represented across the knowledge base                  |
| `GET`  | `/v1/coverage`                    | Stored active-record coverage counts; not clinical or rights approval       |
| `GET`  | `/docs`                           | Interactive Swagger UI console                                              |
| `GET`  | `/redoc`                          | High-readability ReDoc API documentation                                    |
| `GET`  | `/openapi.json`                   | OpenAPI 3.1 schema specification                                            |

---

## 🌐 Publish & Deploy Free to the Community

Publication is planned and remains conditional on the acceptance gates:

- **[RapidAPI Publishing Guide](rapidapi/RAPIDAPI_LISTING_GUIDE.md)**: The static specification has 8 paths while FastAPI generates 15 including admin routes. Generate and test a public-only export before import; verify the collection separately.
- **[Migrations & Controlled Initialization Guide](docs/MIGRATIONS_AND_INITIALIZATION.md)**: Alembic PostgreSQL schema versioning, non-mutating startup validation, legacy table preservation (`cancer_content`), and deployment runbook for Render and Neon.
- **[Free Cloud Hosting Guide](docs/FREE_HOSTING_DEPLOYMENT.md)**: Deployment checklist and provider decision notes. Hosting cost, persistence and capacity require verification for the chosen service.
- **[Validation & Testing Guide](docs/VALIDATION_GUIDE.md)**: Quality assurance runbook for CI/CD and production verification.
- **[App Ideas & Ecosystem Recipes](docs/APP_IDEAS_GUIDE.md)**: Future integration concepts with explicit data and safety prerequisites; they are not current API capabilities.
- **[GitHub Open API Ecosystem Stats](docs/GITHUB_ECOSYSTEM_STATS.md)**: Project discovery checklist and evidence requirements; no verified project adoption statistics are available.

---

<a id="-architecture"></a>

## 🛠️ Tech Stack & Architecture

- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic 1.13+ (versioned migrations), SQLite (local dev/tests) / PostgreSQL (production required), Uvicorn.
- **Developer Documentation & Portal**: Built directly into FastAPI: Interactive Swagger UI (`/docs`), ReDoc (`/redoc`), OpenAPI 3.1 spec (`/openapi.json`), and Developer Landing (`/`).
- **Request handling**: Request ID, timing and disclaimer headers on the normal middleware path; process-local rate limiting. The early 429 response omits several normal headers, and proxy trust requires hardening.
- **Automated Testing**: Complete pytest suite passed with full fact-level provenance validation. No coverage percentage or production acceptance is claimed.
- **Companion UI**: Archived in `cancerinfo-explorer-ui/` and `cancerinfo-explorer-ui.zip`. A runnable standalone build and the previously mentioned archive tag are not verified. Missing service imports require follow-up before revival.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CANCERINFO FASTAPI RUNTIME                      │
├────────────────────────────────────────────────────────────────────────┤
│  Incoming Client (cURL / Python / RapidAPI / Browser / Mobile App)     │
│                                  │                                     │
│                     [FastAPI ASGI Middleware]                          │
│         • Request ID Tracking    • Rate Limiting (120 req/min)         │
│         • Millisecond Timing     • Safety & Disclaimer Headers         │
│         • Root Health Probes     • Automatic CORS Handling             │
│                                  │                                     │
│                    ┌─────────────┴─────────────┐                       │
│                    ▼                           ▼                       │
│         [Core /v1 REST API]            [Documentation Engine]          │
│         • /v1/cancers, /symptoms       • Interactive Swagger (/docs)   │
│         • /v1/search (Acronyms & text) • ReDoc Documentation (/redoc)  │
│         • /v1/sources & /v1/coverage   • OpenAPI 3.1 Schema Spec       │
│         • Jurisdictional Filtering     • Developer Portal (/)          │
│                    │                                                   │
│                    ▼                                                   │
│         [Relational SQLite / Neon PostgreSQL]                          │
│         • Canonical Cancers & Aliases                                  │
│         • Source Registry & Licensing Tiers                            │
│         • Provenance Records & Version History                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

<a id="automated-testing"></a>

## 🧪 Automated Testing

Run the existing regression suite against an isolated database:

```bash
DATABASE_URL=sqlite:////tmp/cancerinfo-tests.db python3 -m pytest tests/ -v
```

The suite samples the following areas; it does not prove exhaustive coverage:

- Health and database connectivity (`/v1/health`, `/health`, `/api/health`)
- Canonical cancer slug resolution and pagination
- Clinical abbreviation matching (`CRC` -> `colorectal-cancer`)
- Fact-level provenance schema validation
- Jurisdictional filtering (`country=US`, `country=GB`)
- Citation fields on seeded responses; multi-source update correctness remains open
- The 37-category catalog and selected normalization rules
- Normal success-response headers; error-path/header and robust limiter acceptance remain open

---

## ⚠️ Legal & Clinical Disclaimer

> **IMPORTANT:** CancerInfo API provides public informational data aggregated from authoritative health organizations for developers, researchers, caregivers, and public-health products. **It does not provide medical diagnosis, personal treatment recommendations, individualized drug selection or dosage, or replace licensed medical professionals.** Always consult a qualified oncologist or physician for clinical decisions.

---

## 🤝 Contributing

We welcome pull requests from developers, bioinformaticians, oncologists, and patient advocates worldwide!
Please read our **[Contributing Guidelines](CONTRIBUTING.md)** and **[Code of Conduct](CODE_OF_CONDUCT.md)** to get started.

---

<div align="center">

### Dedicated with infinite love to my parents, and to every cancer warrior across the world.

_If this project touches your heart or helps your work, please star the repository on GitHub to help other developers find it._ ⭐

**CancerInfo API — Free knowledge for a cancer-free future.**

</div>
