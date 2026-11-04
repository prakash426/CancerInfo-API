"""Public citation lookup for saved fact IDs."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.endpoints.search import serialize_search_result
from app.core.errors import APIError
from app.database.session import get_db
from app.repositories.search_repo import SearchRepository
from app.schemas.common import MetaInfo
from app.schemas.search import FactsResponseOut

router = APIRouter(prefix="/facts", tags=["Facts"])


@router.get("", response_model=FactsResponseOut)
def get_facts(
    ids: str = Query(..., description="Comma separated content record or consensus item IDs, up to 50"),
    db: Session = Depends(get_db),
):
    requested = [part.strip() for part in ids.split(",")]
    if not all(requested) or len(requested) > 50:
        raise APIError("VALIDATION_ERROR", "ids must contain 1 to 50 nonempty IDs.", 422)

    raw_results = SearchRepository(db).by_ids(requested)
    items = [serialize_search_result(result) for result in raw_results]
    return FactsResponseOut(data=items, meta=MetaInfo(result_count=len(items)))
