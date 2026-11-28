"""Internal Asterisk 23 SIP/WebRTC calling API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.v1.health import get_storage
from app.api.v1.live_calls import get_call_session_service
from app.api.v1.telephony import get_telephony_mgmt, get_telephony_repo
from app.core.config import Settings, get_settings
from app.providers.storage import StorageProvider
from app.repositories.telephony_repository import TelephonyRepository
from app.schemas.internal_calls import (
    InternalCallDialRequest,
    InternalCallHangupRequest,
    InternalCallRecord,
    InternalCallsHealth,
    InternalExtension,
)
from app.schemas.response import ApiResponse, ok
from app.services.internal_calls_service import InternalCallsService
from app.services.live_calls_service import CallSessionService
from app.services.telephony_service import TelephonyManagementService

router = APIRouter(prefix="/internal-calls", tags=["internal-calls"])


def get_internal_calls_service(
    storage: StorageProvider = Depends(get_storage),
    repo: TelephonyRepository = Depends(get_telephony_repo),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
    call_svc: CallSessionService = Depends(get_call_session_service),
) -> InternalCallsService:
    return InternalCallsService(storage, repo, mgmt, call_svc)


@router.get("/extensions", response_model=ApiResponse[list[InternalExtension]])
async def list_internal_extensions(
    settings: Settings = Depends(get_settings),
    svc: InternalCallsService = Depends(get_internal_calls_service),
) -> ApiResponse[list[InternalExtension]]:
    """List internal SIP/WebRTC extensions and live registration status (no secrets)."""
    return ok(await svc.list_extensions(), version=settings.app_version)


@router.get("/active", response_model=ApiResponse[list[InternalCallRecord]])
async def list_active_internal_calls(
    settings: Settings = Depends(get_settings),
    svc: InternalCallsService = Depends(get_internal_calls_service),
) -> ApiResponse[list[InternalCallRecord]]:
    """List active internal calls."""
    return ok(svc.list_active_calls(), version=settings.app_version)


@router.get("/history", response_model=ApiResponse[list[InternalCallRecord]])
async def list_internal_call_history(
    limit: int = Query(default=50, ge=1, le=200),
    settings: Settings = Depends(get_settings),
    svc: InternalCallsService = Depends(get_internal_calls_service),
) -> ApiResponse[list[InternalCallRecord]]:
    """List recent internal call history."""
    return ok(svc.list_history(limit=limit), version=settings.app_version)


@router.get("/health", response_model=ApiResponse[InternalCallsHealth])
async def get_internal_calls_health(
    settings: Settings = Depends(get_settings),
    svc: InternalCallsService = Depends(get_internal_calls_service),
) -> ApiResponse[InternalCallsHealth]:
    """Return Asterisk ARI connectivity, extension registration count, and gateway status."""
    return ok(await svc.get_health(), version=settings.app_version)


@router.get("/webrtc-config", response_model=ApiResponse[dict[str, object]])
async def get_internal_webrtc_config(
    settings: Settings = Depends(get_settings),
    repo: TelephonyRepository = Depends(get_telephony_repo),
) -> ApiResponse[dict[str, object]]:
    """Return non-secret WebRTC SIP-over-WebSocket signaling configuration for the browser dialer."""
    providers = repo.providers.list_all()
    ast = next((p for p in providers if p.enabled and p.provider_type.value == "asterisk"), None)
    host = ast.host if ast and ast.host not in ("", "asterisk") else "127.0.0.1"
    port = ast.port if ast else 8088
    scheme = "wss" if (ast and ast.use_tls) else "ws"
    return ok(
        {
            "ws_url": f"{scheme}://{host}:{port}/ws",
            "sip_domain": (ast.sip_domain if ast and ast.sip_domain else host),
            "extensions": ["1001-ws", "1002-ws"],
            "ice_servers": [{"urls": ["stun:stun.l.google.com:19302"]}],
        },
        version=settings.app_version,
    )


@router.post("/dial", response_model=ApiResponse[InternalCallRecord])
async def dial_internal_call(
    payload: InternalCallDialRequest,
    settings: Settings = Depends(get_settings),
    svc: InternalCallsService = Depends(get_internal_calls_service),
) -> ApiResponse[InternalCallRecord]:
    """Originate an internal SIP, echo (600), or AI (700) call via Asterisk ARI."""
    return ok(await svc.dial(payload), version=settings.app_version)


@router.post("/{call_id}/hangup", response_model=ApiResponse[InternalCallRecord])
async def hangup_internal_call(
    call_id: str,
    payload: InternalCallHangupRequest | None = None,
    settings: Settings = Depends(get_settings),
    svc: InternalCallsService = Depends(get_internal_calls_service),
) -> ApiResponse[InternalCallRecord]:
    """Terminate an active internal call and update duration/history."""
    reason = payload.reason if payload else "operator_hangup"
    return ok(await svc.hangup(call_id, reason=reason), version=settings.app_version)


@router.get("/{call_id}", response_model=ApiResponse[InternalCallRecord])
async def get_internal_call(
    call_id: str,
    settings: Settings = Depends(get_settings),
    svc: InternalCallsService = Depends(get_internal_calls_service),
) -> ApiResponse[InternalCallRecord]:
    """Fetch a single internal call record."""
    return ok(svc.get_call(call_id), version=settings.app_version)
