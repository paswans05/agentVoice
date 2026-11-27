"""Provider-independent TelephonyProvider interface, capabilities, and exceptions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class TelephonyProviderError(RuntimeError):
    """Base error for telephony provider operations."""


class TelephonyUnavailableError(TelephonyProviderError):
    """Raised when a real telephony provider is not configured or reachable."""


class TelephonyAuthError(TelephonyProviderError):
    """Raised when telephony provider authentication fails."""


class TelephonyMediaError(TelephonyProviderError):
    """Raised when audio/codec negotiation or media streaming fails."""


@dataclass(slots=True)
class ProviderCapabilities:
    """Verified capabilities supported by a telephony provider instance."""

    inbound: bool = False
    outbound: bool = False
    hold: bool = False
    transfer: bool = False
    recording: bool = False
    dtmf: bool = False
    supported_codecs: list[str] = field(default_factory=lambda: ["PCMU", "PCMA"])
    max_concurrent_calls: int = 10


@dataclass(slots=True)
class CallInitiationResult:
    provider_call_id: str
    status: str
    is_dry_run: bool
    duration_seconds: int = 0
    outcome: str = "INFORMATION_REQUESTED"
    summary: str = ""


class TelephonyProvider(ABC):
    """Abstract telephony provider interface for Asterisk, SIP trunks, GSM gateways, and dry-run."""

    provider_id: str = "base"
    supports_real_calls: bool = False

    def get_capabilities(self) -> ProviderCapabilities:
        """Return verified capability metadata for this provider."""
        return ProviderCapabilities()

    @abstractmethod
    async def validate_configuration(self) -> tuple[bool, str]:
        """Validate provider credentials and configuration."""

    async def connect(self) -> dict[str, Any]:
        """Establish connection or registration with the telephony provider."""
        return await self.check_connection()

    async def disconnect(self) -> dict[str, Any]:
        """Gracefully disconnect from the telephony provider."""
        return {"provider": self.provider_id, "connected": False, "status": "DISCONNECTED"}

    @abstractmethod
    async def check_connection(self) -> dict[str, Any]:
        """Check connectivity to the telephony provider."""

    async def health_check(self) -> dict[str, Any]:
        """Return detailed provider health status."""
        return await self.check_connection()

    async def register_endpoint(self, endpoint_id: str, config: dict[str, Any]) -> dict[str, Any]:
        """Register or verify a SIP/PJSIP endpoint if supported."""
        raise TelephonyUnavailableError(
            f"Provider '{self.provider_id}' does not support endpoint registration."
        )

    @abstractmethod
    async def initiate_call(
        self,
        *,
        to_number: str,
        agent_id: str,
        campaign_id: str,
        idempotency_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> CallInitiationResult:
        """Initiate an outbound call (or dry-run simulation)."""

    async def answer_inbound_call(
        self, provider_call_id: str, *, agent_id: str
    ) -> dict[str, Any]:
        """Answer an inbound call through the provider."""
        raise TelephonyUnavailableError(
            f"Provider '{self.provider_id}' does not support inbound call answering."
        )

    async def reject_call(self, provider_call_id: str, *, reason: str = "rejected") -> bool:
        """Reject an incoming call before answering."""
        raise TelephonyUnavailableError(
            f"Provider '{self.provider_id}' does not support call rejection."
        )

    @abstractmethod
    async def get_call_status(self, provider_call_id: str) -> dict[str, Any]:
        """Retrieve current call status."""

    @abstractmethod
    async def terminate_call(self, provider_call_id: str) -> bool:
        """Terminate an active call if supported."""

    async def hold_call(self, provider_call_id: str) -> bool:
        """Place an active call on hold if supported."""
        raise TelephonyUnavailableError(
            f"Provider '{self.provider_id}' does not support call hold."
        )

    async def resume_call(self, provider_call_id: str) -> bool:
        """Resume a held call if supported."""
        raise TelephonyUnavailableError(
            f"Provider '{self.provider_id}' does not support call resume."
        )

    async def transfer_call(self, provider_call_id: str, *, destination: str) -> bool:
        """Transfer an active call to a destination if supported."""
        raise TelephonyUnavailableError(
            f"Provider '{self.provider_id}' does not support call transfer."
        )

    async def send_dtmf(self, provider_call_id: str, *, digits: str) -> bool:
        """Send DTMF digits on an active call if supported."""
        raise TelephonyUnavailableError(
            f"Provider '{self.provider_id}' does not support DTMF."
        )

    async def handle_provider_event(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        """Normalize a raw provider event into agentVoice call event metadata."""
        return {"provider": self.provider_id, "raw_event": raw_event}

    @abstractmethod
    async def get_call_details(self, provider_call_id: str) -> dict[str, Any]:
        """Retrieve completed call details."""
