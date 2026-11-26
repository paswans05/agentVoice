"""Agent conversation and streaming chat endpoints."""

from collections.abc import AsyncIterator
import json

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from app.api.v1.agents import get_agent_service
from app.api.v1.health import get_storage
from app.api.v1.knowledge import get_rag_service
from app.api.v1.llm import get_llm_provider
from app.api.v1.models import get_model_manager
from app.core.config import Settings, get_settings
from app.providers.llm import LLMProvider
from app.providers.storage import StorageProvider
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.llm import (
    Conversation,
    ConversationCreate,
    SendMessageRequest,
    SendMessageResult,
)
from app.schemas.response import ApiResponse, ok
from app.services.agent_service import AgentService
from app.services.conversation_service import ConversationService
from app.services.model_manager import ModelManager
from app.services.rag_service import RAGService

router = APIRouter(tags=["conversations"])


def get_conversation_service(
    agent_service: AgentService = Depends(get_agent_service),
    model_manager: ModelManager = Depends(get_model_manager),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    storage: StorageProvider = Depends(get_storage),
    rag_service: RAGService = Depends(get_rag_service),
) -> ConversationService:
    """Dependency providing ConversationService."""
    return ConversationService(
        agent_service=agent_service,
        model_manager=model_manager,
        llm_provider=llm_provider,
        conversation_repo=ConversationRepository(storage),
        rag_service=rag_service,
    )


@router.get("/agents/{agent_id}/conversations", response_model=ApiResponse[list[Conversation]])
async def list_agent_conversations(
    agent_id: str,
    settings: Settings = Depends(get_settings),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[list[Conversation]]:
    """List saved conversations for an agent."""
    items = await service.list_conversations(agent_id)
    return ok(items, version=settings.app_version)


@router.post(
    "/agents/{agent_id}/conversations",
    response_model=ApiResponse[Conversation],
    status_code=status.HTTP_201_CREATED,
)
async def create_agent_conversation(
    agent_id: str,
    payload: ConversationCreate,
    settings: Settings = Depends(get_settings),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[Conversation]:
    """Create a new conversation for an agent."""
    conv = await service.create_conversation(agent_id, payload)
    return ok(conv, version=settings.app_version)


@router.get("/conversations/{conversation_id}", response_model=ApiResponse[Conversation])
async def get_conversation(
    conversation_id: str,
    settings: Settings = Depends(get_settings),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[Conversation]:
    """Retrieve a conversation by ID."""
    conv = await service.get_conversation(conversation_id)
    return ok(conv, version=settings.app_version)


@router.delete("/conversations/{conversation_id}", response_model=ApiResponse[dict[str, str | bool]])
async def delete_conversation(
    conversation_id: str,
    settings: Settings = Depends(get_settings),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[dict[str, str | bool]]:
    """Delete a conversation by ID."""
    await service.delete_conversation(conversation_id)
    return ok({"deleted": True, "id": conversation_id}, version=settings.app_version)


@router.post("/conversations/{conversation_id}/messages", response_model=ApiResponse[SendMessageResult])
async def send_conversation_message(
    conversation_id: str,
    payload: SendMessageRequest,
    settings: Settings = Depends(get_settings),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[SendMessageResult]:
    """Send a user message and receive a complete local LLM reply."""
    result = await service.send_message(conversation_id, payload)
    return ok(result, version=settings.app_version)


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_conversation_message(
    conversation_id: str,
    payload: SendMessageRequest,
    request: Request,
    service: ConversationService = Depends(get_conversation_service),
) -> StreamingResponse:
    """Send a user message and stream assistant tokens via Server-Sent Events (SSE)."""

    async def event_generator() -> AsyncIterator[str]:
        async for event in service.stream_message(conversation_id, payload):
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
