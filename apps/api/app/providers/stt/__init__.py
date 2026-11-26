"""STT providers package."""

from .base import STTAudioError, STTProvider, STTProviderError, STTUnavailableError
from .factory import STTProviderFactory
from .faster_whisper import FasterWhisperSTTProvider

__all__ = [
    "STTProvider",
    "STTProviderFactory",
    "FasterWhisperSTTProvider",
    "STTProviderError",
    "STTUnavailableError",
    "STTAudioError",
]
