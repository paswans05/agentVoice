"""AgentRepository backed by StorageProvider (no direct filesystem access)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from pydantic import ValidationError

from app.providers.storage import StorageProvider
from app.schemas.agent import Agent, AgentStatus, AgentType

logger = logging.getLogger(__name__)

AGENTS_DIR = "agents"


class AgentRepositoryError(RuntimeError):
    """Raised when reading or writing agent data fails."""


class AgentRepository:
    """Persistence repository for Agent configurations via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def _agent_path(self, agent_id: str) -> str:
        return f"{AGENTS_DIR}/{agent_id}.json"

    async def create(self, agent: Agent) -> Agent:
        """Persist a new agent. Raises FileExistsError if ID already exists."""
        if await self.exists(agent.id):
            raise FileExistsError(f"Agent '{agent.id}' already exists.")
        try:
            self._storage.write_json(self._agent_path(agent.id), agent.model_dump(mode="json"))
        except OSError as exc:
            raise AgentRepositoryError(f"Failed to persist agent '{agent.id}': {exc}") from exc
        return agent

    async def get_by_id(self, agent_id: str) -> Agent | None:
        """Retrieve and validate an agent by ID, or return None if missing."""
        try:
            raw = self._storage.read_json(self._agent_path(agent_id), default=None)
        except OSError as exc:
            raise AgentRepositoryError(f"Failed to read agent '{agent_id}': {exc}") from exc
        if raw is None:
            return None
        try:
            return Agent.model_validate(raw)
        except ValidationError as exc:
            raise AgentRepositoryError(f"Corrupted agent data for '{agent_id}': {exc}") from exc

    async def list(
        self,
        status: AgentStatus | None = None,
        agent_type: AgentType | None = None,
        search: str | None = None,
    ) -> list[Agent]:
        """List agents with optional status, type, and text search filters."""
        try:
            files = self._storage.list_files(AGENTS_DIR, suffix=".json")
        except OSError as exc:
            raise AgentRepositoryError(f"Failed to list agents: {exc}") from exc

        agents: list[Agent] = []
        search_lower = search.strip().lower() if search else None

        for rel_path in files:
            try:
                raw = self._storage.read_json(rel_path, default=None)
                if raw is None:
                    continue
                agent = Agent.model_validate(raw)
            except (OSError, ValidationError) as exc:
                logger.warning("Skipping unreadable/invalid agent file %s: %s", rel_path, exc)
                continue

            if status is not None and agent.status != status:
                continue
            if agent_type is not None and agent.type != agent_type:
                continue
            if search_lower:
                haystack = f"{agent.name} {agent.description} {agent.type.value}".lower()
                if search_lower not in haystack:
                    continue
            agents.append(agent)

        agents.sort(key=lambda item: item.updated_at, reverse=True)
        return agents

    async def update(self, agent_id: str, agent: Agent) -> Agent | None:
        """Update an existing agent, refreshing updated_at and incrementing version."""
        existing = await self.get_by_id(agent_id)
        if existing is None:
            return None

        updated = agent.model_copy(
            update={
                "id": agent_id,
                "created_at": existing.created_at,
                "updated_at": datetime.now(timezone.utc),
                "version": existing.version + 1,
            }
        )
        try:
            self._storage.write_json(self._agent_path(agent_id), updated.model_dump(mode="json"))
        except OSError as exc:
            raise AgentRepositoryError(f"Failed to update agent '{agent_id}': {exc}") from exc
        return updated

    async def delete(self, agent_id: str) -> bool:
        """Delete an agent by ID. Returns True if deleted, False if not found."""
        try:
            return self._storage.delete_file(self._agent_path(agent_id))
        except OSError as exc:
            raise AgentRepositoryError(f"Failed to delete agent '{agent_id}': {exc}") from exc

    async def exists(self, agent_id: str) -> bool:
        """Return True if an agent with agent_id exists."""
        return self._storage.read_json(self._agent_path(agent_id), default=None) is not None
