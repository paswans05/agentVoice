"""Factory for TTSProvider instances."""

from __future__ import annotations

from pathlib import Path

from app.providers.tts.base import TTSProvider, TTSProviderError
from app.providers.tts.piper import PiperTTSProvider


class TTSProviderFactory:
    """Creates TTSProvider instances without coupling services to a specific engine."""

    @staticmethod
    def create(provider_id: str = "piper", *, models_dir: Path) -> TTSProvider:
        normalized = provider_id.strip().lower()
        if normalized == "piper":
            return PiperTTSProvider(models_dir=models_dir)
        raise TTSProviderError(f"Unsupported TTS provider: '{provider_id}'.")
