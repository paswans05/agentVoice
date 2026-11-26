"""Factory for VADProvider instances."""

from __future__ import annotations

from app.providers.vad.base import VADProvider
from app.providers.vad.energy import EnergyVADProvider


class VADProviderFactory:
    """Creates VADProvider instances."""

    @staticmethod
    def create(
        provider_id: str = "energy",
        *,
        threshold: float = 0.015,
        min_speech_ms: int = 250,
        min_silence_ms: int = 700,
        max_utterance_ms: int = 20000,
    ) -> VADProvider:
        normalized = provider_id.strip().lower()
        if normalized in ("energy", "silero"):
            # Uses deterministic offline RMS+hangover VAD; Silero ONNX can be plugged in here
            return EnergyVADProvider(
                threshold=threshold,
                min_speech_ms=min_speech_ms,
                min_silence_ms=min_silence_ms,
                max_utterance_ms=max_utterance_ms,
            )
        raise ValueError(f"Unsupported VAD provider: '{provider_id}'.")
