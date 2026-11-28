"""Pydantic schemas for Android & iPhone Device Gateway & Mobile VoIP."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DevicePlatform(str, Enum):
    ANDROID = "android"
    IOS = "ios"


class DeviceStatus(str, Enum):
    PAIRING = "PAIRING"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    REVOKED = "REVOKED"
    ERROR = "ERROR"


class DeviceEventType(str, Enum):
    DEVICE_REGISTERED = "DEVICE_REGISTERED"
    DEVICE_ONLINE = "DEVICE_ONLINE"
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    HEARTBEAT_RECEIVED = "HEARTBEAT_RECEIVED"
    NETWORK_CHANGED = "NETWORK_CHANGED"
    SIM_STATUS_CHANGED = "SIM_STATUS_CHANGED"
    CALL_REQUESTED = "CALL_REQUESTED"
    CALL_STARTED = "CALL_STARTED"
    CALL_CONNECTED = "CALL_CONNECTED"
    CALL_ENDED = "CALL_ENDED"
    CALL_FAILED = "CALL_FAILED"
    VOIP_CONNECTED = "VOIP_CONNECTED"
    VOIP_DISCONNECTED = "VOIP_DISCONNECTED"
    PERMISSION_CHANGED = "PERMISSION_CHANGED"
    DEVICE_ERROR = "DEVICE_ERROR"


class DeviceCapabilityProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: DevicePlatform
    cellular_call_initiation: bool = False
    cellular_call_state: bool = False
    cellular_audio_capture: bool = False
    cellular_audio_injection: bool = False
    cellular_audio_bridge_status: str = "CELLULAR_AUDIO_BRIDGE_UNAVAILABLE"
    voip_supported: bool = True
    callkit_supported: bool = False
    webrtc_supported: bool = False
    browser: str | None = None
    device_health: bool = True
    ai_call_ready: bool = False


class DeviceHealthSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    battery_percent: int | None = Field(default=None, ge=0, le=100)
    battery_charging: bool | None = None
    network_type: str = "unknown"
    connected: bool = True
    sim_present: bool | None = None
    carrier_name: str | None = None
    signal_strength_dbm: int | None = None
    mic_permission: str | None = None
    page_visible: bool | None = None
    permissions: dict[str, bool] = Field(default_factory=dict)
    last_error: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Device(BaseModel):
    """Public registered mobile device record (never contains credentials)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    account_id: str
    device_name: str
    platform: DevicePlatform
    platform_version: str
    app_version: str
    device_status: DeviceStatus = DeviceStatus.ONLINE
    capability_profile: DeviceCapabilityProfile
    health: DeviceHealthSnapshot = Field(default_factory=DeviceHealthSnapshot)
    last_seen_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PairingCodeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(default="default_operator", min_length=1, max_length=100)
    platform: DevicePlatform = DevicePlatform.ANDROID
    ttl_seconds: int = Field(default=300, ge=30, le=900)


class PairingCodePublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    account_id: str
    platform: DevicePlatform
    used: bool = False
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DevicePairRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pairing_code: str = Field(min_length=4, max_length=32)
    device_name: str = Field(min_length=2, max_length=100)
    platform: DevicePlatform
    platform_version: str = Field(min_length=1, max_length=40)
    app_version: str = Field(min_length=1, max_length=40)
    capability_profile: DeviceCapabilityProfile | None = None


class DevicePairResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device: Device
    device_token: str
    token_expires_at: datetime


class DeviceHeartbeatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    health: DeviceHealthSnapshot
    capability_profile: DeviceCapabilityProfile | None = None


class DeviceCommandCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_type: str = Field(
        min_length=2,
        max_length=60,
        pattern="^(PING|REFRESH_CAPABILITIES|SYNC_CONFIG|REQUEST_OUTBOUND_CALL|START_VOIP_SESSION|END_VOIP_SESSION)$",
    )
    payload: dict[str, Any] = Field(default_factory=dict)


class DeviceCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    device_id: str
    command_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str = "QUEUED"
    result: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeviceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    device_id: str
    event_type: DeviceEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)


class MobileVoIPSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=100)
    agent_id: str = Field(min_length=1, max_length=100)
    direction: str = Field(default="OUTBOUND", pattern="^(INBOUND|OUTBOUND)$")
    provider: str = Field(default="asterisk", min_length=1, max_length=60)


class MobileVoIPSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    device_id: str
    agent_id: str
    call_session_id: str | None = None
    direction: str = "OUTBOUND"
    call_source: str = "AGENTVOICE_VOIP"
    status: str = "ACTIVE"
    provider: str = "asterisk"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None


class PairingConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=100)


class WebRTCSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=100)
    agent_id: str = Field(min_length=1, max_length=100)
    voice_session_id: str | None = Field(default=None, max_length=100)
    stun_urls: list[str] = Field(default_factory=lambda: ["stun:stun.l.google.com:19302"])


class WebRTCSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    device_id: str
    agent_id: str
    call_session_id: str | None = None
    voice_session_id: str | None = None
    call_source: str = "AGENTVOICE_INTERNET_VOICE_CALL"
    status: str = "SIGNALING"
    ice_state: str = "new"
    stun_urls: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
