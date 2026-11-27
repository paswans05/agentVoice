"""Live Calls REST and WebSocket real-time monitoring endpoints."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging

from fastapi import APIRouter, Depends, Header, Query, WebSocket, WebSocketDisconnect

from app.api.v1.health import get_storage
from app.core.config import Settings, get_settings
from app.providers.storage import StorageProvider
from app.repositories.call_session_repository import (
    CallEventRepository,
    CallMetricsRepository,
    CallMonitoringSettingsService,
    CallSessionRepository,
    TranscriptRepository,
)
from app.schemas.live_calls import (
    CallControlRequest,
    CallFlagRequest,
    CallMetricsSnapshot,
    CallMonitoringSettings,
    CallSession,
    CallSessionStatus,
    CallTransferRequest,
    LiveCallsStats,
    NormalizedCallEvent,
    TranscriptSegment,
)
from app.schemas.response import ApiResponse, ok
from app.services.live_calls_service import (
    CallAuthorizationError,
    CallAuthorizationService,
    CallControlService,
    CallSessionService,
)
from app.services.ws_manager import monitoring_ws_hub

logger = logging.getLogger(__name__)

router = APIRouter(tags=["live-calls"])


def get_call_session_service(
    storage: StorageProvider = Depends(get_storage),
) -> CallSessionService:
    """Dependency providing CallSessionService."""
    return CallSessionService(
        session_repo=CallSessionRepository(storage),
        event_repo=CallEventRepository(storage),
        transcript_repo=TranscriptRepository(storage),
        metrics_repo=CallMetricsRepository(storage),
        ws_hub=monitoring_ws_hub,
    )


def get_call_control_service(
    storage: StorageProvider = Depends(get_storage),
) -> CallControlService:
    """Dependency providing CallControlService."""
    session_repo = CallSessionRepository(storage)
    session_svc = CallSessionService(
        session_repo=session_repo,
        event_repo=CallEventRepository(storage),
        transcript_repo=TranscriptRepository(storage),
        metrics_repo=CallMetricsRepository(storage),
        ws_hub=monitoring_ws_hub,
    )
    return CallControlService(session_service=session_svc, session_repo=session_repo)


def get_monitoring_settings_service(
    storage: StorageProvider = Depends(get_storage),
) -> CallMonitoringSettingsService:
    """Dependency providing CallMonitoringSettingsService."""
    return CallMonitoringSettingsService(storage)


def _require_operator_auth(
    settings: Settings,
    authorization: str | None,
) -> None:
    if not CallAuthorizationService.authorize(settings, authorization):
        raise CallAuthorizationError("Operator authorization is required for this action.")


@router.get("/live-calls", response_model=ApiResponse[list[CallSession]])
async def list_live_calls(
    active_only: bool = Query(default=True),
    status: CallSessionStatus | None = Query(default=None),
    campaign_id: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    settings: Settings = Depends(get_settings),
    svc: CallSessionService = Depends(get_call_session_service),
) -> ApiResponse[list[CallSession]]:
    """List active or historical call sessions."""
    sessions = await svc.list_sessions(
        active_only=active_only,
        status=status,
        campaign_id=campaign_id,
        agent_id=agent_id,
        search=search,
    )
    return ok(sessions[:limit], version=settings.app_version)


@router.get("/live-calls/stats", response_model=ApiResponse[LiveCallsStats])
async def get_live_calls_stats(
    settings: Settings = Depends(get_settings),
    svc: CallSessionService = Depends(get_call_session_service),
) -> ApiResponse[LiveCallsStats]:
    """Return real-time aggregate call monitoring counts."""
    return ok(await svc.get_stats(), version=settings.app_version)


@router.get("/live-calls/settings", response_model=ApiResponse[CallMonitoringSettings])
async def get_live_calls_settings(
    settings: Settings = Depends(get_settings),
    svc: CallMonitoringSettingsService = Depends(get_monitoring_settings_service),
) -> ApiResponse[CallMonitoringSettings]:
    """Return global call monitoring and privacy settings."""
    return ok(svc.get_settings(), version=settings.app_version)


@router.put("/live-calls/settings", response_model=ApiResponse[CallMonitoringSettings])
async def update_live_calls_settings(
    payload: CallMonitoringSettings,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    svc: CallMonitoringSettingsService = Depends(get_monitoring_settings_service),
) -> ApiResponse[CallMonitoringSettings]:
    """Update global call monitoring and privacy settings."""
    _require_operator_auth(settings, authorization)
    return ok(svc.update_settings(payload), version=settings.app_version)


@router.get("/live-calls/{call_id}", response_model=ApiResponse[CallSession])
async def get_live_call(
    call_id: str,
    settings: Settings = Depends(get_settings),
    svc: CallSessionService = Depends(get_call_session_service),
) -> ApiResponse[CallSession]:
    """Get details for a single call session."""
    return ok(await svc.get_session(call_id), version=settings.app_version)


@router.get("/live-calls/{call_id}/events", response_model=ApiResponse[list[NormalizedCallEvent]])
@router.get("/calls/{call_id}/events", response_model=ApiResponse[list[NormalizedCallEvent]])
async def get_call_events(
    call_id: str,
    settings: Settings = Depends(get_settings),
    svc: CallSessionService = Depends(get_call_session_service),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[list[NormalizedCallEvent]]:
    """Return chronological normalized events for a call session."""
    await svc.get_session(call_id)
    events = await CallEventRepository(storage).list_by_call(call_id)
    return ok(events, version=settings.app_version)


@router.get("/live-calls/{call_id}/transcript", response_model=ApiResponse[list[TranscriptSegment]])
@router.get("/calls/{call_id}/transcript", response_model=ApiResponse[list[TranscriptSegment]])
async def get_call_transcript(
    call_id: str,
    q: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
    svc: CallSessionService = Depends(get_call_session_service),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[list[TranscriptSegment]]:
    """Return transcript segments for a call session, optionally filtered by keyword."""
    await svc.get_session(call_id)
    repo = TranscriptRepository(storage)
    segments = await (repo.search_by_call(call_id, q) if q and q.strip() else repo.list_by_call(call_id))
    return ok(segments, version=settings.app_version)


@router.get("/live-calls/{call_id}/metrics", response_model=ApiResponse[CallMetricsSnapshot | None])
@router.get("/calls/{call_id}/metrics", response_model=ApiResponse[CallMetricsSnapshot | None])
async def get_call_metrics(
    call_id: str,
    settings: Settings = Depends(get_settings),
    svc: CallSessionService = Depends(get_call_session_service),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[CallMetricsSnapshot | None]:
    """Return latest latency and stream health metrics for a call session."""
    await svc.get_session(call_id)
    latest = await CallMetricsRepository(storage).get_latest(call_id)
    return ok(latest, version=settings.app_version)


@router.post("/live-calls/{call_id}/terminate", response_model=ApiResponse[CallSession])
async def terminate_live_call(
    call_id: str,
    payload: CallControlRequest | None = None,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    ctrl: CallControlService = Depends(get_call_control_service),
) -> ApiResponse[CallSession]:
    """Terminate an active call session."""
    _require_operator_auth(settings, authorization)
    reason = payload.reason if payload else "Terminated by operator"
    return ok(await ctrl.terminate_call(call_id, reason=reason), version=settings.app_version)


@router.post("/live-calls/{call_id}/hold", response_model=ApiResponse[CallSession])
async def hold_live_call(
    call_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    ctrl: CallControlService = Depends(get_call_control_service),
) -> ApiResponse[CallSession]:
    """Place a call on hold if supported by the underlying provider."""
    _require_operator_auth(settings, authorization)
    return ok(await ctrl.hold_call(call_id), version=settings.app_version)


@router.post("/live-calls/{call_id}/resume", response_model=ApiResponse[CallSession])
async def resume_live_call(
    call_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    ctrl: CallControlService = Depends(get_call_control_service),
) -> ApiResponse[CallSession]:
    """Resume a held call if supported by the underlying provider."""
    _require_operator_auth(settings, authorization)
    return ok(await ctrl.resume_call(call_id), version=settings.app_version)


@router.post("/live-calls/{call_id}/transfer", response_model=ApiResponse[CallSession])
async def transfer_live_call(
    call_id: str,
    payload: CallTransferRequest,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    ctrl: CallControlService = Depends(get_call_control_service),
) -> ApiResponse[CallSession]:
    """Transfer a call to a human operator if supported by the provider."""
    _require_operator_auth(settings, authorization)
    return ok(
        await ctrl.transfer_call(call_id, destination=payload.destination, reason=payload.reason),
        version=settings.app_version,
    )


@router.post("/live-calls/{call_id}/flag", response_model=ApiResponse[CallSession])
async def flag_live_call(
    call_id: str,
    payload: CallFlagRequest,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    ctrl: CallControlService = Depends(get_call_control_service),
) -> ApiResponse[CallSession]:
    """Flag a call session for supervisor review."""
    _require_operator_auth(settings, authorization)
    return ok(await ctrl.flag_call(call_id, reason=payload.reason), version=settings.app_version)


@router.websocket("/live-calls/ws")
async def live_calls_websocket(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
    settings_svc: CallMonitoringSettingsService = Depends(get_monitoring_settings_service),
) -> None:
    """Real-time WebSocket stream for live calls, transcripts, metrics, and events."""
    token = websocket.headers.get("authorization") or websocket.query_params.get("token")
    if not CallAuthorizationService.authorize(settings, token):
        await websocket.close(code=4403)
        return

    await websocket.accept()
    client = monitoring_ws_hub.register(websocket)
    monitoring_cfg = settings_svc.get_settings()
    await websocket.send_json(
        {
            "type": "CONNECTED",
            "client_id": client.client_id,
            "heartbeat_interval_seconds": monitoring_cfg.heartbeat_interval_seconds,
        }
    )

    async def _sender() -> None:
        while True:
            msg = await client.queue.get()
            await websocket.send_json(msg)

    sender_task = asyncio.create_task(_sender())
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                frame = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "ERROR", "message": "Invalid JSON frame."})
                continue

            if not isinstance(frame, dict):
                await websocket.send_json({"type": "ERROR", "message": "Frame must be a JSON object."})
                continue

            msg_type = str(frame.get("type") or "").upper()
            if msg_type == "PING":
                await websocket.send_json({"type": "PONG"})
            elif msg_type == "SUBSCRIBE":
                monitoring_ws_hub.update_subscription(
                    client.client_id,
                    call_ids=frame.get("call_ids") if isinstance(frame.get("call_ids"), list) else None,
                    campaign_id=frame.get("campaign_id") if isinstance(frame.get("campaign_id"), str) else None,
                    agent_id=frame.get("agent_id") if isinstance(frame.get("agent_id"), str) else None,
                    unsubscribe=False,
                )
                await websocket.send_json({"type": "SUBSCRIBED"})
            elif msg_type == "UNSUBSCRIBE":
                monitoring_ws_hub.update_subscription(
                    client.client_id,
                    call_ids=frame.get("call_ids") if isinstance(frame.get("call_ids"), list) else None,
                    unsubscribe=True,
                )
                await websocket.send_json({"type": "UNSUBSCRIBED"})
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sender_task
        monitoring_ws_hub.unregister(client.client_id)
