"""Retrieval, ContextBuilder, RAGSettings, and RAGService."""

from __future__ import annotations

import logging
import time

from app.providers.embeddings import EmbeddingProvider
from app.providers.storage import StorageProvider
from app.providers.vector_store import VectorStoreProvider
from app.repositories.knowledge_repository import KnowledgeBaseRepository
from app.schemas.agent import Agent
from app.schemas.knowledge import (
    RAGSettings,
    RetrievalHit,
    RetrievalTestResult,
    SourceCitation,
)

logger = logging.getLogger(__name__)

RAG_SETTINGS_PATH = "config/rag_settings.json"


class RAGSettingsService:
    """Persists global RAG defaults via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def get_settings(self) -> RAGSettings:
        raw = self._storage.read_json(RAG_SETTINGS_PATH, default=None)
        if not raw:
            return RAGSettings()
        return RAGSettings.model_validate(raw)

    def update_settings(self, settings: RAGSettings) -> RAGSettings:
        self._storage.write_json(RAG_SETTINGS_PATH, settings.model_dump(mode="json"))
        return settings


class RetrievalService:
    """Performs semantic retrieval against a knowledge base vector index."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStoreProvider,
    ) -> None:
        self._embedder = embedding_provider
        self._vectors = vector_store

    async def search(
        self,
        *,
        knowledge_base_id: str,
        query: str,
        agent_id: str | None = None,
        top_k: int = 5,
        similarity_threshold: float = 0.25,
    ) -> tuple[list[RetrievalHit], int]:
        start = time.monotonic()
        query_vec = await self._embedder.embed_query(query)
        hits = await self._vectors.search(
            knowledge_base_id=knowledge_base_id,
            query_vector=query_vec,
            embedding_model=self._embedder.model_id(),
            agent_id=agent_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return hits, elapsed_ms


class ContextBuilderService:
    """Builds grounded prompt context and source citations from retrieved chunks."""

    @staticmethod
    def build_context(
        hits: list[RetrievalHit],
        *,
        max_context_tokens: int = 2000,
    ) -> tuple[str, list[SourceCitation]]:
        if not hits:
            return "", []

        blocks: list[str] = []
        citations: list[SourceCitation] = []
        used_words = 0

        for idx, hit in enumerate(hits, start=1):
            words = hit.content.split()
            if used_words + len(words) > max_context_tokens and blocks:
                break
            used_words += len(words)
            page_info = f", page {hit.page_number}" if hit.page_number else ""
            blocks.append(
                f"[Excerpt {idx} | source={hit.filename}{page_info}]\n{hit.content}"
            )
            citations.append(
                SourceCitation(
                    document_id=hit.document_id,
                    filename=hit.filename,
                    page_number=hit.page_number,
                    chunk_id=hit.chunk_id,
                    score=hit.score,
                )
            )

        context_text = "\n\n---\n\n".join(blocks)
        return context_text, citations


class RAGService:
    """Coordinates agent-scoped retrieval and grounding context for ConversationService."""

    def __init__(
        self,
        kb_repo: KnowledgeBaseRepository,
        retrieval: RetrievalService,
    ) -> None:
        self._kb_repo = kb_repo
        self._retrieval = retrieval

    async def retrieve_for_agent(
        self,
        agent: Agent,
        query: str,
    ) -> tuple[str | None, list[SourceCitation], bool]:
        """Return (context_text, citations, grounded) for an agent if KB is enabled."""
        kb_cfg = agent.knowledge_base
        if not kb_cfg.enabled or not kb_cfg.knowledge_base_id:
            return None, [], False

        kb = await self._kb_repo.get_by_id(kb_cfg.knowledge_base_id)
        if kb is None or not kb.enabled:
            return None, [], False

        # Enforce agent-level access isolation: agent must be assigned to this KB
        if kb.agent_ids and agent.id not in kb.agent_ids:
            logger.warning(
                "Agent %s attempted to access unassigned knowledge base %s",
                agent.id,
                kb.id,
            )
            return None, [], False

        hits, elapsed_ms = await self._retrieval.search(
            knowledge_base_id=kb.id,
            query=query,
            agent_id=agent.id if kb.agent_ids else None,
            top_k=kb_cfg.top_k,
            similarity_threshold=kb_cfg.similarity_threshold,
        )
        logger.info(
            "RAG retrieval (agent=%s, kb=%s, hits=%d, latency_ms=%d)",
            agent.id,
            kb.id,
            len(hits),
            elapsed_ms,
        )
        if not hits:
            return "", [], False

        context_text, citations = ContextBuilderService.build_context(
            hits,
            max_context_tokens=kb_cfg.max_context_tokens,
        )
        return context_text, citations, bool(citations)

    async def test_kb_search(
        self,
        *,
        knowledge_base_id: str,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.25,
        agent_id: str | None = None,
    ) -> RetrievalTestResult:
        hits, elapsed_ms = await self._retrieval.search(
            knowledge_base_id=knowledge_base_id,
            query=query,
            agent_id=agent_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        return RetrievalTestResult(
            query=query,
            hits=hits,
            grounded=len(hits) > 0,
            retrieval_ms=elapsed_ms,
        )
