"""Pydantic schemas for Phase 10 Telephony Integration (strictly masking secrets)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TelephonyProviderType(str, Enum):
    ASTERISK = "asterisk"
    SIP_TRUNK = "sip_trunk"
    GSM_GATEWAY = "gsm_gateway"
    DRY_RUN = "dry_run"
    CUSTOM = "custom"


class TransportProtocol(str, Enum):
    UDP = "UDP"
    TCP = "TCP"
    TLS = "TLS"


class SipAuthMode(str, Enum):
    USERPASS_REGISTRATION = "userpass_registration"
    IP_WHITELIST = "ip_whitelist"
    DIGEST_CHALLENGE = "digest_challenge"


class ProviderConnectionStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    REGISTERING = "REGISTERING"
    CONNECTED = "CONNECTED"
    AUTH_FAILED = "AUTH_FAILED"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNAVAILABLE = "UNAVAILABLE"
    INCOMPLETE = "INCOMPLETE"


class ProviderCapabilitiesSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inbound: bool = False
    outbound: bool = False
    hold: bool = False
    transfer: bool = False
    recording: bool = False
    dtmf: bool = False
    supported_codecs: list[str] = Field(default_factory=lambda: ["PCMU", "PCMA"])
    max_concurrent_calls: int = Field(default=10, ge=1, le=500)


class TelephonyProviderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    provider_type: TelephonyProviderType = TelephonyProviderType.ASTERISK
    host: str = Field(default="", max_length=255)
    port: int = Field(default=8088, ge=1, le=65535)
    use_tls: bool = True
    transport: TransportProtocol = TransportProtocol.TLS
    auth_mode: SipAuthMode = SipAuthMode.USERPASS_REGISTRATION
    username: str = Field(default="", max_length=120)
    password: str | None = Field(default=None, max_length=255)
    auth_username: str | None = Field(default=None, max_length=120)
    sip_domain: str | None = Field(default=None, max_length=255)
    outbound_proxy: str | None = Field(default=None, max_length=255)
    ari_base_url: str | None = Field(default=None, max_length=300)
    ari_app: str = Field(default="agentvoice", max_length=80)
    ari_username: str | None = Field(default=None, max_length=120)
    ari_password: str | None = Field(default=None, max_length=255)
    caller_id: str | None = Field(default=None, max_length=40)
    allowed_destinations: list[str] = Field(default_factory=list)
    connection_timeout_seconds: int = Field(default=10, ge=2, le=60)
    max_concurrent_calls: int = Field(default=5, ge=1, le=200)
    supported_codecs: list[str] = Field(default_factory=lambda: ["PCMU", "PCMA"])
    enabled: bool = True
    webhook_secret: str | None = Field(default=None, max_length=255)
    options: dict[str, Any] = Field(default_factory=dict)


class TelephonyProviderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=100)
    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    use_tls: bool | None = None
    transport: TransportProtocol | None = None
    auth_mode: SipAuthMode | None = None
    username: str | None = Field(default=None, max_length=120)
    password: str | None = Field(default=None, max_length=255)
    auth_username: str | None = Field(default=None, max_length=120)
    sip_domain: str | None = Field(default=None, max_length=255)
    outbound_proxy: str | None = Field(default=None, max_length=255)
    ari_base_url: str | None = Field(default=None, max_length=300)
    ari_app: str | None = Field(default=None, max_length=80)
    ari_username: str | None = Field(default=None, max_length=120)
    ari_password: str | None = Field(default=None, max_length=255)
    caller_id: str | None = Field(default=None, max_length=40)
    allowed_destinations: list[str] | None = None
    connection_timeout_seconds: int | None = Field(default=None, ge=2, le=60)
    max_concurrent_calls: int | None = Field(default=None, ge=1, le=200)
    supported_codecs: list[str] | None = None
    enabled: bool | None = None
    webhook_secret: str | None = Field(default=None, max_length=255)
    options: dict[str, Any] | None = None


class TelephonyProviderPublic(BaseModel):
    """Public provider representation — never contains raw passwords or tokens."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    provider_type: TelephonyProviderType
    supports_real_calls: bool = True
    configured: bool = False
    status: ProviderConnectionStatus = ProviderConnectionStatus.DISCONNECTED
    message: str = ""
    host: str = ""
    port: int = 8088
    use_tls: bool = True
    transport: TransportProtocol = TransportProtocol.TLS
    auth_mode: SipAuthMode = SipAuthMode.USERPASS_REGISTRATION
    username: str = ""
    auth_username: str | None = None
    sip_domain: str | None = None
    outbound_proxy: str | None = None
    ari_base_url: str | None = None
    ari_app: str = "agentvoice"
    ari_username: str | None = None
    caller_id: str | None = None
    allowed_destinations: list[str] = Field(default_factory=list)
    connection_timeout_seconds: int = 10
    max_concurrent_calls: int = 5
    supported_codecs: list[str] = Field(default_factory=lambda: ["PCMU", "PCMA"])
    enabled: bool = True
    has_password: bool = False
    has_ari_password: bool = False
    has_webhook_secret: bool = False
    capabilities: ProviderCapabilitiesSchema = Field(default_factory=ProviderCapabilitiesSchema)
    last_checked_at: datetime | None = None
    last_error: str | None = None
    credential_rotated_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SipTrunkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    provider_id: str = Field(min_length=1, max_length=100)
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=5060, ge=1, le=65535)
    transport: TransportProtocol = TransportProtocol.UDP
    auth_mode: SipAuthMode = SipAuthMode.USERPASS_REGISTRATION
    username: str = Field(default="", max_length=120)
    password: str | None = Field(default=None, max_length=255)
    auth_username: str | None = Field(default=None, max_length=120)
    sip_domain: str | None = Field(default=None, max_length=255)
    outbound_proxy: str | None = Field(default=None, max_length=255)
    caller_id: str = Field(min_length=2, max_length=40)
    register_required: bool = True
    qualify_frequency_seconds: int = Field(default=60, ge=0, le=3600)
    options_status: str = "UNKNOWN"
    allowed_destinations: list[str] = Field(default_factory=list)
    codecs: list[str] = Field(default_factory=lambda: ["PCMU", "PCMA"])
    max_concurrent_calls: int = Field(default=5, ge=1, le=200)
    preferred: bool = False
    enabled: bool = True


class SipTrunkUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=100)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    transport: TransportProtocol | None = None
    auth_mode: SipAuthMode | None = None
    username: str | None = Field(default=None, max_length=120)
    password: str | None = Field(default=None, max_length=255)
    auth_username: str | None = Field(default=None, max_length=120)
    sip_domain: str | None = Field(default=None, max_length=255)
    outbound_proxy: str | None = Field(default=None, max_length=255)
    caller_id: str | None = Field(default=None, min_length=2, max_length=40)
    register_required: bool | None = None
    allowed_destinations: list[str] | None = None
    codecs: list[str] | None = None
    max_concurrent_calls: int | None = Field(default=None, ge=1, le=200)
    preferred: bool | None = None
    enabled: bool | None = None


class SipTrunkPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    provider_id: str
    host: str
    port: int
    transport: TransportProtocol
    auth_mode: SipAuthMode = SipAuthMode.USERPASS_REGISTRATION
    username: str
    auth_username: str | None = None
    sip_domain: str | None = None
    outbound_proxy: str | None = None
    caller_id: str
    register_required: bool = True
    qualify_frequency_seconds: int = Field(default=60, ge=0, le=3600)
    options_status: str = "UNKNOWN"
    allowed_destinations: list[str] = Field(default_factory=list)
    codecs: list[str] = Field(default_factory=lambda: ["PCMU", "PCMA"])
    max_concurrent_calls: int = 5
    preferred: bool = False
    enabled: bool = True
    has_password: bool = False
    status: ProviderConnectionStatus = ProviderConnectionStatus.DISCONNECTED
    last_error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InboundRouteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    phone_number: str = Field(min_length=2, max_length=40)
    sip_destination: str | None = Field(default=None, max_length=160)
    agent_id: str = Field(min_length=1, max_length=100)
    business_identity: str = Field(default="", max_length=120)
    working_hours_timezone: str = Field(default="Asia/Kolkata", max_length=64)
    working_hours_start: str = Field(default="00:00", pattern=r"^\d{2}:\d{2}$")
    working_hours_end: str = Field(default="23:59", pattern=r"^\d{2}:\d{2}$")
    fallback_destination: str | None = Field(default=None, max_length=120)
    enabled: bool = True


class InboundRouteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=100)
    phone_number: str | None = Field(default=None, min_length=2, max_length=40)
    sip_destination: str | None = Field(default=None, max_length=160)
    agent_id: str | None = Field(default=None, min_length=1, max_length=100)
    business_identity: str | None = Field(default=None, max_length=120)
    working_hours_timezone: str | None = Field(default=None, max_length=64)
    working_hours_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    working_hours_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    fallback_destination: str | None = Field(default=None, max_length=120)
    enabled: bool | None = None


class InboundRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    phone_number: str
    sip_destination: str | None = None
    agent_id: str
    business_identity: str = ""
    working_hours_timezone: str = "Asia/Kolkata"
    working_hours_start: str = "00:00"
    working_hours_end: str = "23:59"
    fallback_destination: str | None = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OutboundRouteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    provider_id: str = Field(min_length=1, max_length=100)
    trunk_id: str | None = Field(default=None, max_length=100)
    caller_id: str = Field(min_length=2, max_length=40)
    destination_pattern: str = Field(default="+91*", min_length=1, max_length=80)
    priority: int = Field(default=10, ge=1, le=100)
    require_dlt_template: bool = False
    dlt_entity_id: str | None = Field(default=None, max_length=64)
    dlt_template_id: str | None = Field(default=None, max_length=64)
    enabled: bool = True


class OutboundRouteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=100)
    provider_id: str | None = Field(default=None, min_length=1, max_length=100)
    trunk_id: str | None = Field(default=None, max_length=100)
    caller_id: str | None = Field(default=None, min_length=2, max_length=40)
    destination_pattern: str | None = Field(default=None, min_length=1, max_length=80)
    priority: int | None = Field(default=None, ge=1, le=100)
    require_dlt_template: bool | None = None
    dlt_entity_id: str | None = Field(default=None, max_length=64)
    dlt_template_id: str | None = Field(default=None, max_length=64)
    enabled: bool | None = None


class OutboundRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    provider_id: str
    trunk_id: str | None = None
    caller_id: str
    destination_pattern: str = "+91*"
    priority: int = 10
    require_dlt_template: bool = False
    dlt_entity_id: str | None = None
    dlt_template_id: str | None = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GsmGatewayCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    vendor: str = Field(default="SIP-Compatible Gateway", max_length=80)
    mode: str = Field(default="sip_trunk", pattern="^(sip_trunk|vendor_api)$")
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=5060, ge=1, le=65535)
    api_base_url: str | None = Field(default=None, max_length=300)
    username: str | None = Field(default=None, max_length=120)
    api_token: str | None = Field(default=None, max_length=255)
    max_channels: int = Field(default=4, ge=1, le=64)
    enabled: bool = True


class GsmGatewayPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    vendor: str
    mode: str
    host: str
    port: int
    api_base_url: str | None = None
    username: str | None = None
    max_channels: int = 4
    active_channels: int = 0
    signal_strength: int | None = None
    hardware_verified: bool = False
    has_api_token: bool = False
    enabled: bool = True
    status: ProviderConnectionStatus = ProviderConnectionStatus.DISCONNECTED
    last_error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TelephonySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_concurrent_calls: int = Field(default=5, ge=1, le=500)
    audio_buffer_ms: int = Field(default=60, ge=20, le=500)
    preferred_codecs: list[str] = Field(default_factory=lambda: ["PCMU", "PCMA"])
    connection_timeout_seconds: int = Field(default=10, ge=2, le=60)
    retry_limit: int = Field(default=2, ge=0, le=5)
    enforce_trai_dlt_compliance: bool = True
    require_caller_id_authorization: bool = True
    block_open_sip_relay: bool = True
    webhook_signature_required: bool = True


class TelephonyOverview(BaseModel):
    connected_providers: int
    total_providers: int
    registered_trunks: int
    total_trunks: int
    inbound_routes: int
    outbound_routes: int
    active_gateways: int
    total_gateways: int
    active_telephony_calls: int
    failed_telephony_calls: int
    available_channels: int
    real_telephony_ready: bool
    recent_errors: list[str] = Field(default_factory=list)


class DtmfActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: str = Field(min_length=1, max_length=100)
    digit: str = Field(min_length=1, max_length=2, pattern=r"^[0-9*#]$")
    action_type: str = Field(default="MENU_SELECT", pattern="^(MENU_SELECT|TRANSFER|OPT_OUT)$")
    target: str | None = Field(default=None, max_length=120)


class CredentialRotateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str | None = Field(default=None, min_length=1, max_length=255)
    ari_password: str | None = Field(default=None, min_length=1, max_length=255)
    webhook_secret: str | None = Field(default=None, min_length=1, max_length=255)


class ProviderToggleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
