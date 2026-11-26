"""API v1 router aggregation."""

from fastapi import APIRouter

from .agents import router as agents_router
from .health import router as health_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(agents_router)
