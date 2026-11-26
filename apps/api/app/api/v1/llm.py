"""LLM runtime health and provider listing endpoints."""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.providers.llm import LLMProvider, LLMProviderFactory
from app.schemas.llm import LLMProviderInfo, LLMRuntimeHealth
from app.schemas.response import ApiResponse, ok

router = APIRouter(prefix="/llm", tags=["llm"])


def get_llm_provider(settings: Settings = Depends(get_settings)) -> LLMProvider:
    """Dependency providing the configured local LLMProvider."""
    return LLMProviderFactory.create("ollama", settings)


@router.get("/health", response_model=ApiResponse[LLMRuntimeHealth])
async def llm_health(
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> ApiResponse[LLMRuntimeHealth]:
    """Check local Ollama runtime availability and version."""
    health = await provider.health_check()
    return ok(health, version=settings.app_version)


@router.get("/providers", response_model=ApiResponse[list[LLMProviderInfo]])
async def list_llm_providers(
    settings: Settings = Depends(get_settings),
) -> ApiResponse[list[LLMProviderInfo]]:
    """List supported local LLM providers."""
    providers = [
        LLMProviderInfo(
            id="ollama",
            name="Ollama (Local)",
            description="Local-first LLM runtime using Ollama HTTP API.",
            is_local=True,
            configured_endpoint=settings.ollama_base_url,
        )
    ]
    return ok(providers, version=settings.app_version)
