"""Persistent local JSON-backed cosine-similarity VectorStoreProvider."""

from __future__ import annotations

import logging
import math
from typing import Any

from app.providers.embeddings.base import EmbeddingDimensionError
from app.providers.storage import StorageProvider
from app.providers.vector_store.base import VectorStoreProvider
from app.schemas.knowledge import DocumentChunk, RetrievalHit

logger = logging.getLogger(__name__)

VECTORS_DIR = "knowledge/vectors"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class LocalVectorStoreProvider(VectorStoreProvider):
    """Stores embeddings and chunk metadata per knowledge base via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def _index_path(self, knowledge_base_id: str) -> str:
        return f"{VECTORS_DIR}/{knowledge_base_id}.json"

    def _load_index(self, knowledge_base_id: str) -> dict[str, Any]:
        raw = self._storage.read_json(self._index_path(knowledge_base_id), default=None)
        if not raw or not isinstance(raw, dict):
            return {"embedding_model": None, "dimension": None, "entries": []}
        return raw

    def _save_index(self, knowledge_base_id: str, index: dict[str, Any]) -> None:
        self._storage.write_json(self._index_path(knowledge_base_id), index)

    async def add_vectors(
        self,
        *,
        knowledge_base_id: str,
        embedding_model: str,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Chunks and vectors length mismatch.")
        if not chunks:
            return

        dim = len(vectors[0])
        index = self._load_index(knowledge_base_id)

        existing_model = index.get("embedding_model")
        existing_dim = index.get("dimension")
        if existing_model and existing_model != embedding_model:
            raise EmbeddingDimensionError(
                f"Index uses embedding model '{existing_model}', cannot mix with '{embedding_model}'. "
                "Reprocess documents to rebuild the index."
            )
        if existing_dim and existing_dim != dim:
            raise EmbeddingDimensionError(
                f"Vector dimension mismatch: index expects {existing_dim}, got {dim}."
            )

        index["embedding_model"] = embedding_model
        index["dimension"] = dim
        entries: list[dict[str, Any]] = index.get("entries", [])

        for chunk, vec in zip(chunks, vectors):
            if len(vec) != dim:
                raise EmbeddingDimensionError(f"Inconsistent vector dimension {len(vec)} != {dim}.")
            entries.append(
                {
                    "chunk": chunk.model_dump(mode="json"),
                    "vector": vec,
                }
            )
        index["entries"] = entries
        self._save_index(knowledge_base_id, index)

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
        index = self._load_index(knowledge_base_id)
        entries: list[dict[str, Any]] = index.get("entries", [])
        if not entries:
            return []

        existing_model = index.get("embedding_model")
        existing_dim = index.get("dimension")
        if existing_model and existing_model != embedding_model:
            raise EmbeddingDimensionError(
                f"Query model '{embedding_model}' does not match index model '{existing_model}'."
            )
        if existing_dim and len(query_vector) != existing_dim:
            raise EmbeddingDimensionError(
                f"Query vector dimension {len(query_vector)} does not match index dimension {existing_dim}."
            )

        scored: list[tuple[float, dict[str, Any]]] = []
        seen_contents: set[str] = set()

        for entry in entries:
            chunk_data = entry["chunk"]
            # Enforce agent-level isolation if agent_id is specified
            if agent_id is not None:
                allowed_agents = chunk_data.get("agent_ids") or []
                if allowed_agents and agent_id not in allowed_agents:
                    continue

            score = _cosine_similarity(query_vector, entry["vector"])
            if score < similarity_threshold:
                continue

            content_key = chunk_data["content"].strip()
            if content_key in seen_contents:
                continue
            seen_contents.add(content_key)
            scored.append((score, chunk_data))

        scored.sort(key=lambda item: item[0], reverse=True)
        hits: list[RetrievalHit] = []
        for score, chunk_data in scored[:top_k]:
            hits.append(
                RetrievalHit(
                    chunk_id=chunk_data["chunk_id"],
                    document_id=chunk_data["document_id"],
                    knowledge_base_id=chunk_data["knowledge_base_id"],
                    filename=chunk_data["source_filename"],
                    page_number=chunk_data.get("page_number"),
                    section_title=chunk_data.get("section_title"),
                    content=chunk_data["content"],
                    score=round(score, 4),
                )
            )
        return hits

    async def delete_by_document(self, *, knowledge_base_id: str, document_id: str) -> int:
        index = self._load_index(knowledge_base_id)
        entries: list[dict[str, Any]] = index.get("entries", [])
        kept = [e for e in entries if e["chunk"]["document_id"] != document_id]
        removed = len(entries) - len(kept)
        if removed > 0:
            index["entries"] = kept
            if not kept:
                index["embedding_model"] = None
                index["dimension"] = None
            self._save_index(knowledge_base_id, index)
        return removed

    async def delete_by_knowledge_base(self, *, knowledge_base_id: str) -> None:
        self._storage.delete_file(self._index_path(knowledge_base_id))

    async def count(self, *, knowledge_base_id: str) -> int:
        index = self._load_index(knowledge_base_id)
        return len(index.get("entries", []))
