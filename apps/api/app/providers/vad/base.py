"""Abstract VADProvider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.speech import SpeechProviderHealth, VADResult


class VADProvider(ABC):
    """Voice Activity Detection provider interface."""

    provider_id: str = "base"

    @abstractmethod
    async def health_check(self) -> SpeechProviderHealth:
        """Return VAD readiness status."""

    @abstractmethod
    async def detect_speech(self, audio: bytes, sample_rate: int = 16000) -> VADResult:
        """Analyze a PCM s16le audio chunk and return speech/silence state."""

    @abstractmethod
    def reset(self) -> None:
        """Reset internal utterance state."""
