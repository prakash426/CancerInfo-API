"""
CancerInfo API - Master Application Entry Point
"""
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.constants import MEDICAL_DISCLAIMER
from app.core.errors import APIError, api_error_handler, generic_exception_handler
from app.core.security import rate_limiter
from app.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce database schema verification in production or when explicitly configured
    if settings.is_production or settings.CHECK_MIGRATIONS_ON_STARTUP:
        from app.database.migration_check import verify_database_schema_at_head
        verify_database_schema_at_head(engine)

    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        f"{settings.APP_DESCRIPTION}\n\n"
        f"**Medical Disclaimer:** {MEDICAL_DISCLAIMER}"
    ),
    version=settings.APP_VERSION,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-Response-Time-MS",
        "X-Medical-Disclaimer",
        "X-Disclaimer",
        "X-CancerInfo-API-Version",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
    ],
)

# Exception Handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.middleware("http")
async def request_metrics_and_rate_limit(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Client IP identification
    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    # Bypass rate limiter for internal docs, openapi, and health check endpoints
    path = request.url.path
    is_exempt = (
        path.startswith("/docs")
        or path.startswith("/redoc")
        or path == "/openapi.json"
        or path == "/v1/health"
        or path == "/health"
        or path == "/api/health"
        or path == "/"
    )
    if not is_exempt:
        allowed, limit, remaining, reset = rate_limiter.check(client_ip)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please wait before retrying.",
                        "details": {"retry_after_seconds": reset},
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                    "Retry-After": str(reset),
                },
            )
    else:
        limit, remaining, reset = settings.RATE_LIMIT_PER_MINUTE, settings.RATE_LIMIT_PER_MINUTE, 60

    response: Response = await call_next(request)

    # Response headers
    process_time = (time.time() - start_time) * 1000.0
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-MS"] = f"{process_time:.2f}"
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset)
    response.headers["X-Disclaimer"] = "Informational API only. Not medical advice."
    response.headers["X-Medical-Disclaimer"] = "Informational only; not medical advice"
    response.headers["X-CancerInfo-API-Version"] = settings.APP_VERSION

    return response


# Root and Platform Health Probes
@app.get("/health", tags=["Health"], include_in_schema=False)
@app.get("/api/health", tags=["Health"], include_in_schema=False)
def root_health():
    """
    Standard platform and infrastructure health probe.
    Returns status: ok
    """
    return {"status": "ok"}


# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
def root(request: Request):
    """
    Developer root endpoint.
    Returns developer portal documentation and quick links.
    """
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return {
            "name": settings.APP_NAME,
            "description": settings.APP_DESCRIPTION,
            "version": settings.APP_VERSION,
            "documentation": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "health": "/v1/health",
            "disclaimer": MEDICAL_DISCLAIMER,
        }

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CancerInfo API - Developer Portal</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --primary: #0284c7;
      --primary-hover: #0369a1;
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.6;
      color: var(--text);
      background-color: var(--bg);
      margin: 0;
      padding: 32px 16px;
    }}
    .container {{
      max-width: 960px;
      margin: 0 auto;
    }}
    .header {{
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      padding: 36px 32px;
      border-radius: 16px;
      border: 1px solid var(--card-border);
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
      margin-bottom: 24px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(2, 132, 199, 0.15);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 4px 12px;
      border-radius: 9999px;
      font-weight: 600;
      font-size: 0.8rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin-bottom: 16px;
    }}
    h1 {{
      font-size: 2.25rem;
      font-weight: 800;
      margin: 0 0 12px 0;
      color: #ffffff;
      letter-spacing: -0.025em;
    }}
    .subtitle {{
      color: var(--text-muted);
      font-size: 1.1rem;
      margin: 0 0 24px 0;
      max-width: 720px;
    }}
    .btn-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--primary);
      color: white;
      padding: 10px 20px;
      border-radius: 8px;
      text-decoration: none;
      font-weight: 600;
      font-size: 0.95rem;
      transition: all 0.2s ease;
      border: 1px solid transparent;
    }}
    .btn:hover {{
      background: var(--primary-hover);
      transform: translateY(-1px);
    }}
    .btn-secondary {{
      background: #1e293b;
      color: #f1f5f9;
      border: 1px solid var(--card-border);
    }}
    .btn-secondary:hover {{
      background: #334155;
      color: #ffffff;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 24px;
    }}
    .card h3 {{
      margin-top: 0;
      font-size: 1.15rem;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    pre {{
      background: #090d16;
      border: 1px solid #1e293b;
      color: #38bdf8;
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.875rem;
      margin: 12px 0 0 0;
    }}
    code {{
      font-family: 'JetBrains Mono', monospace;
    }}
    .disclaimer {{
      background: rgba(239, 68, 68, 0.1);
      border-left: 4px solid #ef4444;
      padding: 16px;
      color: #fca5a5;
      font-size: 0.875rem;
      border-radius: 0 8px 8px 0;
      margin-top: 24px;
    }}
    .sources-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }}
    .source-tag {{
      background: #0f172a;
      border: 1px solid #334155;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.8rem;
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <span class="badge">🎗️ Verified Clinical Knowledge API</span>
      <h1>CancerInfo API</h1>
      <p class="subtitle">A free, structured, global, source-transparent REST API aggregating clinical oncology data with fact-level provenance from world-leading public health authorities.</p>
      
      <div class="btn-group">
        <a class="btn" href="/docs">⚡ Interactive Swagger UI (/docs)</a>
        <a class="btn btn-secondary" href="/redoc">📖 ReDoc Specification (/redoc)</a>
        <a class="btn btn-secondary" href="/v1/health">💚 Health Status (/v1/health)</a>
        <a class="btn btn-secondary" href="/openapi.json">📜 OpenAPI Schema</a>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>🔍 Quick Test Endpoints</h3>
        <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 8px;">Run these sample queries directly against the live backend:</p>
        <pre><code># 1. Search by abbreviation or symptom
curl -s http://localhost:3000/v1/search?q=breast+cancer | jq

# 2. Symptoms with fact-level provenance
curl -s http://localhost:3000/v1/cancers/breast-cancer/symptoms?country=US | jq

# 3. Screening guidelines by jurisdiction
curl -s http://localhost:3000/v1/cancers/colorectal-cancer/screening | jq</code></pre>
      </div>

      <div class="card">
        <h3>🏛️ Source Transparency Registry</h3>
        <p style="color: var(--text-muted); font-size: 0.9rem;">Every medical statement is traced to source URL, retrieved date, and legal attribution:</p>
        <div class="sources-list">
          <span class="source-tag">National Cancer Institute (US)</span>
          <span class="source-tag">World Health Organization (Global)</span>
          <span class="source-tag">National Health Service (UK)</span>
          <span class="source-tag">Cancer Australia (AU)</span>
        </div>
        <pre><code># Inspect source audit registry
curl -s http://localhost:3000/v1/sources | jq
curl -s http://localhost:3000/v1/coverage | jq</code></pre>
      </div>
    </div>

    <div class="disclaimer">
      <strong>Clinical Disclaimer:</strong> {MEDICAL_DISCLAIMER}
    </div>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

