"""Local multilingual embeddings using sentence-transformers (Apache-2.0 / MIT)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from app.providers.embeddings.base import (
    EmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingUnavailableError,
)

logger = logging.getLogger(__name__)


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider defaulting to intfloat/multilingual-e5-small."""

    provider_id = "sentence-transformers"

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-small",
        cache_dir: Path | None = None,
        device: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._device = device
        self._model: Any = None
        self._dim: int = 384

    def model_id(self) -> str:
        return self._model_name

    def dimension(self) -> int:
        return self._dim

    @staticmethod
    def _is_installed() -> bool:
        try:
            import sentence_transformers  # noqa: F401

            return True
        except ImportError:
            return False

    async def health_check(self) -> dict[str, object]:
        installed = self._is_installed()
        return {
            "provider": self.provider_id,
            "model_id": self._model_name,
            "available": installed,
            "is_local": True,
            "error": None
            if installed
            else "sentence-transformers is not installed. Install RAG extras: `uv sync --extra rag`.",
        }

    def _get_or_load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
        except ImportError as exc:
            raise EmbeddingUnavailableError(
                "sentence-transformers is not installed. Install with `uv sync --extra rag`."
            ) from exc

        kwargs: dict[str, Any] = {}
        if self._cache_dir is not None:
            kwargs["cache_folder"] = str(self._cache_dir)
        if self._device:
            kwargs["device"] = self._device

        try:
            model = SentenceTransformer(self._model_name, **kwargs)
        except Exception as exc:
            raise EmbeddingUnavailableError(
                f"Failed to load embedding model '{self._model_name}': {exc}"
            ) from exc

        dim = model.get_sentence_embedding_dimension()
        if isinstance(dim, int) and dim > 0:
            self._dim = dim
        self._model = model
        return model

    def _encode_sync(self, texts: list[str], batch_size: int) -> list[list[float]]:
        model = self._get_or_load_model()
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vec.tolist() for vec in vectors]

    async def embed_texts(self, texts: list[str], *, batch_size: int = 16) -> list[list[float]]:
        if not texts:
            return []
        is_e5 = "e5" in self._model_name.lower()
        prepared = [f"passage: {t}" if is_e5 else t for t in texts]
        try:
            return await asyncio.to_thread(self._encode_sync, prepared, batch_size)
        except EmbeddingUnavailableError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError(f"Embedding generation failed: {exc}") from exc

    async def embed_query(self, query: str) -> list[float]:
        is_e5 = "e5" in self._model_name.lower()
        prepared = f"query: {query}" if is_e5 else query
        try:
            res = await asyncio.to_thread(self._encode_sync, [prepared], 1)
            return res[0]
        except EmbeddingUnavailableError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError(f"Query embedding failed: {exc}") from exc
