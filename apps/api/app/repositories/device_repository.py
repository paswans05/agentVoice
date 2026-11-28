"""StorageProvider repositories for Mobile Device Gateway, pairing codes, credentials, and VoIP."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import logging

from pydantic import ValidationError

from app.providers.storage import StorageProvider
from app.schemas.devices import (
    Device,
    DeviceCommand,
    DeviceEvent,
    MobileVoIPSession,
    PairingCodePublic,
    WebRTCSession,
)

logger = logging.getLogger(__name__)

DEVICES_STORE = "devices/devices_store.json"
PAIRING_CODES_STORE = "devices/pairing_codes.json"
COMMANDS_STORE = "devices/commands_store.json"
VOIP_SESSIONS_STORE = "devices/voip_sessions_store.json"
WEBRTC_SESSIONS_STORE = "devices/webrtc_sessions_store.json"
CREDENTIALS_STORE = "devices/device_credentials.json"
DEVICE_EVENTS_LOG = "devices/device_events.jsonl"


class DeviceRepository:
    """Persists registered devices, single-use pairing codes, hashed tokens, commands, and events."""

    def __init__(self, storage: StorageProvider, secret_salt: str) -> None:
        self._storage = storage
        self._salt = secret_salt

    def _hash_token(self, raw_token: str) -> str:
        return hmac.new(
            self._salt.encode("utf-8"),
            raw_token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    # --- Devices ---

    def list_devices(self) -> list[Device]:
        raw = self._storage.read_json(DEVICES_STORE, default=[]) or []
        items: list[Device] = []
        for row in raw:
            try:
                items.append(Device.model_validate(row))
            except ValidationError as exc:
                logger.warning("Skipping invalid device record: %s", exc)
        return items

    def get_device(self, device_id: str) -> Device | None:
        for d in self.list_devices():
            if d.id == device_id:
                return d
        return None

    def save_device(self, device: Device) -> Device:
        items = self.list_devices()
        for idx, existing in enumerate(items):
            if existing.id == device.id:
                updated = device.model_copy(update={"updated_at": datetime.now(timezone.utc)})
                items[idx] = updated
                self._storage.write_json(DEVICES_STORE, [d.model_dump(mode="json") for d in items])
                return updated
        items.append(device)
        self._storage.write_json(DEVICES_STORE, [d.model_dump(mode="json") for d in items])
        return device

    def delete_device(self, device_id: str) -> bool:
        items = self.list_devices()
        filtered = [d for d in items if d.id != device_id]
        if len(filtered) == len(items):
            return False
        self._storage.write_json(DEVICES_STORE, [d.model_dump(mode="json") for d in filtered])
        self.delete_credential(device_id)
        return True

    # --- Pairing Codes ---

    def list_pairing_codes(self) -> list[PairingCodePublic]:
        raw = self._storage.read_json(PAIRING_CODES_STORE, default=[]) or []
        return [PairingCodePublic.model_validate(r) for r in raw]

    def save_pairing_codes(self, codes: list[PairingCodePublic]) -> None:
        self._storage.write_json(PAIRING_CODES_STORE, [c.model_dump(mode="json") for c in codes])

    # --- Credentials (hashed per-device tokens) ---

    def set_credential(self, device_id: str, raw_token: str, expires_at: datetime) -> None:
        creds = self._storage.read_json(CREDENTIALS_STORE, default={}) or {}
        creds[device_id] = {
            "token_hash": self._hash_token(raw_token),
            "expires_at": expires_at.isoformat(),
            "revoked": False,
        }
        self._storage.write_json(CREDENTIALS_STORE, creds)

    def verify_credential(self, device_id: str, raw_token: str) -> bool:
        creds = self._storage.read_json(CREDENTIALS_STORE, default={}) or {}
        rec = creds.get(device_id)
        if not isinstance(rec, dict) or rec.get("revoked"):
            return False
        exp_str = rec.get("expires_at")
        if isinstance(exp_str, str):
            exp = datetime.fromisoformat(exp_str)
            if datetime.now(timezone.utc) >= exp:
                return False
        expected = rec.get("token_hash", "")
        return hmac.compare_digest(expected, self._hash_token(raw_token))

    def revoke_credential(self, device_id: str) -> None:
        creds = self._storage.read_json(CREDENTIALS_STORE, default={}) or {}
        if device_id in creds and isinstance(creds[device_id], dict):
            creds[device_id]["revoked"] = True
            self._storage.write_json(CREDENTIALS_STORE, creds)

    def delete_credential(self, device_id: str) -> None:
        creds = self._storage.read_json(CREDENTIALS_STORE, default={}) or {}
        if device_id in creds:
            creds.pop(device_id, None)
            self._storage.write_json(CREDENTIALS_STORE, creds)

    # --- Commands ---

    def list_commands(self, device_id: str | None = None) -> list[DeviceCommand]:
        raw = self._storage.read_json(COMMANDS_STORE, default=[]) or []
        cmds = [DeviceCommand.model_validate(r) for r in raw]
        if device_id:
            cmds = [c for c in cmds if c.device_id == device_id]
        return cmds

    def save_command(self, cmd: DeviceCommand) -> DeviceCommand:
        cmds = self.list_commands()
        for idx, existing in enumerate(cmds):
            if existing.id == cmd.id:
                cmds[idx] = cmd
                self._storage.write_json(COMMANDS_STORE, [c.model_dump(mode="json") for c in cmds])
                return cmd
        cmds.append(cmd)
        self._storage.write_json(COMMANDS_STORE, [c.model_dump(mode="json") for c in cmds])
        return cmd

    # --- VoIP Sessions ---

    def list_voip_sessions(self) -> list[MobileVoIPSession]:
        raw = self._storage.read_json(VOIP_SESSIONS_STORE, default=[]) or []
        return [MobileVoIPSession.model_validate(r) for r in raw]

    def save_voip_session(self, session: MobileVoIPSession) -> MobileVoIPSession:
        items = self.list_voip_sessions()
        for idx, existing in enumerate(items):
            if existing.id == session.id:
                items[idx] = session
                self._storage.write_json(VOIP_SESSIONS_STORE, [s.model_dump(mode="json") for s in items])
                return session
        items.append(session)
        self._storage.write_json(VOIP_SESSIONS_STORE, [s.model_dump(mode="json") for s in items])
        return session

    # --- WebRTC Sessions ---

    def list_webrtc_sessions(self) -> list[WebRTCSession]:
        raw = self._storage.read_json(WEBRTC_SESSIONS_STORE, default=[]) or []
        return [WebRTCSession.model_validate(r) for r in raw]

    def save_webrtc_session(self, session: WebRTCSession) -> WebRTCSession:
        items = self.list_webrtc_sessions()
        for idx, existing in enumerate(items):
            if existing.id == session.id:
                items[idx] = session
                self._storage.write_json(WEBRTC_SESSIONS_STORE, [s.model_dump(mode="json") for s in items])
                return session
        items.append(session)
        self._storage.write_json(WEBRTC_SESSIONS_STORE, [s.model_dump(mode="json") for s in items])
        return session

    # --- Events ---

    def append_event(self, event: DeviceEvent) -> DeviceEvent:
        self._storage.append_jsonl(DEVICE_EVENTS_LOG, event.model_dump(mode="json"))
        return event

    def list_events(self, device_id: str) -> list[DeviceEvent]:
        rows = self._storage.read_jsonl(DEVICE_EVENTS_LOG)
        items = [DeviceEvent.model_validate(r) for r in rows if r.get("device_id") == device_id]
        items.sort(key=lambda e: e.timestamp, reverse=True)
        return items
