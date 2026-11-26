"""Agent CRUD, templates, and lifecycle API endpoints."""

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.health import get_storage
from app.core.config import Settings, get_settings
from app.providers.storage import StorageProvider
from app.repositories.agent_repository import AgentRepository
from app.schemas.agent import (
    Agent,
    AgentCreate,
    AgentStatus,
    AgentTemplate,
    AgentType,
    AgentUpdate,
)
from app.schemas.response import ApiResponse, ok
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


def get_agent_service(storage: StorageProvider = Depends(get_storage)) -> AgentService:
    """Dependency providing an AgentService backed by StorageProvider."""
    return AgentService(AgentRepository(storage))


@router.get("/templates", response_model=ApiResponse[list[AgentTemplate]])
async def list_agent_templates(
    settings: Settings = Depends(get_settings),
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[list[AgentTemplate]]:
    """Return built-in starter agent templates."""
    return ok(service.list_templates(), version=settings.app_version)


@router.get("", response_model=ApiResponse[list[Agent]])
async def list_agents(
    status_filter: AgentStatus | None = Query(default=None, alias="status"),
    agent_type: AgentType | None = Query(default=None, alias="type"),
    search: str | None = Query(default=None, max_length=100),
    settings: Settings = Depends(get_settings),
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[list[Agent]]:
    """List agents with optional status, type, and search filters."""
    agents = await service.list_agents(
        status=status_filter,
        agent_type=agent_type,
        search=search,
    )
    return ok(agents, version=settings.app_version)


@router.post("", response_model=ApiResponse[Agent], status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    settings: Settings = Depends(get_settings),
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[Agent]:
    """Create a new AI agent (starts in DRAFT status)."""
    agent = await service.create_agent(payload)
    return ok(agent, version=settings.app_version)


@router.get("/{agent_id}", response_model=ApiResponse[Agent])
async def get_agent(
    agent_id: str,
    settings: Settings = Depends(get_settings),
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[Agent]:
    """Retrieve a single agent by ID."""
    agent = await service.get_agent(agent_id)
    return ok(agent, version=settings.app_version)


@router.put("/{agent_id}", response_model=ApiResponse[Agent])
async def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    settings: Settings = Depends(get_settings),
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[Agent]:
    """Update an existing agent's configuration."""
    agent = await service.update_agent(agent_id, payload)
    return ok(agent, version=settings.app_version)


@router.delete("/{agent_id}", response_model=ApiResponse[dict[str, bool | str]])
async def delete_agent(
    agent_id: str,
    settings: Settings = Depends(get_settings),
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[dict[str, bool | str]]:
    """Delete an agent by ID."""
    await service.delete_agent(agent_id)
    return ok({"deleted": True, "id": agent_id}, version=settings.app_version)


@router.post("/{agent_id}/duplicate", response_model=ApiResponse[Agent], status_code=status.HTTP_201_CREATED)
async def duplicate_agent(
    agent_id: str,
    settings: Settings = Depends(get_settings),
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[Agent]:
    """Duplicate an existing agent into a new DRAFT agent."""
    agent = await service.duplicate_agent(agent_id)
    return ok(agent, version=settings.app_version)


@router.post("/{agent_id}/activate", response_model=ApiResponse[Agent])
async def activate_agent(
    agent_id: str,
    settings: Settings = Depends(get_settings),
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[Agent]:
    """Validate and activate an agent."""
    agent = await service.activate_agent(agent_id)
    return ok(agent, version=settings.app_version)


@router.post("/{agent_id}/deactivate", response_model=ApiResponse[Agent])
async def deactivate_agent(
    agent_id: str,
    settings: Settings = Depends(get_settings),
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[Agent]:
    """Deactivate an ACTIVE agent."""
    agent = await service.deactivate_agent(agent_id)
    return ok(agent, version=settings.app_version)
