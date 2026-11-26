"""Model management endpoints (discovery, pull, progress, cancel, delete, default)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.health import get_storage
from app.api.v1.llm import get_llm_provider
from app.core.config import Settings, get_settings
from app.providers.llm import LLMProvider
from app.providers.storage import StorageProvider
from app.schemas.llm import (
    DefaultModelRequest,
    ModelPullRequest,
    ModelPullTask,
    ModelsOverview,
)
from app.schemas.response import ApiResponse, ok
from app.services.model_manager import ModelManager

router = APIRouter(prefix="/models", tags=["models"])


def get_model_manager(
    provider: LLMProvider = Depends(get_llm_provider),
    storage: StorageProvider = Depends(get_storage),
) -> ModelManager:
    """Dependency providing the ModelManager."""
    return ModelManager(provider=provider, storage=storage)


@router.get("", response_model=ApiResponse[ModelsOverview])
async def list_models(
    settings: Settings = Depends(get_settings),
    manager: ModelManager = Depends(get_model_manager),
) -> ApiResponse[ModelsOverview]:
    """Get Ollama runtime status, installed models, default model, and recommendations."""
    overview = await manager.get_overview()
    return ok(overview, version=settings.app_version)


@router.post("/refresh", response_model=ApiResponse[ModelsOverview])
async def refresh_models(
    settings: Settings = Depends(get_settings),
    manager: ModelManager = Depends(get_model_manager),
) -> ApiResponse[ModelsOverview]:
    """Refresh installed models from the local LLM runtime."""
    overview = await manager.get_overview()
    return ok(overview, version=settings.app_version)


@router.post("/default", response_model=ApiResponse[dict[str, str]])
async def set_default_model(
    payload: DefaultModelRequest,
    settings: Settings = Depends(get_settings),
    manager: ModelManager = Depends(get_model_manager),
) -> ApiResponse[dict[str, str]]:
    """Persist the user's default local LLM model selection."""
    selected = manager.set_default_model_id(payload.model_id)
    return ok({"default_model_id": selected}, version=settings.app_version)


@router.post("/pull", response_model=ApiResponse[ModelPullTask], status_code=status.HTTP_202_ACCEPTED)
async def pull_model(
    payload: ModelPullRequest,
    settings: Settings = Depends(get_settings),
    manager: ModelManager = Depends(get_model_manager),
) -> ApiResponse[ModelPullTask]:
    """Start pulling a model in the background via Ollama."""
    task = manager.start_pull(payload.model_id)
    return ok(task, version=settings.app_version)


@router.get("/pull/{task_id}", response_model=ApiResponse[ModelPullTask])
async def get_pull_status(
    task_id: str,
    settings: Settings = Depends(get_settings),
    manager: ModelManager = Depends(get_model_manager),
) -> ApiResponse[ModelPullTask]:
    """Poll progress for an active or recent model pull task."""
    task = manager.get_pull_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Pull task '{task_id}' was not found.")
    return ok(task, version=settings.app_version)


@router.post("/pull/{task_id}/cancel", response_model=ApiResponse[ModelPullTask])
async def cancel_pull(
    task_id: str,
    settings: Settings = Depends(get_settings),
    manager: ModelManager = Depends(get_model_manager),
) -> ApiResponse[ModelPullTask]:
    """Cancel a running model pull task."""
    task = manager.cancel_pull(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Pull task '{task_id}' was not found.")
    return ok(task, version=settings.app_version)


@router.delete("/{model_id:path}", response_model=ApiResponse[dict[str, str | bool]])
async def delete_model(
    model_id: str,
    settings: Settings = Depends(get_settings),
    manager: ModelManager = Depends(get_model_manager),
) -> ApiResponse[dict[str, str | bool]]:
    """Delete an installed model from the local LLM runtime."""
    await manager.delete_model(model_id)
    return ok({"deleted": True, "model_id": model_id}, version=settings.app_version)
