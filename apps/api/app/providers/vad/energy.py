"""Offline RMS Energy + Hangover VADProvider (zero external dependencies)."""

from __future__ import annotations

import array
import math

from app.providers.vad.base import VADProvider
from app.schemas.speech import SpeechProviderHealth, VADResult


class EnergyVADProvider(VADProvider):
    """Stateful offline Voice Activity Detector with speech/silence hangover."""

    provider_id = "energy"

    def __init__(
        self,
        threshold: float = 0.015,
        min_speech_ms: int = 250,
        min_silence_ms: int = 700,
        max_utterance_ms: int = 20000,
    ) -> None:
        self.threshold = threshold
        self.min_speech_ms = min_speech_ms
        self.min_silence_ms = min_silence_ms
        self.max_utterance_ms = max_utterance_ms

        self._in_speech = False
        self._speech_ms = 0.0
        self._silence_ms = 0.0
        self._utterance_ms = 0.0

    def reset(self) -> None:
        self._in_speech = False
        self._speech_ms = 0.0
        self._silence_ms = 0.0
        self._utterance_ms = 0.0

    @staticmethod
    def compute_rms(audio: bytes) -> float:
        """Compute normalized RMS amplitude (0.0 to 1.0) for PCM s16le bytes."""
        if len(audio) < 2:
            return 0.0
        usable_len = len(audio) - (len(audio) % 2)
        samples = array.array("h")
        samples.frombytes(audio[:usable_len])
        if not samples:
            return 0.0
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / len(samples)) / 32768.0
        return round(rms, 5)

    async def health_check(self) -> SpeechProviderHealth:
        return SpeechProviderHealth(
            provider=self.provider_id,
            available=True,
            is_local=True,
            details=f"threshold={self.threshold}, min_silence_ms={self.min_silence_ms}",
        )

    async def detect_speech(self, audio: bytes, sample_rate: int = 16000) -> VADResult:
        if len(audio) < 2 or sample_rate <= 0:
            return VADResult(is_speech=False, energy_rms=0.0, event="none")

        chunk_ms = ((len(audio) // 2) / float(sample_rate)) * 1000.0
        rms = self.compute_rms(audio)
        above = rms >= self.threshold

        if above:
            self._silence_ms = 0.0
            self._speech_ms += chunk_ms
            if not self._in_speech:
                if self._speech_ms >= self.min_speech_ms:
                    self._in_speech = True
                    self._utterance_ms = self._speech_ms
                    return VADResult(is_speech=True, energy_rms=rms, event="speech_start")
                return VADResult(is_speech=True, energy_rms=rms, event="none")

            self._utterance_ms += chunk_ms
            if self._utterance_ms >= self.max_utterance_ms:
                self.reset()
                return VADResult(is_speech=False, energy_rms=rms, event="speech_end")
            return VADResult(is_speech=True, energy_rms=rms, event="speech_continue")

        # Below threshold
        if self._in_speech:
            self._silence_ms += chunk_ms
            self._utterance_ms += chunk_ms
            if self._silence_ms >= self.min_silence_ms or self._utterance_ms >= self.max_utterance_ms:
                self.reset()
                return VADResult(is_speech=False, energy_rms=rms, event="speech_end")
            return VADResult(is_speech=False, energy_rms=rms, event="speech_continue")

        self._speech_ms = 0.0
        return VADResult(is_speech=False, energy_rms=rms, event="none")
