"""Abstract TTSProvider interface and exceptions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.schemas.speech import SpeechProviderHealth, TTSVoiceInfo


class TTSProviderError(RuntimeError):
    """Base error for Text-to-Speech providers."""


class TTSUnavailableError(TTSProviderError):
    """Raised when the TTS engine is not installed or unavailable."""


class TTSVoiceNotFoundError(TTSProviderError):
    """Raised when the configured voice_id is not installed."""


class TTSValidationError(ValueError):
    """Raised when TTS input text or parameters are invalid."""


class TTSProvider(ABC):
    """Provider-independent Text-to-Speech interface."""

    provider_id: str = "base"

    @abstractmethod
    async def health_check(self) -> SpeechProviderHealth:
        """Return whether the TTS engine is installed and ready."""

    @abstractmethod
    async def synthesize(self, text: str, config: dict[str, Any]) -> bytes:
        """Synthesize text into browser-compatible WAV audio bytes."""

    @abstractmethod
    async def supported_voices(self) -> list[TTSVoiceInfo]:
        """Return actually installed TTS voices (never fabricated)."""
