"""
CancerInfo API - Master Application Entry Point
"""
import html
import time
from pathlib import Path
import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.constants import MEDICAL_DISCLAIMER
from app.core.source_notices import (CDC_NOTICE, NHS_NOTICE, SOURCE_NOTICE, WHO_LICENSE_ID,
                                     WHO_LICENSE_URL, WHO_NOTICE)
from app.core.errors import (APIError, api_error_handler, generic_exception_handler,
                             validation_error_handler, http_error_handler)
from app.core.security import rate_limiter, client_address
from starlette.concurrency import run_in_threadpool
from app.database.session import engine
from app.schemas.common import ErrorResponse


# Startup schema verification must fail fast instead of hanging the boot
# sequence on an unresponsive database. Failures keep raising RuntimeError.
_STARTUP_VERIFY_TIMEOUT_SECONDS = 15.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce database schema verification in production or when explicitly configured
    if settings.is_production or settings.CHECK_MIGRATIONS_ON_STARTUP:
        import asyncio
        from app.database.migration_check import verify_database_schema_at_head
        try:
            await asyncio.wait_for(
                asyncio.to_thread(verify_database_schema_at_head, engine),
                timeout=_STARTUP_VERIFY_TIMEOUT_SECONDS)
        except TimeoutError as exc:
            raise RuntimeError(
                "Database schema validation failed: verification timed out after "
                f"{_STARTUP_VERIFY_TIMEOUT_SECONDS:g}s; refusing to serve on an unverified schema."
            ) from exc

    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        f"{settings.APP_DESCRIPTION}\n\n"
        f"**Medical Disclaimer:** {MEDICAL_DISCLAIMER}\n\n{SOURCE_NOTICE}"
    ),
    version=settings.APP_VERSION,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    responses={code: {"model": ErrorResponse} for code in (400, 401, 404, 405, 409, 422, 429, 500, 503)},
)


# Exception Handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)


@app.middleware("http")
async def request_metrics_and_rate_limit(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.monotonic()
    from app.core.publication_access import publication_use, approved_use
    use = approved_use(request.headers.get("X-API-Key"))
    token = publication_use.set(use)
    limit, remaining, reset = settings.RATE_LIMIT_PER_MINUTE, settings.RATE_LIMIT_PER_MINUTE, 60
    path = request.url.path
    exempt = path in {"/", "/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json",
                      "/v1/health", "/v1/ready", "/health", "/api/health"}
    try:
        response = None
        if not exempt:
            try:
                allowed, limit, remaining, reset = await run_in_threadpool(
                    rate_limiter.check, client_address(request))
            except Exception:
                logging.getLogger(__name__).error("rate_limit_unavailable request_id=%s", request_id)
                response = JSONResponse(status_code=503, content={"error": {
                    "code": "RATE_LIMIT_UNAVAILABLE", "message": "Request accounting is temporarily unavailable.",
                    "details": {}}}, headers={"Retry-After": "5"})
                remaining = 0
            else:
                if not allowed:
                    response = JSONResponse(status_code=429, content={"error": {
                        "code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please wait before retrying.",
                        "details": {"retry_after_seconds": reset}}}, headers={"Retry-After": str(reset)})
        if response is None:
            try:
                response = await call_next(request)
            except Exception as exc:
                logging.getLogger(__name__).error("request_failed request_id=%s error_type=%s", request_id, type(exc).__name__)
                response = await generic_exception_handler(request, exc)
    finally:
        publication_use.reset(token)
    # Apply the same privacy and compliance contract to success and failure paths.
    response.headers["X-Publication-Use"] = use
    response.headers["Cache-Control"] = "private, no-store"
    response.headers.append("Vary", "X-API-Key")
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-MS"] = f"{(time.monotonic() - start_time) * 1000:.2f}"
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset)
    response.headers["X-Disclaimer"] = "Informational API only. Not medical advice."
    response.headers["X-Medical-Disclaimer"] = "Informational only; not medical advice"
    response.headers["X-CancerInfo-API-Version"] = settings.APP_VERSION
    return response


# Keep CORS outside request accounting so browsers can read denial/error responses.
# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-Publication-Use",
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

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _render_portal() -> str:
    """Fill the developer portal template with the current notices (HTML-escaped)."""
    page = (STATIC_DIR / "portal.html").read_text(encoding="utf-8")
    values = {
        "APP_VERSION": settings.APP_VERSION,
        "MEDICAL_DISCLAIMER": MEDICAL_DISCLAIMER,
        "NHS_NOTICE": NHS_NOTICE,
        "CDC_NOTICE": CDC_NOTICE,
        "WHO_NOTICE": WHO_NOTICE,
        "WHO_LICENSE_ID": WHO_LICENSE_ID,
        "WHO_LICENSE_URL": WHO_LICENSE_URL,
    }
    for key, value in values.items():
        page = page.replace("{{" + key + "}}", html.escape(str(value)))
    return page


PORTAL_HTML = _render_portal()


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(STATIC_DIR / "favicon.png", media_type="image/png")


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

    return HTMLResponse(content=PORTAL_HTML)
