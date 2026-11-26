"""Pydantic schemas for local STT, TTS, VAD, audio settings, and voice sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VoiceSessionState(str, Enum):
    """Explicit backend-controlled states for a real-time voice session."""

    IDLE = "IDLE"
    CONNECTING = "CONNECTING"
    LISTENING = "LISTENING"
    SPEECH_DETECTED = "SPEECH_DETECTED"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    GENERATING_SPEECH = "GENERATING_SPEECH"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    ERROR = "ERROR"
    COMPLETED = "COMPLETED"


class SpeechProviderHealth(BaseModel):
    """Health status for a speech provider (STT, TTS, or VAD)."""

    provider: str
    available: bool
    is_local: bool = True
    details: str | None = None
    error: str | None = None


class SpeechRuntimeHealth(BaseModel):
    """Combined health status for local speech engines."""

    stt: SpeechProviderHealth
    tts: SpeechProviderHealth
    vad: SpeechProviderHealth
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class STTSegment(BaseModel):
    """Timed segment from speech-to-text transcription."""

    start: float
    end: float
    text: str


class STTResult(BaseModel):
    """Normalized transcription output from STTProvider."""

    text: str
    raw_text: str | None = None
    language: str | None = None
    segments: list[STTSegment] = Field(default_factory=list)
    duration_seconds: float = 0.0
    is_final: bool = True


class STTModelInfo(BaseModel):
    """Available or installed STT model metadata."""

    id: str
    name: str
    provider: str
    languages: list[str]
    approximate_size: str
    min_ram_gb: int
    license: str
    installed: bool = False


class TTSVoiceInfo(BaseModel):
    """Installed TTS voice metadata (never fabricated)."""

    id: str
    name: str
    provider: str
    language: str
    sample_rate: int = 22050
    license: str = "MIT"
    installed: bool = True


class TTSSynthesizeRequest(BaseModel):
    """Request payload for REST TTS synthesis."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)
    provider: str = Field(default="piper", min_length=1, max_length=60)
    voice_id: str = Field(default="default", min_length=1, max_length=120)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)


class VADResult(BaseModel):
    """Voice Activity Detection decision for an audio frame."""

    is_speech: bool
    energy_rms: float
    event: Literal["none", "speech_start", "speech_continue", "speech_end"] = "none"


class AudioSettings(BaseModel):
    """User-level audio & speech defaults (agent-specific config takes precedence)."""

    model_config = ConfigDict(extra="forbid")

    input_sample_rate: int = Field(default=16000, ge=8000, le=48000)
    output_format: Literal["audio/wav", "pcm_s16le"] = "audio/wav"
    stt_provider: str = Field(default="faster-whisper", min_length=1, max_length=60)
    stt_model: str = Field(default="small", min_length=1, max_length=80)
    hinglish_script_mode: Literal["auto", "original", "hindi", "english"] = "auto"
    tts_provider: str = Field(default="piper", min_length=1, max_length=60)
    default_voice_id: str = Field(default="default", min_length=1, max_length=120)
    default_speed: float = Field(default=1.0, ge=0.5, le=2.0)
    default_pitch: float = Field(default=1.0, ge=0.5, le=2.0)
    vad_threshold: float = Field(default=0.015, ge=0.001, le=0.5)
    min_speech_ms: int = Field(default=250, ge=50, le=2000)
    min_silence_ms: int = Field(default=700, ge=200, le=5000)
    max_utterance_ms: int = Field(default=20000, ge=2000, le=60000)


class LatencyMetrics(BaseModel):
    """Per-turn stage latency measurements in milliseconds."""

    vad_ms: int = 0
    stt_ms: int = 0
    llm_ttft_ms: int = 0
    llm_total_ms: int = 0
    tts_ms: int = 0
    total_ms: int = 0


class VoiceSessionCreate(BaseModel):
    """Payload to create a real-time voice session."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=3, max_length=64)
    conversation_id: str | None = Field(default=None, max_length=64)
    allow_draft_preview: bool = True


class VoiceSessionInfo(BaseModel):
    """Public state of a voice conversation session."""

    session_id: str
    agent_id: str
    conversation_id: str
    model_id: str
    state: VoiceSessionState
    stt_provider: str
    tts_provider: str
    voice_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_latency: LatencyMetrics | None = None
