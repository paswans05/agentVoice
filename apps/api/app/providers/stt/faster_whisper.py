"""Local Speech-to-Text using faster-whisper (MIT License, CTranslate2)."""

from __future__ import annotations

import asyncio
import io
import logging
from pathlib import Path
from typing import Any
import wave

from app.providers.stt.base import (
    STTAudioError,
    STTProvider,
    STTProviderError,
    STTUnavailableError,
)
from app.schemas.speech import SpeechProviderHealth, STTResult, STTSegment

logger = logging.getLogger(__name__)


class FasterWhisperSTTProvider(STTProvider):
    """Local offline STT using faster-whisper with CPU int8 fallback."""

    provider_id = "faster-whisper"

    def __init__(
        self,
        model_size: str = "small",
        device: str = "auto",
        compute_type: str = "int8",
        download_root: Path | None = None,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root
        self._model: Any = None

    @staticmethod
    def _is_package_installed() -> bool:
        try:
            import faster_whisper  # noqa: F401

            return True
        except ImportError:
            return False

    async def health_check(self) -> SpeechProviderHealth:
        if not self._is_package_installed():
            return SpeechProviderHealth(
                provider=self.provider_id,
                available=False,
                is_local=True,
                error=(
                    "faster-whisper is not installed. Install speech extras: "
                    "`uv sync --extra speech` (or `pip install faster-whisper`)."
                ),
            )
        return SpeechProviderHealth(
            provider=self.provider_id,
            available=True,
            is_local=True,
            details=f"model={self.model_size}, device={self.device}, compute={self.compute_type}",
        )

    def _get_or_load_model(self, model_size: str) -> Any:
        if self._model is not None and getattr(self._model, "_av_size", None) == model_size:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise STTUnavailableError(
                "faster-whisper is not installed. Install with `pip install faster-whisper`."
            ) from exc

        kwargs: dict[str, Any] = {
            "device": self.device if self.device != "auto" else "cpu",
            "compute_type": self.compute_type,
        }
        if self.download_root is not None:
            kwargs["download_root"] = str(self.download_root)

        model = WhisperModel(model_size, **kwargs)
        model._av_size = model_size  # type: ignore[attr-defined]
        self._model = model
        return model

    @staticmethod
    def _wav_or_pcm_to_float32(
        audio: bytes, audio_format: str, sample_rate: int
    ) -> tuple[Any, float]:
        import numpy as np

        if not audio or len(audio) < 320:
            raise STTAudioError("Audio input is empty or too short for transcription.")

        if audio_format == "audio/wav" or audio[:4] == b"RIFF":
            try:
                with wave.open(io.BytesIO(audio), "rb") as wf:
                    channels = wf.getnchannels()
                    sampwidth = wf.getsampwidth()
                    rate = wf.getframerate() or sample_rate
                    frames = wf.getnframes()
                    raw_pcm = wf.readframes(frames)
            except wave.Error as exc:
                raise STTAudioError(f"Invalid WAV audio header: {exc}") from exc

            if sampwidth != 2:
                raise STTAudioError(f"Unsupported WAV sample width: {sampwidth * 8}-bit (expected 16-bit).")
            samples = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0
            if channels > 1:
                samples = samples.reshape(-1, channels).mean(axis=1)
            duration = frames / float(rate)
            if rate != 16000 and len(samples) > 0:
                target_len = int(len(samples) * 16000 / rate)
                samples = np.interp(
                    np.linspace(0, len(samples) - 1, target_len),
                    np.arange(len(samples)),
                    samples,
                ).astype(np.float32)
            return samples, round(duration, 3)

        if audio_format == "pcm_s16le":
            if len(audio) % 2 != 0:
                raise STTAudioError("PCM s16le audio byte length must be even.")
            samples = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            duration = len(samples) / float(sample_rate)
            if sample_rate != 16000 and len(samples) > 0:
                target_len = int(len(samples) * 16000 / sample_rate)
                samples = np.interp(
                    np.linspace(0, len(samples) - 1, target_len),
                    np.arange(len(samples)),
                    samples,
                ).astype(np.float32)
            return samples, round(duration, 3)

        raise STTAudioError(f"Unsupported audio format: {audio_format}")

    def _transcribe_sync(
        self,
        audio_array: Any,
        model_size: str,
        language: str | None,
        initial_prompt: str | None,
    ) -> tuple[str, str | None, list[STTSegment]]:
        model = self._get_or_load_model(model_size)
        kwargs: dict[str, Any] = {"beam_size": 3, "vad_filter": False}
        if language:
            kwargs["language"] = language
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt

        segments_iter, info = model.transcribe(audio_array, **kwargs)
        segments: list[STTSegment] = []
        parts: list[str] = []
        for seg in segments_iter:
            txt = seg.text.strip()
            if txt:
                parts.append(txt)
                segments.append(
                    STTSegment(
                        start=round(float(seg.start), 3),
                        end=round(float(seg.end), 3),
                        text=txt,
                    )
                )
        detected_lang = getattr(info, "language", None)
        return " ".join(parts).strip(), detected_lang, segments

    async def transcribe(self, audio: bytes, config: dict[str, Any]) -> STTResult:
        audio_format = str(config.get("format", "pcm_s16le"))
        sample_rate = int(config.get("sample_rate", 16000))
        model_size = str(config.get("model", self.model_size))
        language_hint = config.get("language")
        hinglish_mode = str(config.get("hinglish_script_mode", "auto"))

        # Map locale like hi-IN / en-IN to Whisper 2-letter code
        whisper_lang: str | None = None
        if isinstance(language_hint, str) and language_hint.strip():
            whisper_lang = language_hint.split("-")[0].lower()

        initial_prompt: str | None = None
        if hinglish_mode in ("auto", "english"):
            initial_prompt = "Namaste, AI voice agent, business, support, demo, callback."

        audio_array, duration = self._wav_or_pcm_to_float32(audio, audio_format, sample_rate)

        try:
            text, detected_lang, segments = await asyncio.to_thread(
                self._transcribe_sync,
                audio_array,
                model_size,
                whisper_lang,
                initial_prompt,
            )
        except STTUnavailableError:
            raise
        except Exception as exc:
            logger.exception("faster-whisper transcription failed")
            raise STTProviderError(f"STT transcription failed: {exc}") from exc

        return STTResult(
            text=text,
            raw_text=text,
            language=detected_lang,
            segments=segments,
            duration_seconds=duration,
            is_final=True,
        )

    async def supported_languages(self) -> list[str]:
        return ["hi", "en"]
