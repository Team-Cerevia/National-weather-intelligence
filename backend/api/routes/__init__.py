"""Aggregated API router registering all Track D1 endpoint routers."""

from fastapi import APIRouter

from .incidents import router as incidents_router
from .reports import router as reports_router
from .stream import router as stream_router

api_router = APIRouter()

api_router.include_router(incidents_router, prefix="/incidents", tags=["incidents"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(stream_router, prefix="/stream", tags=["stream"])


@api_router.get("/health", tags=["health"], summary="Health check endpoint")
def health_check() -> dict[str, str]:
    """Return health status of API service."""
    return {"status": "healthy", "service": "national-weather-intelligence-api"}


__all__ = ["api_router"]
