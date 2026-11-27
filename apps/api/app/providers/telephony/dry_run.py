"""Dry-run TelephonyProvider for local workflow testing without real phone calls."""

from __future__ import annotations

from typing import Any
import uuid

from app.providers.telephony.base import CallInitiationResult, TelephonyProvider


class DryRunTelephonyProvider(TelephonyProvider):
    """Simulates call execution states locally; never initiates real phone calls."""

    provider_id = "dry_run"
    supports_real_calls = False

    def __init__(self) -> None:
        self._calls: dict[str, dict[str, Any]] = {}

    async def validate_configuration(self) -> tuple[bool, str]:
        return True, "Dry-run mode active: simulates execution locally without real calls."

    async def check_connection(self) -> dict[str, Any]:
        return {
            "provider": self.provider_id,
            "connected": True,
            "supports_real_calls": False,
            "message": "Dry-run simulator ready (no real phone calls will be placed).",
        }

    async def initiate_call(
        self,
        *,
        to_number: str,
        agent_id: str,
        campaign_id: str,
        idempotency_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> CallInitiationResult:
        call_id = f"dry_{uuid.uuid4().hex[:12]}"
        record = {
            "provider_call_id": call_id,
            "status": "COMPLETED",
            "is_dry_run": True,
            "campaign_id": campaign_id,
            "agent_id": agent_id,
            "idempotency_key": idempotency_key,
            "duration_seconds": 0,
        }
        self._calls[call_id] = record
        return CallInitiationResult(
            provider_call_id=call_id,
            status="COMPLETED",
            is_dry_run=True,
            duration_seconds=0,
            outcome="INFORMATION_REQUESTED",
            summary="Dry-run simulation completed (no actual telephone call occurred).",
        )

    async def get_call_status(self, provider_call_id: str) -> dict[str, Any]:
        return self._calls.get(provider_call_id, {"status": "UNKNOWN", "is_dry_run": True})

    async def terminate_call(self, provider_call_id: str) -> bool:
        if provider_call_id in self._calls:
            self._calls[provider_call_id]["status"] = "TERMINATED"
            return True
        return False

    async def get_call_details(self, provider_call_id: str) -> dict[str, Any]:
        return self._calls.get(provider_call_id, {})
