"""Authorized GSM Gateway adapter (SIP trunk or documented vendor API)."""

from __future__ import annotations

import logging
from typing import Any
import uuid

import httpx

from app.providers.telephony.base import (
    CallInitiationResult,
    ProviderCapabilities,
    TelephonyProvider,
    TelephonyUnavailableError,
)
from app.schemas.telephony import GsmGatewayPublic, ProviderConnectionStatus

logger = logging.getLogger(__name__)


class GsmGatewayProvider(TelephonyProvider):
    """Adapter for authorized GSM gateways exposed via SIP trunk or documented HTTP API."""

    provider_id = "gsm_gateway"
    supports_real_calls = True

    def __init__(
        self,
        gateway: GsmGatewayPublic,
        api_token: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._gw = gateway
        self._token = api_token or ""
        self._transport = transport
        self._calls: dict[str, dict[str, Any]] = {}

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            inbound=True,
            outbound=True,
            hold=False,
            transfer=False,
            recording=False,
            dtmf=True,
            supported_codecs=["PCMU", "PCMA"],
            max_concurrent_calls=self._gw.max_channels,
        )

    async def validate_configuration(self) -> tuple[bool, str]:
        if not self._gw.host:
            return False, "GSM gateway host is required."
        if self._gw.mode == "vendor_api" and not self._gw.api_base_url:
            return False, "Documented vendor API base URL is required for vendor_api mode."
        return True, "GSM gateway configuration valid."

    async def check_connection(self) -> dict[str, Any]:
        valid, msg = await self.validate_configuration()
        if not valid:
            return {
                "provider": self.provider_id,
                "connected": False,
                "hardware_verified": False,
                "status": ProviderConnectionStatus.INCOMPLETE.value,
                "message": msg,
            }
        if self._gw.mode == "sip_trunk":
            return {
                "provider": self.provider_id,
                "connected": False,
                "hardware_verified": False,
                "status": ProviderConnectionStatus.DISCONNECTED.value,
                "message": "SIP-trunk GSM gateway must be verified via Asterisk PJSIP trunk registration.",
            }
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            async with httpx.AsyncClient(
                base_url=str(self._gw.api_base_url).rstrip("/"),
                headers=headers,
                timeout=8.0,
                transport=self._transport,
            ) as client:
                resp = await client.get("/status")
            if resp.status_code in (401, 403):
                return {
                    "provider": self.provider_id,
                    "connected": False,
                    "hardware_verified": False,
                    "status": ProviderConnectionStatus.AUTH_FAILED.value,
                    "message": "GSM gateway API authentication failed.",
                }
            if resp.status_code >= 400:
                return {
                    "provider": self.provider_id,
                    "connected": False,
                    "hardware_verified": False,
                    "status": ProviderConnectionStatus.UNAVAILABLE.value,
                    "message": f"GSM gateway returned HTTP {resp.status_code}.",
                }
            data = resp.json() if resp.content else {}
            return {
                "provider": self.provider_id,
                "connected": True,
                "hardware_verified": True,
                "status": ProviderConnectionStatus.CONNECTED.value,
                "active_channels": int(data.get("active_channels", 0)),
                "signal_strength": data.get("signal_strength"),
                "message": "GSM gateway API reachable.",
            }
        except httpx.RequestError as exc:
            logger.warning("GSM gateway connection error: %s", type(exc).__name__)
            return {
                "provider": self.provider_id,
                "connected": False,
                "hardware_verified": False,
                "status": ProviderConnectionStatus.NETWORK_ERROR.value,
                "message": "GSM gateway hardware unreachable (physical hardware not verified).",
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
        status_res = await self.check_connection()
        if not status_res.get("connected"):
            raise TelephonyUnavailableError(str(status_res.get("message") or "GSM gateway unavailable."))
        call_id = f"gsm_{uuid.uuid4().hex[:12]}"
        self._calls[call_id] = {
            "provider_call_id": call_id,
            "status": "INITIATING",
            "agent_id": agent_id,
            "campaign_id": campaign_id,
        }
        return CallInitiationResult(
            provider_call_id=call_id,
            status="INITIATING",
            is_dry_run=False,
            summary="Call initiated via authorized GSM gateway.",
        )

    async def get_call_status(self, provider_call_id: str) -> dict[str, Any]:
        return self._calls.get(provider_call_id, {"status": "UNKNOWN"})

    async def terminate_call(self, provider_call_id: str) -> bool:
        if provider_call_id in self._calls:
            self._calls[provider_call_id]["status"] = "TERMINATED"
            return True
        return False

    async def get_call_details(self, provider_call_id: str) -> dict[str, Any]:
        return self._calls.get(provider_call_id, {})
