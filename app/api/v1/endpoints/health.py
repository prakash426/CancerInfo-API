"""Database-backed readiness, independent of the static process liveness probes."""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.session import Base, get_db
from app.models import Cancer, Source
from app.schemas.search import HealthResponseOut

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)
START_TIME = time.monotonic()

# A hung database must fail closed fast instead of pinning orchestrator
# probes and workers: every readiness check runs in a bounded worker pool
# with a hard wall-clock deadline and pile-up guard. The pool matches the
# semaphore so excess probes get an immediate 503 with no queued backlog.
READINESS_DEADLINE_SECONDS = 3.0
_READINESS_MAX_CONCURRENT_PROBES = 4
_ready_executor = ThreadPoolExecutor(
    max_workers=_READINESS_MAX_CONCURRENT_PROBES, thread_name_prefix="readiness-probe")
_ready_permits = threading.Semaphore(_READINESS_MAX_CONCURRENT_PROBES)


@lru_cache(maxsize=1)
def expected_revision():
    from app.database.migration_check import get_head_revision
    return get_head_revision()


def _probe_database(db):
    """Run the full readiness check sequence; raises on any failure."""
    db.execute(text("SELECT 1")).scalar_one()
    if settings.is_production or settings.CHECK_MIGRATIONS_ON_STARTUP:
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        if revision != [expected_revision()]:
            raise RuntimeError("Database revision is not current")
    # Parse all managed columns without scanning corpus data. This also
    # detects a table/column lost after startup without modifying the DB.
    projections = ", ".join(
        f'(SELECT "{column.name}" FROM "{table.name}" LIMIT 0)'
        for table in Base.metadata.sorted_tables for column in table.columns)
    db.execute(text("SELECT " + projections)).first()
    source_count = db.query(Source).count()
    cancer_count = db.query(Cancer).count()
    return source_count, cancer_count


def _rollback_when_probe_unwinds(future, session):
    # Runs in the probe worker thread: same-thread session use stays safe
    # while the request thread has already returned its 503.
    try:
        try:
            future.result()
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
    finally:
        _ready_permits.release()


@router.get("/ready", response_model=HealthResponseOut,
            responses={503: {"model": HealthResponseOut, "description": "Database or required schema unavailable"}})
@router.get("/health", response_model=HealthResponseOut,
            responses={503: {"model": HealthResponseOut, "description": "Database or required schema unavailable"}})
def get_health(request: Request, response: Response, db: Session = Depends(get_db)):
    source_count = cancer_count = 0
    db_status = "connected"
    pending_probe = False
    acquired = False
    try:
        if not _ready_permits.acquire(blocking=False):
            raise TimeoutError("readiness probe concurrency guard")
        acquired = True
        try:
            future = _ready_executor.submit(_probe_database, db)
            try:
                source_count, cancer_count = future.result(timeout=READINESS_DEADLINE_SECONDS)
            except TimeoutError:
                if not future.done():
                    pending_probe = True
                    future.add_done_callback(
                        lambda fut, session=db: _rollback_when_probe_unwinds(fut, session))
                raise
        finally:
            if acquired and not pending_probe:
                _ready_permits.release()
    except Exception:
        if not pending_probe:
            try:
                db.rollback()
            except Exception:
                pass
        source_count = cancer_count = 0
        db_status = "unavailable"
        response.status_code = 503
        response.headers["Retry-After"] = "5"
        logger.warning("database_not_ready request_id=%s", request.state.request_id)
    return HealthResponseOut(
        status="healthy" if db_status == "connected" else "degraded",
        api_name=settings.APP_NAME, api_version=settings.APP_VERSION,
        database=db_status, timestamp=datetime.utcnow().isoformat() + "Z",
        uptime_seconds=round(time.monotonic() - START_TIME, 2),
        environment=settings.ENVIRONMENT, source_registry_count=source_count,
        approved_cancers_count=cancer_count,
    )
