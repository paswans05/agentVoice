"""ConversationRepository backed by StorageProvider."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from pydantic import ValidationError

from app.providers.storage import StorageProvider
from app.schemas.llm import Conversation

logger = logging.getLogger(__name__)

CONVERSATIONS_DIR = "conversations"


class ConversationRepositoryError(RuntimeError):
    """Raised when conversation storage fails."""


class ConversationRepository:
    """Persists Conversation records via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def _path(self, conversation_id: str) -> str:
        return f"{CONVERSATIONS_DIR}/{conversation_id}.json"

    async def save(self, conversation: Conversation) -> Conversation:
        updated = conversation.model_copy(
            update={"updated_at": datetime.now(timezone.utc)}
        )
        try:
            self._storage.write_json(
                self._path(updated.id),
                updated.model_dump(mode="json"),
            )
        except OSError as exc:
            raise ConversationRepositoryError(
                f"Failed to persist conversation '{updated.id}': {exc}"
            ) from exc
        return updated

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        try:
            raw = self._storage.read_json(self._path(conversation_id), default=None)
        except OSError as exc:
            raise ConversationRepositoryError(
                f"Failed to read conversation '{conversation_id}': {exc}"
            ) from exc
        if raw is None:
            return None
        try:
            return Conversation.model_validate(raw)
        except ValidationError as exc:
            raise ConversationRepositoryError(
                f"Corrupted conversation '{conversation_id}': {exc}"
            ) from exc

    async def list_by_agent(self, agent_id: str) -> list[Conversation]:
        try:
            files = self._storage.list_files(CONVERSATIONS_DIR, suffix=".json")
        except OSError as exc:
            raise ConversationRepositoryError(f"Failed to list conversations: {exc}") from exc

        items: list[Conversation] = []
        for rel_path in files:
            try:
                raw = self._storage.read_json(rel_path, default=None)
                if raw is None:
                    continue
                conv = Conversation.model_validate(raw)
                if conv.agent_id == agent_id:
                    items.append(conv)
            except (OSError, ValidationError) as exc:
                logger.warning("Skipping unreadable conversation %s: %s", rel_path, exc)
        items.sort(key=lambda c: c.updated_at, reverse=True)
        return items

    async def delete(self, conversation_id: str) -> bool:
        try:
            return self._storage.delete_file(self._path(conversation_id))
        except OSError as exc:
            raise ConversationRepositoryError(
                f"Failed to delete conversation '{conversation_id}': {exc}"
            ) from exc
