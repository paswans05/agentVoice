"""Repositories for KnowledgeBases, Documents, and raw upload blobs via StorageProvider."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from pydantic import ValidationError

from app.providers.storage import StorageProvider
from app.schemas.knowledge import KnowledgeBase, KnowledgeDocument

logger = logging.getLogger(__name__)

KB_DIR = "knowledge/bases"
DOCS_DIR = "knowledge/documents"
RAW_DOCS_DIR = "knowledge/raw"


class KnowledgeBaseRepository:
    """Persists KnowledgeBase metadata via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def _path(self, kb_id: str) -> str:
        return f"{KB_DIR}/{kb_id}.json"

    async def save(self, kb: KnowledgeBase) -> KnowledgeBase:
        updated = kb.model_copy(update={"updated_at": datetime.now(timezone.utc)})
        self._storage.write_json(self._path(updated.id), updated.model_dump(mode="json"))
        return updated

    async def get_by_id(self, kb_id: str) -> KnowledgeBase | None:
        raw = self._storage.read_json(self._path(kb_id), default=None)
        if raw is None:
            return None
        return KnowledgeBase.model_validate(raw)

    async def list_all(self) -> list[KnowledgeBase]:
        files = self._storage.list_files(KB_DIR, suffix=".json")
        items: list[KnowledgeBase] = []
        for rel in files:
            try:
                raw = self._storage.read_json(rel, default=None)
                if raw:
                    items.append(KnowledgeBase.model_validate(raw))
            except (OSError, ValidationError) as exc:
                logger.warning("Skipping invalid knowledge base %s: %s", rel, exc)
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items

    async def delete(self, kb_id: str) -> bool:
        return self._storage.delete_file(self._path(kb_id))


class DocumentRepository:
    """Persists KnowledgeDocument metadata and raw text/chunks via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def _path(self, doc_id: str) -> str:
        return f"{DOCS_DIR}/{doc_id}.json"

    def _raw_path(self, doc_id: str) -> str:
        return f"{RAW_DOCS_DIR}/{doc_id}.json"

    async def save(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        updated = doc.model_copy(update={"updated_at": datetime.now(timezone.utc)})
        self._storage.write_json(self._path(updated.id), updated.model_dump(mode="json"))
        return updated

    async def get_by_id(self, doc_id: str) -> KnowledgeDocument | None:
        raw = self._storage.read_json(self._path(doc_id), default=None)
        if raw is None:
            return None
        return KnowledgeDocument.model_validate(raw)

    async def list_by_kb(self, kb_id: str) -> list[KnowledgeDocument]:
        files = self._storage.list_files(DOCS_DIR, suffix=".json")
        items: list[KnowledgeDocument] = []
        for rel in files:
            try:
                raw = self._storage.read_json(rel, default=None)
                if raw:
                    doc = KnowledgeDocument.model_validate(raw)
                    if doc.knowledge_base_id == kb_id:
                        items.append(doc)
            except (OSError, ValidationError) as exc:
                logger.warning("Skipping invalid document %s: %s", rel, exc)
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items

    async def list_all(self) -> list[KnowledgeDocument]:
        files = self._storage.list_files(DOCS_DIR, suffix=".json")
        items: list[KnowledgeDocument] = []
        for rel in files:
            try:
                raw = self._storage.read_json(rel, default=None)
                if raw:
                    items.append(KnowledgeDocument.model_validate(raw))
            except (OSError, ValidationError) as exc:
                logger.warning("Skipping invalid document %s: %s", rel, exc)
        return items

    async def delete(self, doc_id: str) -> bool:
        self._storage.delete_file(self._raw_path(doc_id))
        return self._storage.delete_file(self._path(doc_id))

    async def save_extracted_sections(self, doc_id: str, sections: list[dict]) -> None:
        """Persist extracted text sections so documents can be re-chunked/reprocessed."""
        self._storage.write_json(self._raw_path(doc_id), {"sections": sections})

    async def get_extracted_sections(self, doc_id: str) -> list[dict] | None:
        raw = self._storage.read_json(self._raw_path(doc_id), default=None)
        if not raw or not isinstance(raw, dict):
            return None
        return raw.get("sections")
