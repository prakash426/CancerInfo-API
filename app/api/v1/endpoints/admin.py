"""
Administrative Endpoints (Protected by Admin API Key)
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import verify_admin_key
from app.database.session import get_db
from app.ingestion.pipeline import run_ingestion_for_source
from app.ingestion.seed import seed_database
from app.schemas.common import MetaInfo, StandardResponse
from app.sources.registry import list_registered_source_ids

router = APIRouter(prefix="/admin", tags=["Administrative (Protected)"], dependencies=[Depends(verify_admin_key)])


class IngestRequest(BaseModel):
    source_id: str


@router.post("/ingest", response_model=StandardResponse[dict])
async def trigger_source_ingestion(
    request: IngestRequest,
    db: Session = Depends(get_db),
):
    """
    Triggers an automated ingestion cycle for a specified registered source.
    Requires administrative authorization header.
    """
    valid_sources = list_registered_source_ids()
    if request.source_id not in valid_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source ID '{request.source_id}' is not a registered adapter. Available: {valid_sources}",
        )

    try:
        metrics = await run_ingestion_for_source(request.source_id, db)
        return StandardResponse(
            data=metrics,
            meta=MetaInfo(result_count=1),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed", response_model=StandardResponse[dict])
def trigger_seed(db: Session = Depends(get_db)):
    """
    Seeds initial taxonomy, sources, and verified baseline records if database is empty.
    Disabled in production environments.
    """
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Database seeding via administrative HTTP endpoint is strictly disabled in production. "
                "Use the controlled CLI bootstrap command instead."
            ),
        )

    seed_database(db)
    return StandardResponse(
        data={"message": "Seed routine executed successfully."},
        meta=MetaInfo(result_count=1),
    )
