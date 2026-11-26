"""Factory for STTProvider instances."""

from __future__ import annotations

from pathlib import Path

from app.providers.stt.base import STTProvider, STTProviderError
from app.providers.stt.faster_whisper import FasterWhisperSTTProvider


class STTProviderFactory:
    """Creates STTProvider instances without coupling services to a specific engine."""

    @staticmethod
    def create(
        provider_id: str = "faster-whisper",
        *,
        model_size: str = "small",
        download_root: Path | None = None,
    ) -> STTProvider:
        normalized = provider_id.strip().lower()
        if normalized == "faster-whisper":
            return FasterWhisperSTTProvider(model_size=model_size, download_root=download_root)
        raise STTProviderError(f"Unsupported STT provider: '{provider_id}'.")
