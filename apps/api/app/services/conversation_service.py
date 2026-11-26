"""ConversationService orchestrating agent validation, model resolution, and LLM chat."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
import logging
import time
import uuid

from app.providers.llm import (
    LLMGenerationConfig,
    LLMModelNotFoundError,
    LLMProvider,
)
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.agent import Agent, AgentStatus
from app.schemas.llm import (
    ChatMessage,
    Conversation,
    ConversationCreate,
    SendMessageRequest,
    SendMessageResult,
)
from app.services.agent_service import AgentLifecycleError, AgentService
from app.services.model_manager import ModelManager
from app.services.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class ConversationNotFoundError(LookupError):
    """Raised when a conversation ID is not found."""


class ConversationService:
    """Manages multi-turn local LLM conversations for configured agents."""

    def __init__(
        self,
        agent_service: AgentService,
        model_manager: ModelManager,
        llm_provider: LLMProvider,
        conversation_repo: ConversationRepository,
    ) -> None:
        self._agents = agent_service
        self._models = model_manager
        self._llm = llm_provider
        self._repo = conversation_repo

    async def _resolve_agent_and_model(
        self,
        agent_id: str,
        *,
        override_model_id: str | None = None,
        allow_draft_preview: bool = True,
    ) -> tuple[Agent, str]:
        agent = await self._agents.get_agent(agent_id)
        if agent.status == AgentStatus.INACTIVE:
            raise AgentLifecycleError(
                f"Agent '{agent.name}' is INACTIVE. Activate it before starting a conversation."
            )
        if agent.status == AgentStatus.DRAFT and not allow_draft_preview:
            raise AgentLifecycleError(
                f"Agent '{agent.name}' is in DRAFT status. Activate it or enable preview mode."
            )

        model_id = (
            (override_model_id or "").strip()
            or agent.model.model_id.strip()
            or (self._models.get_default_model_id() or "").strip()
        )
        if not model_id:
            raise LLMModelNotFoundError(
                "No model is assigned to this agent and no default model is selected. "
                "Open Model Manager to download or select a local model."
            )

        installed = await self._models.is_model_installed(model_id)
        if not installed:
            raise LLMModelNotFoundError(
                f"Selected model '{model_id}' is not installed. "
                "Open Model Manager to download or select another model."
            )
        return agent, model_id

    async def list_conversations(self, agent_id: str) -> list[Conversation]:
        await self._agents.get_agent(agent_id)
        return await self._repo.list_by_agent(agent_id)

    async def create_conversation(
        self,
        agent_id: str,
        payload: ConversationCreate,
        *,
        allow_draft_preview: bool = True,
    ) -> Conversation:
        agent, model_id = await self._resolve_agent_and_model(
            agent_id,
            override_model_id=payload.model_id,
            allow_draft_preview=allow_draft_preview,
        )
        now = datetime.now(timezone.utc)
        conv = Conversation(
            id=f"conv_{uuid.uuid4().hex[:12]}",
            agent_id=agent.id,
            model_id=model_id,
            title=payload.title.strip() or "New Conversation",
            messages=[],
            created_at=now,
            updated_at=now,
        )
        saved = await self._repo.save(conv)
        logger.info("Created conversation %s for agent %s using model %s", saved.id, agent.id, model_id)
        return saved

    async def get_conversation(self, conversation_id: str) -> Conversation:
        conv = await self._repo.get_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundError(f"Conversation '{conversation_id}' was not found.")
        return conv

    async def delete_conversation(self, conversation_id: str) -> None:
        deleted = await self._repo.delete(conversation_id)
        if not deleted:
            raise ConversationNotFoundError(f"Conversation '{conversation_id}' was not found.")

    async def send_message(
        self,
        conversation_id: str,
        payload: SendMessageRequest,
    ) -> SendMessageResult:
        conv = await self.get_conversation(conversation_id)
        agent, model_id = await self._resolve_agent_and_model(
            conv.agent_id,
            override_model_id=conv.model_id,
            allow_draft_preview=payload.allow_draft_preview,
        )

        user_msg = ChatMessage(role="user", content=payload.content.strip())
        prompt_messages = PromptBuilder.build_messages(agent, conv.messages, user_msg.content)

        # Persist user message before generation
        conv.messages.append(user_msg)
        conv = await self._repo.save(conv)

        gen_config = LLMGenerationConfig(
            model_id=model_id,
            temperature=agent.model.temperature,
            max_tokens=agent.model.max_tokens,
        )
        start = time.monotonic()
        logger.info("Generation started (conv=%s, agent=%s, model=%s)", conv.id, agent.id, model_id)
        reply_text = await self._llm.generate(prompt_messages, gen_config)
        duration_ms = int((time.monotonic() - start) * 1000)

        assistant_msg = ChatMessage(
            role="assistant",
            content=reply_text.strip(),
            model_id=model_id,
            duration_ms=duration_ms,
        )
        conv.messages.append(assistant_msg)
        conv = await self._repo.save(conv)
        logger.info(
            "Generation completed (conv=%s, model=%s, duration_ms=%d)",
            conv.id,
            model_id,
            duration_ms,
        )
        return SendMessageResult(conversation=conv, reply=assistant_msg)

    async def stream_message(
        self,
        conversation_id: str,
        payload: SendMessageRequest,
    ) -> AsyncIterator[dict[str, object]]:
        """Yield structured streaming events and persist assistant reply only on completion."""
        conv = await self.get_conversation(conversation_id)
        agent, model_id = await self._resolve_agent_and_model(
            conv.agent_id,
            override_model_id=conv.model_id,
            allow_draft_preview=payload.allow_draft_preview,
        )

        user_msg = ChatMessage(role="user", content=payload.content.strip())
        prompt_messages = PromptBuilder.build_messages(agent, conv.messages, user_msg.content)

        # Persist user message immediately
        conv.messages.append(user_msg)
        conv = await self._repo.save(conv)

        gen_config = LLMGenerationConfig(
            model_id=model_id,
            temperature=agent.model.temperature,
            max_tokens=agent.model.max_tokens,
        )

        yield {"event": "meta", "conversation_id": conv.id, "model_id": model_id}

        start = time.monotonic()
        chunks: list[str] = []
        completed = False
        logger.info("Streaming generation started (conv=%s, model=%s)", conv.id, model_id)

        try:
            async for delta in self._llm.stream(prompt_messages, gen_config):
                chunks.append(delta)
                yield {"event": "delta", "content": delta}
            completed = True
        except Exception as exc:
            logger.warning("Streaming generation failed (conv=%s): %s", conv.id, exc)
            yield {"event": "error", "message": str(exc)}
            return
        finally:
            if not completed:
                logger.info("Streaming generation interrupted before completion (conv=%s)", conv.id)

        full_text = "".join(chunks).strip()
        duration_ms = int((time.monotonic() - start) * 1000)

        if full_text:
            assistant_msg = ChatMessage(
                role="assistant",
                content=full_text,
                model_id=model_id,
                duration_ms=duration_ms,
            )
            conv.messages.append(assistant_msg)
            await self._repo.save(conv)
            logger.info(
                "Streaming generation completed (conv=%s, model=%s, duration_ms=%d)",
                conv.id,
                model_id,
                duration_ms,
            )
            yield {
                "event": "done",
                "conversation_id": conv.id,
                "model_id": model_id,
                "duration_ms": duration_ms,
                "message": assistant_msg.model_dump(mode="json"),
            }
        else:
            yield {"event": "error", "message": "Model returned an empty response."}
