"""Backend Device Gateway services: Pairing, Auth, Registry, Heartbeat, Commands, and Mobile VoIP."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import secrets
from typing import Any
import uuid

from app.repositories.device_repository import DeviceRepository
from app.schemas.devices import (
    Device,
    DeviceCapabilityProfile,
    DeviceCommand,
    DeviceCommandCreate,
    DeviceEvent,
    DeviceEventType,
    DeviceHealthSnapshot,
    DeviceHeartbeatRequest,
    DevicePairRequest,
    DevicePairResponse,
    DevicePlatform,
    DeviceStatus,
    MobileVoIPSession,
    MobileVoIPSessionCreate,
    PairingCodeCreate,
    PairingCodePublic,
)
from app.schemas.live_calls import CallDirection, CallSessionStatus, CallSessionType
from app.services.live_calls_service import CallSessionService
from app.services.ws_manager import WebSocketManager, monitoring_ws_hub

logger = logging.getLogger(__name__)


class DeviceNotFoundError(LookupError):
    """Raised when a device, command, or VoIP session is not found."""


class DeviceAuthError(PermissionError):
    """Raised when device token authentication fails or device is revoked."""


class DevicePairingError(ValueError):
    """Raised when a pairing code is invalid, expired, or already used."""


class DeviceEventService:
    """Persists and broadcasts observed device events."""

    def __init__(self, repo: DeviceRepository, ws_hub: WebSocketManager = monitoring_ws_hub) -> None:
        self._repo = repo
        self._ws = ws_hub

    def emit(
        self,
        device_id: str,
        event_type: DeviceEventType,
        payload: dict[str, Any] | None = None,
    ) -> DeviceEvent:
        ev = DeviceEvent(
            event_id=f"devt_{uuid.uuid4().hex[:12]}",
            device_id=device_id,
            event_type=event_type,
            payload=payload or {},
        )
        self._repo.append_event(ev)
        self._ws.publish_nonblocking(
            {
                "type": "DEVICE_EVENT",
                "device_id": device_id,
                "event_type": event_type.value,
                "timestamp": ev.timestamp.isoformat(),
                "payload": ev.payload,
            }
        )
        return ev

    def list_events(self, device_id: str) -> list[DeviceEvent]:
        return self._repo.list_events(device_id)


class DeviceAuthenticationService:
    """Issues, verifies, rotates, and revokes per-device credentials."""

    def __init__(self, repo: DeviceRepository, events: DeviceEventService) -> None:
        self._repo = repo
        self._events = events

    def issue_token(self, device_id: str, ttl_days: int = 30) -> tuple[str, datetime]:
        raw_token = f"avd_{secrets.token_urlsafe(32)}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        self._repo.set_credential(device_id, raw_token, expires_at)
        return raw_token, expires_at

    def authenticate(self, device_id: str, token: str | None) -> Device:
        dev = self._repo.get_device(device_id)
        if dev is None:
            raise DeviceNotFoundError(f"Device '{device_id}' not found.")
        if dev.device_status == DeviceStatus.REVOKED:
            raise DeviceAuthError("Device has been revoked.")
        if not token:
            raise DeviceAuthError("Device bearer token is required.")
        cleaned = token.replace("Bearer ", "").strip()
        if not self._repo.verify_credential(device_id, cleaned):
            raise DeviceAuthError("Invalid or expired device token.")
        return dev

    def revoke_device(self, device_id: str) -> Device:
        dev = self._repo.get_device(device_id)
        if dev is None:
            raise DeviceNotFoundError(f"Device '{device_id}' not found.")
        self._repo.revoke_credential(device_id)
        updated = self._repo.save_device(dev.model_copy(update={"device_status": DeviceStatus.REVOKED}))
        self._events.emit(device_id, DeviceEventType.DEVICE_OFFLINE, {"reason": "revoked"})
        return updated


class DevicePairingService:
    """Manages short-lived, single-use pairing codes for Android & iPhone devices."""

    def __init__(
        self,
        repo: DeviceRepository,
        auth: DeviceAuthenticationService,
        events: DeviceEventService,
    ) -> None:
        self._repo = repo
        self._auth = auth
        self._events = events

    def create_pairing_code(self, req: PairingCodeCreate) -> PairingCodePublic:
        code = secrets.token_hex(4).upper()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=req.ttl_seconds)
        rec = PairingCodePublic(
            code=code,
            account_id=req.account_id,
            platform=req.platform,
            used=False,
            expires_at=expires_at,
        )
        codes = self._repo.list_pairing_codes()
        codes.append(rec)
        self._repo.save_pairing_codes(codes)
        return rec

    def pair_device(self, req: DevicePairRequest) -> DevicePairResponse:
        codes = self._repo.list_pairing_codes()
        now = datetime.now(timezone.utc)
        matched_idx: int | None = None
        for idx, c in enumerate(codes):
            if c.code == req.pairing_code.strip().upper():
                matched_idx = idx
                break
        if matched_idx is None:
            raise DevicePairingError("Invalid pairing code.")
        code_rec = codes[matched_idx]
        if code_rec.used:
            raise DevicePairingError("Pairing code has already been used.")
        if now >= code_rec.expires_at:
            raise DevicePairingError("Pairing code has expired.")

        # Mark single-use immediately
        codes[matched_idx] = code_rec.model_copy(update={"used": True})
        self._repo.save_pairing_codes(codes)

        default_caps = DeviceCapabilityProfile(
            platform=req.platform,
            cellular_call_initiation=req.platform == DevicePlatform.ANDROID,
            cellular_call_state=req.platform == DevicePlatform.ANDROID,
            cellular_audio_capture=False,
            cellular_audio_injection=False,
            cellular_audio_bridge_status="CELLULAR_AUDIO_BRIDGE_UNAVAILABLE",
            voip_supported=True,
            callkit_supported=req.platform == DevicePlatform.IOS,
            device_health=True,
            ai_call_ready=False,
        )
        caps = req.capability_profile or default_caps
        # Never allow claiming cellular audio capture/injection without verified hardware bridge
        caps = caps.model_copy(
            update={
                "cellular_audio_capture": False,
                "cellular_audio_injection": False,
                "cellular_audio_bridge_status": "CELLULAR_AUDIO_BRIDGE_UNAVAILABLE",
                "ai_call_ready": False,
            }
        )

        device_id = f"dev_{uuid.uuid4().hex[:10]}"
        device = Device(
            id=device_id,
            account_id=code_rec.account_id,
            device_name=req.device_name,
            platform=req.platform,
            platform_version=req.platform_version,
            app_version=req.app_version,
            device_status=DeviceStatus.ONLINE,
            capability_profile=caps,
            last_seen_at=now,
        )
        saved = self._repo.save_device(device)
        token, exp = self._auth.issue_token(device_id)
        self._events.emit(
            device_id,
            DeviceEventType.DEVICE_REGISTERED,
            {"platform": req.platform.value, "device_name": req.device_name},
        )
        return DevicePairResponse(device=saved, device_token=token, token_expires_at=exp)


class DeviceRegistryService:
    """Device lookup, listing, deletion, capabilities, health, heartbeat, and commands."""

    def __init__(self, repo: DeviceRepository, events: DeviceEventService) -> None:
        self._repo = repo
        self._events = events

    def list_devices(self) -> list[Device]:
        return self._repo.list_devices()

    def get_device(self, device_id: str) -> Device:
        dev = self._repo.get_device(device_id)
        if dev is None:
            raise DeviceNotFoundError(f"Device '{device_id}' not found.")
        return dev

    def delete_device(self, device_id: str) -> bool:
        return self._repo.delete_device(device_id)

    def get_health(self, device_id: str) -> DeviceHealthSnapshot:
        return self.get_device(device_id).health

    def get_capabilities(self, device_id: str) -> DeviceCapabilityProfile:
        return self.get_device(device_id).capability_profile

    def record_heartbeat(self, device_id: str, req: DeviceHeartbeatRequest) -> Device:
        dev = self.get_device(device_id)
        if dev.device_status == DeviceStatus.REVOKED:
            raise DeviceAuthError("Revoked device cannot send heartbeats.")
        caps = req.capability_profile or dev.capability_profile
        caps = caps.model_copy(
            update={
                "cellular_audio_capture": False,
                "cellular_audio_injection": False,
                "cellular_audio_bridge_status": "CELLULAR_AUDIO_BRIDGE_UNAVAILABLE",
            }
        )
        status_val = DeviceStatus.ONLINE if req.health.connected else DeviceStatus.DEGRADED
        if req.health.last_error:
            status_val = DeviceStatus.DEGRADED
        updated = self._repo.save_device(
            dev.model_copy(
                update={
                    "device_status": status_val,
                    "health": req.health,
                    "capability_profile": caps,
                    "last_seen_at": datetime.now(timezone.utc),
                }
            )
        )
        self._events.emit(
            device_id,
            DeviceEventType.HEARTBEAT_RECEIVED,
            {"network_type": req.health.network_type, "battery_percent": req.health.battery_percent},
        )
        return updated

    def enqueue_command(self, device_id: str, req: DeviceCommandCreate) -> DeviceCommand:
        dev = self.get_device(device_id)
        if dev.device_status == DeviceStatus.REVOKED:
            raise DeviceAuthError("Cannot send commands to a revoked device.")
        cmd = DeviceCommand(
            id=f"dcmd_{uuid.uuid4().hex[:10]}",
            device_id=device_id,
            command_type=req.command_type,
            payload=req.payload,
        )
        saved = self._repo.save_command(cmd)
        if req.command_type == "REQUEST_OUTBOUND_CALL":
            self._events.emit(device_id, DeviceEventType.CALL_REQUESTED, req.payload)
        return saved

    def get_command(self, device_id: str, command_id: str) -> DeviceCommand:
        self.get_device(device_id)
        for c in self._repo.list_commands(device_id):
            if c.id == command_id:
                return c
        raise DeviceNotFoundError(f"Command '{command_id}' not found for device '{device_id}'.")


class MobileVoIPService:
    """Manages AgentVoice VoIP sessions for mobile endpoints (linked to CallSessionService)."""

    def __init__(
        self,
        repo: DeviceRepository,
        registry: DeviceRegistryService,
        events: DeviceEventService,
        call_svc: CallSessionService,
    ) -> None:
        self._repo = repo
        self._registry = registry
        self._events = events
        self._calls = call_svc

    async def start_session(self, req: MobileVoIPSessionCreate) -> MobileVoIPSession:
        dev = self._registry.get_device(req.device_id)
        if dev.device_status == DeviceStatus.REVOKED:
            raise DeviceAuthError("Revoked device cannot start VoIP sessions.")

        direction = CallDirection.INBOUND if req.direction == "INBOUND" else CallDirection.OUTBOUND
        call_session = await self._calls.create_session(
            agent_id=req.agent_id,
            session_type=CallSessionType.TELEPHONY,
            direction=direction,
            provider=req.provider,
        )
        voip = MobileVoIPSession(
            id=f"mvoip_{uuid.uuid4().hex[:10]}",
            device_id=dev.id,
            agent_id=req.agent_id,
            call_session_id=call_session.id,
            direction=req.direction,
            call_source="AGENTVOICE_VOIP",
            status="ACTIVE",
            provider=req.provider,
        )
        saved = self._repo.save_voip_session(voip)
        self._events.emit(
            dev.id,
            DeviceEventType.VOIP_CONNECTED,
            {"voip_session_id": saved.id, "call_session_id": call_session.id},
        )
        return saved

    def get_session(self, session_id: str) -> MobileVoIPSession:
        for s in self._repo.list_voip_sessions():
            if s.id == session_id:
                return s
        raise DeviceNotFoundError(f"Mobile VoIP session '{session_id}' not found.")

    async def terminate_session(self, session_id: str) -> MobileVoIPSession:
        session = self.get_session(session_id)
        if session.call_session_id:
            try:
                await self._calls.end_session(
                    session.call_session_id,
                    status=CallSessionStatus.TERMINATED,
                    end_reason="Mobile VoIP session terminated",
                )
            except Exception:
                pass
        ended = self._repo.save_voip_session(
            session.model_copy(
                update={"status": "TERMINATED", "ended_at": datetime.now(timezone.utc)}
            )
        )
        self._events.emit(
            session.device_id,
            DeviceEventType.VOIP_DISCONNECTED,
            {"voip_session_id": session.id},
        )
        return ended
