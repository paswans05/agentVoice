"""Pydantic schemas for internal Asterisk 23 SIP/WebRTC calling."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class InternalCallMode(str, Enum):
    HUMAN = "human"
    AI = "ai"
    ECHO = "echo"


class InternalCallStatus(str, Enum):
    INITIATING = "INITIATING"
    RINGING = "RINGING"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    FAILED = "FAILED"


class InternalExtension(BaseModel):
    """Public extension status (never includes SIP passwords or secrets)."""

    model_config = ConfigDict(extra="forbid")

    extension: str
    label: str
    transport: str = "UDP"
    webrtc_enabled: bool = False
    registered: bool = False
    state: str = "offline"
    active_channels: int = 0


class InternalCallDialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_extension: str = Field(min_length=2, max_length=32)
    to_extension: str = Field(min_length=2, max_length=40)
    mode: InternalCallMode = InternalCallMode.HUMAN
    agent_id: str | None = Field(default=None, max_length=64)
    idempotency_key: str | None = Field(default=None, max_length=120)


class InternalCallHangupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="operator_hangup", max_length=120)


class InternalCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: str
    provider_id: str
    channel_id: str
    live_call_session_id: str | None = None
    from_extension: str
    to_extension: str
    mode: InternalCallMode = InternalCallMode.HUMAN
    agent_id: str | None = None
    status: InternalCallStatus = InternalCallStatus.INITIATING
    is_external: bool = False
    idempotency_key: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    answered_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int = 0
    hangup_reason: str | None = None


class InternalCallsHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ari_connected: bool
    provider_id: str | None = None
    provider_name: str | None = None
    asterisk_version: str | None = None
    registered_extensions: int = 0
    active_calls: int = 0
    external_telephony_configured: bool = False
    message: str = ""
