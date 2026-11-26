"""AgentService containing all business logic and lifecycle rules."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from app.agents.templates import AGENT_TEMPLATES, get_template_by_id
from app.repositories.agent_repository import AgentRepository
from app.schemas.agent import (
    Agent,
    AgentCreate,
    AgentStatus,
    AgentTemplate,
    AgentType,
    AgentUpdate,
)


class AgentNotFoundError(LookupError):
    """Raised when a requested agent does not exist."""


class AgentLifecycleError(ValueError):
    """Raised when an invalid lifecycle transition or activation check fails."""


class AgentConflictError(RuntimeError):
    """Raised on genuine resource conflict (e.g., duplicate ID)."""


class AgentService:
    """Business logic for agent creation, updates, lifecycle, and duplication."""

    def __init__(self, repository: AgentRepository) -> None:
        self._repo = repository

    @staticmethod
    def _generate_id() -> str:
        return f"agent_{uuid.uuid4().hex[:12]}"

    def list_templates(self) -> list[AgentTemplate]:
        """Return all built-in starter templates."""
        return AGENT_TEMPLATES

    async def list_agents(
        self,
        *,
        status: AgentStatus | None = None,
        agent_type: AgentType | None = None,
        search: str | None = None,
    ) -> list[Agent]:
        """List agents with optional filters."""
        return await self._repo.list(status=status, agent_type=agent_type, search=search)

    async def get_agent(self, agent_id: str) -> Agent:
        """Fetch an agent or raise AgentNotFoundError."""
        agent = await self._repo.get_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent '{agent_id}' was not found.")
        return agent

    async def create_agent(self, payload: AgentCreate) -> Agent:
        """Create a new agent in DRAFT status, optionally seeded from a template."""
        now = datetime.now(timezone.utc)
        personality = payload.personality
        instructions = payload.instructions
        language = payload.language
        voice = payload.voice
        model = payload.model
        avatar = payload.avatar
        agent_type = payload.type

        if payload.template_id:
            template = get_template_by_id(payload.template_id)
            if template is None:
                raise AgentLifecycleError(f"Unknown template_id '{payload.template_id}'.")
            if not instructions.system_prompt and not instructions.greeting:
                instructions = template.instructions.model_copy(deep=True)
            if not payload.description:
                description = template.description
            else:
                description = payload.description
            avatar = payload.avatar or template.avatar
        else:
            description = payload.description

        # Ensure primary_language is included in supported_languages
        supported = list(language.supported_languages)
        if language.primary_language not in supported:
            supported.insert(0, language.primary_language)
            language = language.model_copy(update={"supported_languages": supported})

        agent = Agent(
            id=self._generate_id(),
            name=payload.name.strip(),
            description=description.strip(),
            avatar=avatar,
            type=agent_type,
            status=AgentStatus.DRAFT,
            personality=personality,
            instructions=instructions,
            language=language,
            voice=voice,
            model=model,
            created_at=now,
            updated_at=now,
            version=1,
        )
        try:
            return await self._repo.create(agent)
        except FileExistsError as exc:
            raise AgentConflictError(str(exc)) from exc

    async def update_agent(self, agent_id: str, payload: AgentUpdate) -> Agent:
        """Update an existing agent's configuration."""
        existing = await self.get_agent(agent_id)

        supported = list(payload.language.supported_languages)
        language = payload.language
        if language.primary_language not in supported:
            supported.insert(0, language.primary_language)
            language = language.model_copy(update={"supported_languages": supported})

        candidate = existing.model_copy(
            update={
                "name": payload.name.strip(),
                "description": payload.description.strip(),
                "avatar": payload.avatar,
                "type": payload.type,
                "personality": payload.personality,
                "instructions": payload.instructions,
                "language": language,
                "voice": payload.voice,
                "model": payload.model,
            }
        )

        # If currently ACTIVE, ensure updated config still satisfies activation rules
        if existing.status == AgentStatus.ACTIVE:
            self._validate_for_activation(candidate)

        updated = await self._repo.update(agent_id, candidate)
        if updated is None:
            raise AgentNotFoundError(f"Agent '{agent_id}' was not found.")
        return updated

    async def delete_agent(self, agent_id: str) -> None:
        """Delete an agent by ID or raise AgentNotFoundError."""
        deleted = await self._repo.delete(agent_id)
        if not deleted:
            raise AgentNotFoundError(f"Agent '{agent_id}' was not found.")

    async def duplicate_agent(self, agent_id: str) -> Agent:
        """Duplicate an agent into a new DRAFT agent with a fresh ID and timestamps."""
        source = await self.get_agent(agent_id)
        now = datetime.now(timezone.utc)

        base_name = source.name.strip()
        copy_name = f"{base_name} (Copy)"
        if len(copy_name) > 80:
            copy_name = f"{base_name[:73]} (Copy)"

        duplicated = source.model_copy(
            deep=True,
            update={
                "id": self._generate_id(),
                "name": copy_name,
                "status": AgentStatus.DRAFT,
                "created_at": now,
                "updated_at": now,
                "version": 1,
            },
        )
        try:
            return await self._repo.create(duplicated)
        except FileExistsError as exc:
            raise AgentConflictError(str(exc)) from exc

    @staticmethod
    def _validate_for_activation(agent: Agent) -> None:
        """Validate that an agent has the minimum required configuration to become ACTIVE."""
        errors: list[str] = []
        if len(agent.name.strip()) < 2:
            errors.append("Agent name must be at least 2 characters.")
        if not agent.instructions.system_prompt.strip():
            errors.append("System prompt is required before activating an agent.")
        if not agent.language.primary_language:
            errors.append("Primary language must be configured.")
        if not agent.voice.provider.strip() or not agent.voice.voice_id.strip():
            errors.append("Voice provider and voice_id must be configured.")
        if errors:
            raise AgentLifecycleError(" ".join(errors))

    async def activate_agent(self, agent_id: str) -> Agent:
        """Transition a valid DRAFT or INACTIVE agent to ACTIVE."""
        agent = await self.get_agent(agent_id)
        if agent.status == AgentStatus.ACTIVE:
            return agent
        self._validate_for_activation(agent)
        updated = await self._repo.update(
            agent_id,
            agent.model_copy(update={"status": AgentStatus.ACTIVE}),
        )
        if updated is None:
            raise AgentNotFoundError(f"Agent '{agent_id}' was not found.")
        return updated

    async def deactivate_agent(self, agent_id: str) -> Agent:
        """Transition an ACTIVE agent to INACTIVE."""
        agent = await self.get_agent(agent_id)
        if agent.status == AgentStatus.DRAFT:
            raise AgentLifecycleError("Cannot deactivate a DRAFT agent; edit or delete it instead.")
        if agent.status == AgentStatus.INACTIVE:
            return agent
        updated = await self._repo.update(
            agent_id,
            agent.model_copy(update={"status": AgentStatus.INACTIVE}),
        )
        if updated is None:
            raise AgentNotFoundError(f"Agent '{agent_id}' was not found.")
        return updated
