"""Internal Asterisk 23 SIP/WebRTC calling service and external gateway guard."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
import uuid

from app.providers.storage import StorageProvider
from app.providers.telephony.asterisk_ari import AsteriskARIProvider
from app.providers.telephony.base import (
    TelephonyProviderError,
    TelephonyUnavailableError,
)
from app.repositories.telephony_repository import TelephonyRepository
from app.schemas.internal_calls import (
    InternalCallDialRequest,
    InternalCallMode,
    InternalCallRecord,
    InternalCallsHealth,
    InternalCallStatus,
    InternalExtension,
)
from app.schemas.live_calls import (
    CallDirection,
    CallEventType,
    CallSessionStatus,
    CallSessionType,
)
from app.schemas.telephony import (
    ProviderConnectionStatus,
    TelephonyProviderPublic,
    TelephonyProviderType,
)
from app.services.live_calls_service import CallSessionService
from app.services.telephony_service import TelephonyManagementService

logger = logging.getLogger(__name__)

_INTERNAL_EXTENSIONS: tuple[tuple[str, str, str, bool], ...] = (
    ("1001", "Extension 1001 (UDP SIP)", "UDP", False),
    ("1002", "Extension 1002 (UDP SIP)", "UDP", False),
    ("1001-ws", "Extension 1001 (WebRTC Browser)", "WS", True),
    ("1002-ws", "Extension 1002 (WebRTC Browser)", "WS", True),
    ("600", "Echo Test (600)", "INTERNAL", False),
    ("700", "AI Voice Assistant (700)", "INTERNAL", False),
)

_EXTERNAL_NUMBER_RE = re.compile(r"^(\+|00|\d{7,})")
_INTERNAL_STORE = "internal_calls/calls.json"
_INTERNAL_HISTORY = "internal_calls/calls.jsonl"


class ExternalTelephonyNotConfiguredError(Exception):
    """Raised when external PSTN dialing is attempted without an authorized trunk/gateway."""

    def __init__(self, message: str = "EXTERNAL_TELEPHONY_NOT_CONFIGURED: External telephony is not configured.") -> None:
        super().__init__(message)


class InternalCallNotFoundError(Exception):
    """Raised when an internal call ID is not found."""

    def __init__(self, call_id: str) -> None:
        super().__init__(f"Internal call '{call_id}' was not found.")


class DuplicateInternalCallError(Exception):
    """Raised when an identical active internal call is already running."""


class ExternalGatewayGuard:
    """Phase 8 guard separating internal SIP extensions from external PSTN trunks/gateways."""

    @staticmethod
    def is_external_destination(destination: str) -> bool:
        dest = destination.strip()
        if dest in {"1001", "1002", "1001-ws", "1002-ws", "600", "700"}:
            return False
        if re.fullmatch(r"9\d{3}", dest):
            return False
        return bool(_EXTERNAL_NUMBER_RE.match(dest))

    @staticmethod
    def has_authorized_external_gateway(repo: TelephonyRepository) -> bool:
        providers = repo.providers.list_all()
        trunks = repo.trunks.list_all()
        connected_trunk = any(
            p.enabled
            and p.status == ProviderConnectionStatus.CONNECTED
            and p.provider_type in (TelephonyProviderType.SIP_TRUNK, TelephonyProviderType.GSM_GATEWAY)
            for p in providers
        )
        return connected_trunk or any(t.enabled for t in trunks)


class InternalCallsService:
    """Manages internal Asterisk 23 extensions, call origination, tracking, and history."""

    def __init__(
        self,
        storage: StorageProvider,
        telephony_repo: TelephonyRepository,
        telephony_mgmt: TelephonyManagementService,
        call_sessions: CallSessionService,
    ) -> None:
        self._storage = storage
        self._repo = telephony_repo
        self._mgmt = telephony_mgmt
        self._calls = call_sessions

    def _load_records(self) -> list[InternalCallRecord]:
        raw = self._storage.read_json(_INTERNAL_STORE, default=[])
        if not isinstance(raw, list):
            return []
        return [InternalCallRecord.model_validate(item) for item in raw]

    def _save_records(self, records: list[InternalCallRecord]) -> None:
        self._storage.write_json(
            _INTERNAL_STORE,
            [r.model_dump(mode="json") for r in records],
        )

    def _resolve_asterisk_provider(self) -> tuple[TelephonyProviderPublic, AsteriskARIProvider] | None:
        providers = self._repo.providers.list_all()
        for p in providers:
            if p.enabled and p.provider_type == TelephonyProviderType.ASTERISK:
                adapter = self._mgmt._build_provider_adapter(p)
                if isinstance(adapter, AsteriskARIProvider):
                    return p, adapter
        return None

    async def list_extensions(self) -> list[InternalExtension]:
        resolved = self._resolve_asterisk_provider()
        live_map: dict[str, dict] = {}
        if resolved is not None:
            _, adapter = resolved
            try:
                endpoints = await adapter.list_pjsip_endpoints()
                for ep in endpoints:
                    res_name = str(ep.get("resource") or "")
                    if res_name:
                        live_map[res_name] = ep
            except TelephonyProviderError as exc:
                logger.warning("Unable to query PJSIP endpoints from ARI: %s", exc)

        result: list[InternalExtension] = []
        for ext, label, transport, webrtc in _INTERNAL_EXTENSIONS:
            ep = live_map.get(ext)
            state = str(ep.get("state") or "offline").lower() if ep else (
                "available" if transport == "INTERNAL" and resolved is not None else "offline"
            )
            chans = ep.get("channel_ids") if ep and isinstance(ep.get("channel_ids"), list) else []
            registered = state in ("online", "available")
            result.append(
                InternalExtension(
                    extension=ext,
                    label=label,
                    transport=transport,
                    webrtc_enabled=webrtc,
                    registered=registered,
                    state=state,
                    active_channels=len(chans),
                )
            )
        return result

    async def get_health(self) -> InternalCallsHealth:
        resolved = self._resolve_asterisk_provider()
        ext_configured = ExternalGatewayGuard.has_authorized_external_gateway(self._repo)
        active = self.list_active_calls()
        if resolved is None:
            return InternalCallsHealth(
                ari_connected=False,
                active_calls=len(active),
                external_telephony_configured=ext_configured,
                message="No enabled Asterisk ARI provider is configured.",
            )
        prov, adapter = resolved
        conn = await adapter.check_connection()
        exts = await self.list_extensions()
        reg_count = sum(1 for e in exts if e.registered and e.transport != "INTERNAL")
        return InternalCallsHealth(
            ari_connected=bool(conn.get("connected")),
            provider_id=prov.id,
            provider_name=prov.name,
            asterisk_version=conn.get("asterisk_version"),
            registered_extensions=reg_count,
            active_calls=len(active),
            external_telephony_configured=ext_configured,
            message=str(conn.get("message") or ""),
        )

    def list_active_calls(self) -> list[InternalCallRecord]:
        return [
            r
            for r in self._load_records()
            if r.status in (InternalCallStatus.INITIATING, InternalCallStatus.RINGING, InternalCallStatus.ACTIVE)
        ]

    def list_history(self, limit: int = 50) -> list[InternalCallRecord]:
        records = self._load_records()
        records.sort(key=lambda r: r.started_at, reverse=True)
        return records[:limit]

    def get_call(self, call_id: str) -> InternalCallRecord:
        for r in self._load_records():
            if r.call_id == call_id:
                return r
        raise InternalCallNotFoundError(call_id)

    async def dial(self, req: InternalCallDialRequest) -> InternalCallRecord:
        to_ext = req.to_extension.strip()
        from_ext = req.from_extension.strip()

        # Phase 8: Block external PSTN dialing unless authorized SIP trunk / GSM gateway exists
        if ExternalGatewayGuard.is_external_destination(to_ext):
            if not ExternalGatewayGuard.has_authorized_external_gateway(self._repo):
                raise ExternalTelephonyNotConfiguredError(
                    "EXTERNAL_TELEPHONY_NOT_CONFIGURED: External PSTN calling requires an authorized SIP trunk or GSM gateway. Use internal extensions (1001, 1002, 600, 700)."
                )

        records = self._load_records()
        # Duplicate / idempotency protection
        for existing in records:
            if req.idempotency_key and existing.idempotency_key == req.idempotency_key:
                return existing
            if (
                existing.status in (InternalCallStatus.INITIATING, InternalCallStatus.RINGING, InternalCallStatus.ACTIVE)
                and existing.from_extension == from_ext
                and existing.to_extension == to_ext
            ):
                raise DuplicateInternalCallError(
                    f"An active internal call from {from_ext} to {to_ext} is already in progress ({existing.call_id})."
                )

        resolved = self._resolve_asterisk_provider()
        if resolved is None:
            raise TelephonyUnavailableError("No enabled Asterisk ARI provider is configured.")
        prov, adapter = resolved

        mode = req.mode
        if to_ext == "600":
            mode = InternalCallMode.ECHO
        elif to_ext == "700":
            mode = InternalCallMode.AI

        call_id = f"icall_{uuid.uuid4().hex[:12]}"
        orig = await adapter.originate_internal_call(
            from_extension=from_ext,
            to_extension=to_ext,
            mode=mode.value,
            agent_id=req.agent_id,
            channel_id=call_id,
        )
        channel_id = orig["channel_id"]

        live_sess = await self._calls.create_session(
            agent_id=req.agent_id or "internal-pbx",
            session_type=CallSessionType.TELEPHONY,
            direction=CallDirection.OUTBOUND,
            provider="asterisk_internal",
            caller_number=from_ext,
            destination_number=to_ext,
            external_call_id=channel_id,
        )

        record = InternalCallRecord(
            call_id=call_id,
            provider_id=prov.id,
            channel_id=channel_id,
            live_call_session_id=live_sess.id,
            from_extension=from_ext,
            to_extension=to_ext,
            mode=mode,
            agent_id=req.agent_id,
            status=InternalCallStatus.ACTIVE if mode != InternalCallMode.HUMAN else InternalCallStatus.RINGING,
            is_external=ExternalGatewayGuard.is_external_destination(to_ext),
            idempotency_key=req.idempotency_key,
        )
        records.append(record)
        self._save_records(records)
        self._storage.append_jsonl(_INTERNAL_HISTORY, record.model_dump(mode="json"))
        return record

    async def hangup(self, call_id: str, reason: str = "operator_hangup") -> InternalCallRecord:
        records = self._load_records()
        target_idx = next((i for i, r in enumerate(records) if r.call_id == call_id), None)
        if target_idx is None:
            raise InternalCallNotFoundError(call_id)

        rec = records[target_idx]
        if rec.status == InternalCallStatus.ENDED:
            return rec

        resolved = self._resolve_asterisk_provider()
        if resolved is not None:
            _, adapter = resolved
            try:
                await adapter.terminate_call(rec.channel_id)
            except TelephonyProviderError as exc:
                logger.warning("ARI hangup failed for %s: %s", rec.channel_id, exc)

        now = datetime.now(timezone.utc)
        duration = max(0, int((now - rec.started_at).total_seconds()))
        updated = rec.model_copy(
            update={
                "status": InternalCallStatus.ENDED,
                "ended_at": now,
                "duration_seconds": duration,
                "hangup_reason": reason,
            }
        )
        records[target_idx] = updated
        self._save_records(records)
        self._storage.append_jsonl(_INTERNAL_HISTORY, updated.model_dump(mode="json"))

        if rec.live_call_session_id:
            try:
                await self._calls.update_status(rec.live_call_session_id, CallSessionStatus.ENDED)
                await self._calls.publish_event(
                    call_id=rec.live_call_session_id,
                    event_type=CallEventType.CALL_ENDED,
                    source="internal_calls",
                    payload={"reason": reason, "duration_seconds": duration},
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Live call session update skipped for %s: %s", rec.live_call_session_id, exc)

        return updated
