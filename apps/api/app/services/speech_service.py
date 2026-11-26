"""Speech services (STTService, TTSService, VADService, AudioSettingsService)."""

from __future__ import annotations

from typing import Any

from app.providers.stt import STTProvider
from app.providers.tts import TTSProvider
from app.providers.vad import VADProvider
from app.providers.storage import StorageProvider
from app.schemas.speech import (
    AudioSettings,
    SpeechRuntimeHealth,
    STTModelInfo,
    STTResult,
    TTSVoiceInfo,
    VADResult,
)

AUDIO_SETTINGS_PATH = "config/audio_settings.json"

CURATED_STT_MODELS: list[STTModelInfo] = [
    STTModelInfo(
        id="tiny",
        name="Whisper Tiny",
        provider="faster-whisper",
        languages=["en", "hi"],
        approximate_size="~75 MB",
        min_ram_gb=2,
        license="MIT",
    ),
    STTModelInfo(
        id="base",
        name="Whisper Base",
        provider="faster-whisper",
        languages=["en", "hi"],
        approximate_size="~145 MB",
        min_ram_gb=2,
        license="MIT",
    ),
    STTModelInfo(
        id="small",
        name="Whisper Small",
        provider="faster-whisper",
        languages=["hi", "en"],
        approximate_size="~480 MB",
        min_ram_gb=4,
        license="MIT",
    ),
    STTModelInfo(
        id="medium",
        name="Whisper Medium",
        provider="faster-whisper",
        languages=["hi", "en"],
        approximate_size="~1.5 GB",
        min_ram_gb=8,
        license="MIT",
    ),
    STTModelInfo(
        id="large-v3",
        name="Whisper Large v3",
        provider="faster-whisper",
        languages=["hi", "en"],
        approximate_size="~3.0 GB",
        min_ram_gb=12,
        license="MIT",
    ),
]


class AudioSettingsService:
    """Persists user-level audio defaults via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def get_settings(self) -> AudioSettings:
        raw = self._storage.read_json(AUDIO_SETTINGS_PATH, default=None)
        if not raw:
            return AudioSettings()
        return AudioSettings.model_validate(raw)

    def update_settings(self, settings: AudioSettings) -> AudioSettings:
        self._storage.write_json(AUDIO_SETTINGS_PATH, settings.model_dump(mode="json"))
        return settings


class STTService:
    """Orchestrates Speech-to-Text transcription."""

    def __init__(self, provider: STTProvider) -> None:
        self._provider = provider

    async def health_check(self) -> Any:
        return await self._provider.health_check()

    async def transcribe(self, audio: bytes, config: dict[str, Any]) -> STTResult:
        return await self._provider.transcribe(audio, config)

    async def supported_languages(self) -> list[str]:
        return await self._provider.supported_languages()

    def list_models(self) -> list[STTModelInfo]:
        return CURATED_STT_MODELS


class TTSService:
    """Orchestrates Text-to-Speech synthesis."""

    def __init__(self, provider: TTSProvider) -> None:
        self._provider = provider

    async def health_check(self) -> Any:
        return await self._provider.health_check()

    async def synthesize(self, text: str, config: dict[str, Any]) -> bytes:
        return await self._provider.synthesize(text, config)

    async def supported_voices(self) -> list[TTSVoiceInfo]:
        return await self._provider.supported_voices()


class VADService:
    """Orchestrates Voice Activity Detection."""

    def __init__(self, provider: VADProvider) -> None:
        self._provider = provider

    async def health_check(self) -> Any:
        return await self._provider.health_check()

    async def detect_speech(self, audio: bytes, sample_rate: int = 16000) -> VADResult:
        return await self._provider.detect_speech(audio, sample_rate=sample_rate)

    def reset(self) -> None:
        self._provider.reset()


async def get_speech_runtime_health(
    stt: STTService, tts: TTSService, vad: VADService
) -> SpeechRuntimeHealth:
    """Aggregate health across STT, TTS, and VAD providers."""
    return SpeechRuntimeHealth(
        stt=await stt.health_check(),
        tts=await tts.health_check(),
        vad=await vad.health_check(),
    )
