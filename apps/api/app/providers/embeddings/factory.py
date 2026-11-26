"""Factory for EmbeddingProvider instances."""

from __future__ import annotations

from pathlib import Path

from app.providers.embeddings.base import EmbeddingProvider, EmbeddingProviderError
from app.providers.embeddings.sentence_transformers import SentenceTransformerEmbeddingProvider


class EmbeddingProviderFactory:
    """Creates EmbeddingProvider instances."""

    @staticmethod
    def create(
        provider_id: str = "sentence-transformers",
        *,
        model_name: str = "intfloat/multilingual-e5-small",
        cache_dir: Path | None = None,
    ) -> EmbeddingProvider:
        normalized = provider_id.strip().lower()
        if normalized == "sentence-transformers":
            return SentenceTransformerEmbeddingProvider(model_name=model_name, cache_dir=cache_dir)
        raise EmbeddingProviderError(f"Unsupported embedding provider: '{provider_id}'.")
