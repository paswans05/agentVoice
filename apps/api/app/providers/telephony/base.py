"""Provider-independent TelephonyProvider interface and exceptions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class TelephonyProviderError(RuntimeError):
    """Base error for telephony provider operations."""


class TelephonyUnavailableError(TelephonyProviderError):
    """Raised when a real telephony provider is not configured or reachable."""


@dataclass(slots=True)
class CallInitiationResult:
    provider_call_id: str
    status: str
    is_dry_run: bool
    duration_seconds: int = 0
    outcome: str = "INFORMATION_REQUESTED"
    summary: str = ""


class TelephonyProvider(ABC):
    """Abstract telephony provider interface (real SIP/Asterisk implemented in Phase 9)."""

    provider_id: str = "base"
    supports_real_calls: bool = False

    @abstractmethod
    async def validate_configuration(self) -> tuple[bool, str]:
        """Validate provider credentials and configuration."""

    @abstractmethod
    async def check_connection(self) -> dict[str, Any]:
        """Check connectivity to the telephony provider."""

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

    @abstractmethod
    async def get_call_status(self, provider_call_id: str) -> dict[str, Any]:
        """Retrieve current call status."""

    @abstractmethod
    async def terminate_call(self, provider_call_id: str) -> bool:
        """Terminate an active call if supported."""

    @abstractmethod
    async def get_call_details(self, provider_call_id: str) -> dict[str, Any]:
        """Retrieve completed call details."""
