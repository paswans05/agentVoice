"""Local Text-to-Speech using Piper (MIT License, ONNX neural TTS)."""

from __future__ import annotations

import asyncio
import io
import json
import logging
from pathlib import Path
import shutil
import subprocess
from typing import Any
import wave

from app.providers.tts.base import (
    TTSProvider,
    TTSProviderError,
    TTSUnavailableError,
    TTSValidationError,
    TTSVoiceNotFoundError,
)
from app.schemas.speech import SpeechProviderHealth, TTSVoiceInfo

logger = logging.getLogger(__name__)


class PiperTTSProvider(TTSProvider):
    """Local offline TTS using Piper ONNX voice models."""

    provider_id = "piper"

    def __init__(self, models_dir: Path) -> None:
        self.models_dir = Path(models_dir)
        self._loaded_voices: dict[str, Any] = {}

    @staticmethod
    def _has_piper_python() -> bool:
        try:
            import piper  # noqa: F401

            return True
        except ImportError:
            return False

    @staticmethod
    def _has_piper_cli() -> str | None:
        return shutil.which("piper")

    def _discover_voice_files(self) -> dict[str, Path]:
        """Scan models_dir for installed .onnx Piper voice files."""
        voices: dict[str, Path] = {}
        if not self.models_dir.exists():
            return voices
        for onnx_path in sorted(self.models_dir.glob("*.onnx")):
            voices[onnx_path.stem] = onnx_path
        return voices

    async def health_check(self) -> SpeechProviderHealth:
        has_py = self._has_piper_python()
        has_cli = self._has_piper_cli() is not None
        voices = self._discover_voice_files()

        if not has_py and not has_cli:
            return SpeechProviderHealth(
                provider=self.provider_id,
                available=False,
                is_local=True,
                error=(
                    "Piper TTS is not installed. Install `piper-tts` (`pip install piper-tts`) "
                    "or place the `piper` binary in PATH."
                ),
            )
        if not voices:
            return SpeechProviderHealth(
                provider=self.provider_id,
                available=True,
                is_local=True,
                details=f"Engine ready, 0 voices installed in {self.models_dir}",
            )
        return SpeechProviderHealth(
            provider=self.provider_id,
            available=True,
            is_local=True,
            details=f"{len(voices)} voice(s) installed in {self.models_dir}",
        )

    async def supported_voices(self) -> list[TTSVoiceInfo]:
        result: list[TTSVoiceInfo] = []
        for voice_id, onnx_path in self._discover_voice_files().items():
            cfg_path = onnx_path.with_suffix(".onnx.json")
            language = "unknown"
            sample_rate = 22050
            if cfg_path.exists():
                try:
                    meta = json.loads(cfg_path.read_text(encoding="utf-8"))
                    lang_info = meta.get("language") or {}
                    language = str(lang_info.get("code") or voice_id.split("-")[0])
                    audio_info = meta.get("audio") or {}
                    sample_rate = int(audio_info.get("sample_rate") or 22050)
                except Exception:
                    pass
            result.append(
                TTSVoiceInfo(
                    id=voice_id,
                    name=voice_id,
                    provider=self.provider_id,
                    language=language,
                    sample_rate=sample_rate,
                    license="MIT / model-specific",
                    installed=True,
                )
            )
        return result

    def _synthesize_with_python(self, text: str, onnx_path: Path, length_scale: float) -> bytes:
        from piper.voice import PiperVoice  # type: ignore[import-not-found]

        key = str(onnx_path)
        voice = self._loaded_voices.get(key)
        if voice is None:
            voice = PiperVoice.load(str(onnx_path))
            self._loaded_voices[key] = voice

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            if hasattr(voice, "synthesize_wav"):
                from piper.config import SynthesisConfig  # type: ignore[import-not-found]

                syn_cfg = SynthesisConfig(length_scale=length_scale)
                voice.synthesize_wav(text, wf, syn_config=syn_cfg)
            else:
                voice.synthesize(text, wf, length_scale=length_scale)
        return buf.getvalue()

    def _synthesize_with_cli(
        self, cli_path: str, text: str, onnx_path: Path, length_scale: float
    ) -> bytes:
        proc = subprocess.run(
            [
                cli_path,
                "--model",
                str(onnx_path),
                "--length_scale",
                f"{length_scale:.3f}",
                "--output-raw",
            ],
            input=text.encode("utf-8"),
            capture_output=True,
            check=False,
            timeout=60,
        )
        if proc.returncode != 0:
            raise TTSProviderError(
                f"Piper CLI failed ({proc.returncode}): {proc.stderr.decode('utf-8', 'ignore')}"
            )
        sample_rate = 22050
        cfg_path = onnx_path.with_suffix(".onnx.json")
        if cfg_path.exists():
            try:
                meta = json.loads(cfg_path.read_text(encoding="utf-8"))
                sample_rate = int((meta.get("audio") or {}).get("sample_rate") or 22050)
            except Exception:
                pass
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(proc.stdout)
        return buf.getvalue()

    async def synthesize(self, text: str, config: dict[str, Any]) -> bytes:
        cleaned = text.strip()
        if not cleaned:
            raise TTSValidationError("TTS input text cannot be empty.")
        if len(cleaned) > 4000:
            raise TTSValidationError("TTS input text exceeds 4000 character limit.")

        speed = float(config.get("speed", 1.0))
        if speed < 0.5 or speed > 2.0:
            raise TTSValidationError("Speaking speed must be between 0.5 and 2.0.")

        voice_id = str(config.get("voice_id") or "").strip()
        voices = self._discover_voice_files()

        if not voices:
            raise TTSVoiceNotFoundError(
                f"No Piper TTS voice models found in {self.models_dir}. "
                "Download a Piper .onnx voice model first."
            )

        if voice_id in ("", "default"):
            raise TTSVoiceNotFoundError(
                "No specific TTS voice_id is configured on this agent. "
                f"Available installed voices: {', '.join(voices.keys())}"
            )

        onnx_path = voices.get(voice_id)
        if onnx_path is None:
            raise TTSVoiceNotFoundError(
                f"Voice '{voice_id}' is not installed. "
                f"Installed voices: {', '.join(voices.keys())}"
            )

        # Piper length_scale is inverse of speed
        length_scale = round(1.0 / speed, 3)

        if self._has_piper_python():
            return await asyncio.to_thread(
                self._synthesize_with_python, cleaned, onnx_path, length_scale
            )

        cli_path = self._has_piper_cli()
        if cli_path:
            return await asyncio.to_thread(
                self._synthesize_with_cli, cli_path, cleaned, onnx_path, length_scale
            )

        raise TTSUnavailableError(
            "Piper TTS engine is not installed. Install `piper-tts` or the `piper` binary."
        )
