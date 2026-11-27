"""Pydantic schemas for Live Calls, Normalized Events, Transcripts, Metrics, and Controls."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CallSessionType(str, Enum):
    BROWSER = "BROWSER"
    TELEPHONY = "TELEPHONY"
    INTERNAL_TEST = "INTERNAL_TEST"


class CallDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class CallSessionStatus(str, Enum):
    CREATED = "CREATED"
    INITIATING = "INITIATING"
    RINGING = "RINGING"
    ANSWERED = "ANSWERED"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    TRANSFERRING = "TRANSFERRING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BUSY = "BUSY"
    NO_ANSWER = "NO_ANSWER"
    TERMINATED = "TERMINATED"
    DISCONNECTED = "DISCONNECTED"


class CallEventType(str, Enum):
    CALL_CREATED = "CALL_CREATED"
    CALL_INITIATING = "CALL_INITIATING"
    CALL_RINGING = "CALL_RINGING"
    CALL_ANSWERED = "CALL_ANSWERED"
    CALL_STARTED = "CALL_STARTED"
    CALL_ENDED = "CALL_ENDED"
    CALL_FAILED = "CALL_FAILED"
    CALL_DISCONNECTED = "CALL_DISCONNECTED"
    CALL_ON_HOLD = "CALL_ON_HOLD"
    CALL_RESUMED = "CALL_RESUMED"
    CALL_TRANSFER_STARTED = "CALL_TRANSFER_STARTED"
    CALL_TRANSFER_COMPLETED = "CALL_TRANSFER_COMPLETED"
    SPEECH_DETECTED = "SPEECH_DETECTED"
    TRANSCRIPTION_PARTIAL = "TRANSCRIPTION_PARTIAL"
    TRANSCRIPTION_FINAL = "TRANSCRIPTION_FINAL"
    AI_THINKING = "AI_THINKING"
    AI_RESPONSE_STARTED = "AI_RESPONSE_STARTED"
    AI_RESPONSE_COMPLETED = "AI_RESPONSE_COMPLETED"
    TTS_STARTED = "TTS_STARTED"
    TTS_COMPLETED = "TTS_COMPLETED"
    CALL_WARNING = "CALL_WARNING"
    CALL_ERROR = "CALL_ERROR"
    CONSENT_CAPTURED = "CONSENT_CAPTURED"
    DO_NOT_CALL_REQUESTED = "DO_NOT_CALL_REQUESTED"
    HUMAN_HANDOFF_REQUESTED = "HUMAN_HANDOFF_REQUESTED"


class TranscriptSpeaker(str, Enum):
    CUSTOMER = "CUSTOMER"
    AI_AGENT = "AI_AGENT"
    HUMAN_OPERATOR = "HUMAN_OPERATOR"
    SYSTEM = "SYSTEM"


class CallSession(BaseModel):
    """Real-time or completed call session record."""

    model_config = ConfigDict(extra="forbid")

    id: str
    external_call_id: str | None = None
    provider_call_id: str | None = None
    campaign_id: str | None = None
    campaign_lead_id: str | None = None
    lead_id: str | None = None
    agent_id: str
    conversation_id: str | None = None
    session_type: CallSessionType = CallSessionType.BROWSER
    direction: CallDirection = CallDirection.INBOUND
    status: CallSessionStatus = CallSessionStatus.CREATED
    caller_number_masked: str = ""
    destination_number_masked: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    answered_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int = 0
    current_speaker: TranscriptSpeaker | None = None
    current_agent_state: str = "IDLE"
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    outcome: str | None = None
    end_reason: str | None = None
    flagged_for_review: bool = False
    flag_reason: str | None = None
    provider: str = "browser"
    recording_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NormalizedCallEvent(BaseModel):
    """Normalized call event delivered over storage and WebSocket."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    call_id: str
    event_type: CallEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sequence_number: int = 1
    source: str = "voice_engine"
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TranscriptSegment(BaseModel):
    """Partial or finalized transcript segment."""

    model_config = ConfigDict(extra="forbid")

    segment_id: str
    call_id: str
    speaker: TranscriptSpeaker
    text: str
    final: bool = True
    start_time_ms: int | None = None
    end_time_ms: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    language: str | None = None
    confidence: float | None = None
    source: str = "stt"


class CallMetricsSnapshot(BaseModel):
    """Technical latency and stream health metrics for a call."""

    model_config = ConfigDict(extra="forbid")

    call_id: str
    stt_latency_ms: int | None = None
    llm_ttft_ms: int | None = None
    llm_total_ms: int | None = None
    tts_latency_ms: int | None = None
    end_to_end_ms: int | None = None
    provider_healthy: bool = True
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LiveCallsStats(BaseModel):
    active_calls: int
    ringing_calls: int
    in_progress_calls: int
    on_hold_calls: int
    attention_required_calls: int
    recently_completed_calls: int
    provider_status: str


class CallMonitoringSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recording_enabled_by_default: bool = False
    require_explicit_recording_consent: bool = True
    transcript_retention_days: int = Field(default=30, ge=1, le=3650)
    mask_customer_numbers: bool = True
    heartbeat_interval_seconds: int = Field(default=20, ge=5, le=120)


class CallControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="Operator action", max_length=300)


class CallTransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str = Field(min_length=2, max_length=120)
    reason: str = Field(default="Customer requested human handoff", max_length=300)


class CallFlagRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=2, max_length=300)
