"""
API v1 Router Aggregator
"""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    admin,
    cancers,
    categories,
    countries,
    coverage,
    facts,
    health,
    search,
    sources,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(cancers.router)
api_router.include_router(search.router)
api_router.include_router(facts.router)
api_router.include_router(sources.router)
api_router.include_router(categories.router)
api_router.include_router(countries.router)
api_router.include_router(coverage.router)
api_router.include_router(admin.router)
