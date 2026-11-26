"""Abstract EmbeddingProvider interface and exceptions."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProviderError(RuntimeError):
    """Base error for embedding providers."""


class EmbeddingUnavailableError(EmbeddingProviderError):
    """Raised when the embedding library or model cannot be loaded."""


class EmbeddingDimensionError(ValueError):
    """Raised when vector dimensions do not match the existing index."""


class EmbeddingProvider(ABC):
    """Provider-independent local text embedding interface."""

    provider_id: str = "base"

    @abstractmethod
    def model_id(self) -> str:
        """Return the configured embedding model identifier."""

    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimension produced by this model."""

    @abstractmethod
    async def health_check(self) -> dict[str, object]:
        """Return availability and model metadata."""

    @abstractmethod
    async def embed_texts(self, texts: list[str], *, batch_size: int = 16) -> list[list[float]]:
        """Embed a batch of document passages."""

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Embed a single search query."""
