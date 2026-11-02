"""Database-backed readiness, independent of the static process liveness probes."""
import logging
import time
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


@lru_cache(maxsize=1)
def expected_revision():
    from app.database.migration_check import get_head_revision
    return get_head_revision()


@router.get("/ready", response_model=HealthResponseOut,
            responses={503: {"model": HealthResponseOut, "description": "Database or required schema unavailable"}})
@router.get("/health", response_model=HealthResponseOut,
            responses={503: {"model": HealthResponseOut, "description": "Database or required schema unavailable"}})
def get_health(request: Request, response: Response, db: Session = Depends(get_db)):
    source_count = cancer_count = 0
    db_status = "connected"
    try:
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
    except Exception:
        db.rollback()
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
