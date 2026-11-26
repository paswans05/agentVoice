"""Factory for resolving configured LLMProvider instances."""

from __future__ import annotations

from app.core.config import Settings
from app.providers.llm.base import LLMProvider, LLMProviderError
from app.providers.llm.ollama import OllamaProvider


class LLMProviderFactory:
    """Creates LLMProvider instances without coupling services to a specific runtime."""

    @staticmethod
    def create(provider_id: str, settings: Settings) -> LLMProvider:
        normalized = provider_id.strip().lower()
        if normalized == "ollama":
            return OllamaProvider(base_url=settings.ollama_base_url)
        raise LLMProviderError(f"Unsupported LLM provider: '{provider_id}'.")
