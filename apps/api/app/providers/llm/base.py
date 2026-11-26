"""Abstract LLMProvider interface and domain exceptions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from app.schemas.llm import LLMModelInfo, LLMRuntimeHealth


class LLMProviderError(RuntimeError):
    """Base error for LLM provider operations."""


class LLMUnavailableError(LLMProviderError):
    """Raised when the local LLM runtime cannot be reached."""


class LLMModelNotFoundError(LLMProviderError):
    """Raised when a requested model is not installed in the runtime."""


class LLMTimeoutError(LLMProviderError):
    """Raised when a generation or runtime request times out."""


@dataclass(slots=True)
class LLMGenerationConfig:
    """Normalized generation parameters passed to an LLMProvider."""

    model_id: str
    temperature: float = 0.7
    max_tokens: int = 512
    timeout_seconds: float = 120.0


class LLMProvider(ABC):
    """Provider-independent interface for local/self-hosted LLM runtimes."""

    provider_id: str = "base"

    @abstractmethod
    async def health_check(self) -> LLMRuntimeHealth:
        """Check whether the runtime is reachable and return version/status."""

    @abstractmethod
    async def list_models(self) -> list[LLMModelInfo]:
        """List installed models from the runtime."""

    @abstractmethod
    async def has_model(self, model_id: str) -> bool:
        """Return True if model_id is currently installed."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        config: LLMGenerationConfig,
    ) -> str:
        """Generate a complete response for the given chat messages."""

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        config: LLMGenerationConfig,
    ) -> AsyncIterator[str]:
        """Stream response text chunks for the given chat messages."""

    @abstractmethod
    async def pull_model(self, model_id: str) -> AsyncIterator[dict[str, Any]]:
        """Stream download progress events while pulling a model."""

    @abstractmethod
    async def delete_model(self, model_id: str) -> None:
        """Remove an installed model from the runtime."""
