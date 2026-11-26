"""Abstract VectorStoreProvider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.knowledge import DocumentChunk, RetrievalHit


class VectorStoreProvider(ABC):
    """Provider-independent local/remote vector index interface."""

    @abstractmethod
    async def add_vectors(
        self,
        *,
        knowledge_base_id: str,
        embedding_model: str,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        """Add chunk vectors to the index."""

    @abstractmethod
    async def search(
        self,
        *,
        knowledge_base_id: str,
        query_vector: list[float],
        embedding_model: str,
        agent_id: str | None = None,
        top_k: int = 5,
        similarity_threshold: float = 0.25,
    ) -> list[RetrievalHit]:
        """Search vectors with strict knowledge_base_id and optional agent_id isolation."""

    @abstractmethod
    async def delete_by_document(self, *, knowledge_base_id: str, document_id: str) -> int:
        """Remove all vectors belonging to document_id. Returns count removed."""

    @abstractmethod
    async def delete_by_knowledge_base(self, *, knowledge_base_id: str) -> None:
        """Delete the entire vector index for knowledge_base_id."""

    @abstractmethod
    async def count(self, *, knowledge_base_id: str) -> int:
        """Return total indexed vectors in knowledge_base_id."""
