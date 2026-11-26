"""Provider interfaces for the agentVoice local voice pipeline."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class LLMProvider(ABC):
    """Abstract interface for local or self-hosted LLM runtimes (e.g., Ollama)."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Return runtime health and availability details."""

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream generated response tokens."""


class STTProvider(ABC):
    """Abstract interface for Speech-to-Text engines (e.g., faster-whisper)."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        """Transcribe an audio buffer to text."""


class TTSProvider(ABC):
    """Abstract interface for Text-to-Speech engines (e.g., Piper)."""

    @abstractmethod
    async def synthesize_stream(
        self,
        text: str,
        voice: str,
        **kwargs: Any,
    ) -> AsyncIterator[bytes]:
        """Stream synthesized PCM/WAV audio chunks."""


class VADProvider(ABC):
    """Abstract interface for Voice Activity Detection (e.g., Silero VAD)."""

    @abstractmethod
    async def is_speech(self, audio_chunk: bytes, sample_rate: int = 16000) -> bool:
        """Return True when speech is detected in the audio frame."""
