"""API v1 router aggregation."""

from fastapi import APIRouter

from .agents import router as agents_router
from .conversations import router as conversations_router
from .health import router as health_router
from .llm import router as llm_router
from .models import router as models_router
from .speech import router as speech_router
from .voice import router as voice_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(agents_router)
api_v1_router.include_router(llm_router)
api_v1_router.include_router(models_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(speech_router)
api_v1_router.include_router(voice_router)
