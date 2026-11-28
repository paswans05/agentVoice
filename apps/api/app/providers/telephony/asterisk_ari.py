"""Asterisk REST Interface (ARI) & PJSIP TelephonyProvider adapter."""

from __future__ import annotations

import logging
import time
from typing import Any
import uuid

import httpx

from app.providers.telephony.base import (
    CallInitiationResult,
    ProviderCapabilities,
    TelephonyAuthError,
    TelephonyProvider,
    TelephonyProviderError,
    TelephonyUnavailableError,
)
from app.schemas.live_calls import CallEventType
from app.schemas.telephony import ProviderConnectionStatus, TelephonyProviderPublic

logger = logging.getLogger(__name__)

_ARI_EVENT_MAP: dict[str, CallEventType] = {
    "StasisStart": CallEventType.CALL_STARTED,
    "ChannelStateChange": CallEventType.CALL_ANSWERED,
    "ChannelDtmfReceived": CallEventType.SPEECH_DETECTED,
    "ChannelHangupRequest": CallEventType.CALL_ENDED,
    "ChannelDestroyed": CallEventType.CALL_DISCONNECTED,
    "ChannelHold": CallEventType.CALL_ON_HOLD,
    "ChannelUnhold": CallEventType.CALL_RESUMED,
}


class AsteriskARIProvider(TelephonyProvider):
    """Real Asterisk PBX adapter using ARI over HTTP/TLS and PJSIP endpoints."""

    provider_id = "asterisk"
    supports_real_calls = True

    def __init__(
        self,
        config: TelephonyProviderPublic,
        ari_password: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._cfg = config
        self._ari_password = ari_password or ""
        self._transport = transport
        self._channels: dict[str, dict[str, Any]] = {}

    def _base_url(self) -> str:
        if self._cfg.ari_base_url:
            return self._cfg.ari_base_url.rstrip("/")
        scheme = "https" if self._cfg.use_tls else "http"
        return f"{scheme}://{self._cfg.host}:{self._cfg.port}/ari"

    def _client(self) -> httpx.AsyncClient:
        auth = None
        if self._cfg.ari_username and self._ari_password:
            auth = httpx.BasicAuth(self._cfg.ari_username, self._ari_password)
        return httpx.AsyncClient(
            base_url=self._base_url(),
            auth=auth,
            timeout=self._cfg.connection_timeout_seconds,
            verify=self._cfg.use_tls,
            transport=self._transport,
        )

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            inbound=True,
            outbound=True,
            hold=True,
            transfer=True,
            recording=False,
            dtmf=True,
            supported_codecs=list(self._cfg.supported_codecs),
            max_concurrent_calls=self._cfg.max_concurrent_calls,
        )

    async def validate_configuration(self) -> tuple[bool, str]:
        if not self._cfg.host and not self._cfg.ari_base_url:
            return False, "Asterisk host or ARI base URL is required."
        if not self._cfg.ari_username or not self._ari_password:
            return False, "Asterisk ARI username and password are required."
        if not self._cfg.caller_id:
            return False, "Authorized caller_id is required."
        return True, "Asterisk ARI configuration is complete."

    async def check_connection(self) -> dict[str, Any]:
        valid, msg = await self.validate_configuration()
        if not valid:
            return {
                "provider": self.provider_id,
                "connected": False,
                "status": ProviderConnectionStatus.INCOMPLETE.value,
                "supports_real_calls": True,
                "message": msg,
            }
        started = time.monotonic()
        try:
            async with self._client() as client:
                resp = await client.get("/asterisk/info")
            latency_ms = int((time.monotonic() - started) * 1000)
            if resp.status_code in (401, 403):
                return {
                    "provider": self.provider_id,
                    "connected": False,
                    "status": ProviderConnectionStatus.AUTH_FAILED.value,
                    "supports_real_calls": True,
                    "latency_ms": latency_ms,
                    "message": "Asterisk ARI authentication failed.",
                }
            if resp.status_code >= 400:
                return {
                    "provider": self.provider_id,
                    "connected": False,
                    "status": ProviderConnectionStatus.UNAVAILABLE.value,
                    "supports_real_calls": True,
                    "latency_ms": latency_ms,
                    "message": f"Asterisk ARI returned HTTP {resp.status_code}.",
                }
            info = resp.json() if resp.content else {}
            return {
                "provider": self.provider_id,
                "connected": True,
                "status": ProviderConnectionStatus.CONNECTED.value,
                "supports_real_calls": True,
                "latency_ms": latency_ms,
                "asterisk_version": info.get("system", {}).get("version"),
                "message": "Connected to Asterisk ARI.",
            }
        except httpx.TimeoutException:
            return {
                "provider": self.provider_id,
                "connected": False,
                "status": ProviderConnectionStatus.NETWORK_ERROR.value,
                "supports_real_calls": True,
                "message": "Asterisk ARI connection timed out.",
            }
        except httpx.RequestError as exc:
            logger.warning("Asterisk ARI network error: %s", type(exc).__name__)
            return {
                "provider": self.provider_id,
                "connected": False,
                "status": ProviderConnectionStatus.NETWORK_ERROR.value,
                "supports_real_calls": True,
                "message": "Unable to reach Asterisk ARI endpoint.",
            }

    async def register_endpoint(self, endpoint_id: str, config: dict[str, Any]) -> dict[str, Any]:
        async with self._client() as client:
            resp = await client.get(f"/endpoints/PJSIP/{endpoint_id}")
        if resp.status_code in (401, 403):
            raise TelephonyAuthError("Asterisk ARI authentication failed.")
        if resp.status_code >= 400:
            raise TelephonyUnavailableError(f"PJSIP endpoint '{endpoint_id}' not found.")
        return resp.json()

    async def initiate_call(
        self,
        *,
        to_number: str,
        agent_id: str,
        campaign_id: str,
        idempotency_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> CallInitiationResult:
        valid, msg = await self.validate_configuration()
        if not valid:
            raise TelephonyUnavailableError(msg)

        channel_id = f"ast_{uuid.uuid4().hex[:12]}"
        trunk_prefix = (metadata or {}).get("endpoint_prefix") or "PJSIP"
        endpoint = f"{trunk_prefix}/{to_number}"
        payload = {
            "endpoint": endpoint,
            "app": self._cfg.ari_app,
            "callerId": self._cfg.caller_id or "",
            "channelId": channel_id,
            "variables": {
                "AGENTVOICE_AGENT_ID": agent_id,
                "AGENTVOICE_CAMPAIGN_ID": campaign_id,
                "AGENTVOICE_IDEMPOTENCY_KEY": idempotency_key,
            },
        }
        try:
            async with self._client() as client:
                resp = await client.post("/channels", json=payload)
        except httpx.RequestError as exc:
            raise TelephonyUnavailableError("Asterisk ARI unreachable during call initiation.") from exc

        if resp.status_code in (401, 403):
            raise TelephonyAuthError("Asterisk ARI rejected credentials during call initiation.")
        if resp.status_code >= 400:
            raise TelephonyProviderError(f"Asterisk ARI channel creation failed ({resp.status_code}).")

        data = resp.json() if resp.content else {}
        actual_id = str(data.get("id") or channel_id)
        self._channels[actual_id] = {
            "provider_call_id": actual_id,
            "status": "INITIATING",
            "is_dry_run": False,
            "agent_id": agent_id,
            "campaign_id": campaign_id,
        }
        return CallInitiationResult(
            provider_call_id=actual_id,
            status="INITIATING",
            is_dry_run=False,
            summary="Outbound channel created via Asterisk ARI.",
        )

    async def answer_inbound_call(self, provider_call_id: str, *, agent_id: str) -> dict[str, Any]:
        async with self._client() as client:
            resp = await client.post(f"/channels/{provider_call_id}/answer")
        if resp.status_code in (401, 403):
            raise TelephonyAuthError("Asterisk ARI authentication failed.")
        if resp.status_code >= 400:
            raise TelephonyProviderError(f"Failed to answer channel '{provider_call_id}'.")
        self._channels[provider_call_id] = {
            "provider_call_id": provider_call_id,
            "status": "ACTIVE",
            "agent_id": agent_id,
        }
        return {"provider_call_id": provider_call_id, "status": "ACTIVE", "agent_id": agent_id}

    async def reject_call(self, provider_call_id: str, *, reason: str = "declined") -> bool:
        async with self._client() as client:
            resp = await client.delete(f"/channels/{provider_call_id}", params={"reason": reason})
        return resp.status_code < 400

    async def terminate_call(self, provider_call_id: str) -> bool:
        async with self._client() as client:
            resp = await client.delete(f"/channels/{provider_call_id}")
        if resp.status_code < 400:
            if provider_call_id in self._channels:
                self._channels[provider_call_id]["status"] = "TERMINATED"
            return True
        return False

    async def hold_call(self, provider_call_id: str) -> bool:
        async with self._client() as client:
            resp = await client.post(f"/channels/{provider_call_id}/hold")
        return resp.status_code < 400

    async def resume_call(self, provider_call_id: str) -> bool:
        async with self._client() as client:
            resp = await client.delete(f"/channels/{provider_call_id}/hold")
        return resp.status_code < 400

    async def transfer_call(self, provider_call_id: str, *, destination: str) -> bool:
        async with self._client() as client:
            resp = await client.post(
                f"/channels/{provider_call_id}/redirect",
                params={"endpoint": destination},
            )
        return resp.status_code < 400

    async def send_dtmf(self, provider_call_id: str, *, digits: str) -> bool:
        async with self._client() as client:
            resp = await client.post(
                f"/channels/{provider_call_id}/dtmf",
                params={"dtmf": digits},
            )
        return resp.status_code < 400

    async def get_call_status(self, provider_call_id: str) -> dict[str, Any]:
        return self._channels.get(provider_call_id, {"provider_call_id": provider_call_id, "status": "UNKNOWN"})

    async def get_call_details(self, provider_call_id: str) -> dict[str, Any]:
        return self._channels.get(provider_call_id, {})

    async def handle_provider_event(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        ari_type = str(raw_event.get("type") or "")
        channel = raw_event.get("channel") if isinstance(raw_event.get("channel"), dict) else {}
        channel_id = str(channel.get("id") or raw_event.get("channel_id") or "")
        normalized_type = _ARI_EVENT_MAP.get(ari_type, CallEventType.CALL_WARNING)
        return {
            "provider": self.provider_id,
            "ari_event_type": ari_type,
            "normalized_event_type": normalized_type,
            "provider_call_id": channel_id,
            "caller_number": (channel.get("caller") or {}).get("number"),
            "destination_number": (channel.get("dialplan") or {}).get("exten"),
            "digit": raw_event.get("digit"),
        }

    async def list_pjsip_endpoints(self) -> list[dict[str, Any]]:
        """Query Asterisk ARI for PJSIP endpoints and registration states."""
        try:
            async with self._client() as client:
                resp = await client.get("/endpoints/PJSIP")
        except httpx.RequestError as exc:
            raise TelephonyUnavailableError(f"Asterisk ARI unreachable: {type(exc).__name__}") from exc
        if resp.status_code in (401, 403):
            raise TelephonyAuthError("Asterisk ARI authentication failed.")
        if resp.status_code >= 400:
            raise TelephonyProviderError(f"Failed to list PJSIP endpoints (HTTP {resp.status_code}).")
        data = resp.json()
        return data if isinstance(data, list) else []

    async def list_active_channels(self) -> list[dict[str, Any]]:
        """Query Asterisk ARI for currently active channels."""
        try:
            async with self._client() as client:
                resp = await client.get("/channels")
        except httpx.RequestError as exc:
            raise TelephonyUnavailableError(f"Asterisk ARI unreachable: {type(exc).__name__}") from exc
        if resp.status_code in (401, 403):
            raise TelephonyAuthError("Asterisk ARI authentication failed.")
        if resp.status_code >= 400:
            raise TelephonyProviderError(f"Failed to list active ARI channels (HTTP {resp.status_code}).")
        data = resp.json()
        return data if isinstance(data, list) else []

    async def originate_internal_call(
        self,
        *,
        from_extension: str,
        to_extension: str,
        mode: str = "human",
        agent_id: str | None = None,
        channel_id: str | None = None,
        context: str = "from-internal",
    ) -> dict[str, Any]:
        """Originate an internal PJSIP or Stasis AI call via Asterisk ARI."""
        cid = channel_id or f"int_{uuid.uuid4().hex[:12]}"
        payload: dict[str, Any] = {
            "endpoint": f"PJSIP/{from_extension}",
            "callerId": from_extension,
            "channelId": cid,
            "variables": {
                "AGENTVOICE_MODE": mode,
                "AGENTVOICE_FROM_EXT": from_extension,
                "AGENTVOICE_TO_EXT": to_extension,
                **({"AGENTVOICE_AGENT_ID": agent_id} if agent_id else {}),
            },
        }
        if mode == "ai" or to_extension == "700":
            payload["app"] = self._cfg.ari_app
            payload["appArgs"] = f"ai,{from_extension},{agent_id or ''}"
        else:
            payload["context"] = context
            payload["extension"] = to_extension
            payload["priority"] = 1

        try:
            async with self._client() as client:
                resp = await client.post("/channels", json=payload)
        except httpx.TimeoutException as exc:
            raise TelephonyUnavailableError("Asterisk ARI request timed out.") from exc
        except httpx.RequestError as exc:
            raise TelephonyUnavailableError(f"Asterisk ARI unreachable: {type(exc).__name__}") from exc

        if resp.status_code in (401, 403):
            raise TelephonyAuthError("Asterisk ARI authentication failed.")
        if resp.status_code >= 400:
            raise TelephonyProviderError(f"ARI internal origination failed (HTTP {resp.status_code}).")
        body = resp.json() if resp.content else {}
        resolved_id = str(body.get("id") or cid)
        self._channels[resolved_id] = {
            "provider_call_id": resolved_id,
            "from_extension": from_extension,
            "to_extension": to_extension,
            "mode": mode,
            "status": "INITIATING",
        }
        return {"channel_id": resolved_id, "raw": body}

    async def create_external_media_bridge(
        self,
        *,
        channel_id: str,
        external_host: str,
        format_name: str = "ulaw",
    ) -> dict[str, str]:
        """Create a mixing ARI bridge and attach an ExternalMedia UDP channel for AI audio."""
        bridge_id = f"br_{uuid.uuid4().hex[:12]}"
        ext_chan_id = f"ext_{uuid.uuid4().hex[:12]}"
        async with self._client() as client:
            br_resp = await client.post(
                "/bridges",
                params={"type": "mixing", "bridgeId": bridge_id, "name": f"agentvoice-{channel_id}"},
            )
            if br_resp.status_code >= 400:
                raise TelephonyProviderError(f"Failed to create ARI bridge (HTTP {br_resp.status_code}).")

            em_resp = await client.post(
                "/channels/externalMedia",
                params={
                    "app": self._cfg.ari_app,
                    "external_host": external_host,
                    "format": format_name,
                    "channelId": ext_chan_id,
                    "encapsulation": "rtp",
                    "transport": "udp",
                    "direction": "both",
                },
            )
            if em_resp.status_code >= 400:
                await client.delete(f"/bridges/{bridge_id}")
                raise TelephonyProviderError(
                    f"Failed to create ARI ExternalMedia channel (HTTP {em_resp.status_code})."
                )

            for cid in (channel_id, ext_chan_id):
                add_resp = await client.post(f"/bridges/{bridge_id}/addChannel", params={"channel": cid})
                if add_resp.status_code >= 400:
                    raise TelephonyProviderError(f"Failed to add channel {cid} to bridge {bridge_id}.")

        return {"bridge_id": bridge_id, "external_media_channel_id": ext_chan_id}

    async def destroy_bridge(self, bridge_id: str) -> bool:
        """Tear down an ARI mixing bridge on call termination."""
        async with self._client() as client:
            resp = await client.delete(f"/bridges/{bridge_id}")
        return resp.status_code < 400
