"""Abstract STTProvider interface and exceptions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.schemas.speech import SpeechProviderHealth, STTResult


class STTProviderError(RuntimeError):
    """Base error for Speech-to-Text providers."""


class STTUnavailableError(STTProviderError):
    """Raised when the STT engine or model is not installed/available."""


class STTAudioError(ValueError):
    """Raised when input audio is empty, malformed, or unsupported."""


class STTProvider(ABC):
    """Provider-independent Speech-to-Text interface."""

    provider_id: str = "base"

    @abstractmethod
    async def health_check(self) -> SpeechProviderHealth:
        """Return whether the STT engine is installed and ready."""

    @abstractmethod
    async def transcribe(self, audio: bytes, config: dict[str, Any]) -> STTResult:
        """Transcribe PCM/WAV audio bytes into normalized STTResult."""

    @abstractmethod
    async def supported_languages(self) -> list[str]:
        """Return language codes supported by this STT provider."""
