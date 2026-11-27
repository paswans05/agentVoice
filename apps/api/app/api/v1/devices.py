"""Device Gateway, Mobile Pairing, Commands, and Mobile VoIP endpoints."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

from fastapi import APIRouter, Depends, Header, WebSocket, WebSocketDisconnect, status

from app.api.v1.health import get_storage
from app.api.v1.live_calls import get_call_session_service
from app.core.config import Settings, get_settings
from app.providers.storage import StorageProvider
from app.repositories.device_repository import DeviceRepository
from app.schemas.devices import (
    Device,
    DeviceCapabilityProfile,
    DeviceCommand,
    DeviceCommandCreate,
    DeviceEvent,
    DeviceHealthSnapshot,
    DeviceHeartbeatRequest,
    DevicePairRequest,
    DevicePairResponse,
    MobileVoIPSession,
    MobileVoIPSessionCreate,
    PairingCodeCreate,
    PairingCodePublic,
)
from app.schemas.response import ApiResponse, ok
from app.services.device_service import (
    DeviceAuthenticationService,
    DeviceEventService,
    DevicePairingService,
    DeviceRegistryService,
    MobileVoIPService,
)
from app.services.live_calls_service import (
    CallAuthorizationError,
    CallAuthorizationService,
    CallSessionService,
)
from app.services.ws_manager import monitoring_ws_hub

router = APIRouter(tags=["devices"])


def get_device_repo(
    storage: StorageProvider = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> DeviceRepository:
    return DeviceRepository(storage, settings.agentvoice_secret_key)


def get_device_events(
    repo: DeviceRepository = Depends(get_device_repo),
) -> DeviceEventService:
    return DeviceEventService(repo, ws_hub=monitoring_ws_hub)


def get_device_auth(
    repo: DeviceRepository = Depends(get_device_repo),
    events: DeviceEventService = Depends(get_device_events),
) -> DeviceAuthenticationService:
    return DeviceAuthenticationService(repo, events)


def get_device_pairing(
    repo: DeviceRepository = Depends(get_device_repo),
    auth: DeviceAuthenticationService = Depends(get_device_auth),
    events: DeviceEventService = Depends(get_device_events),
) -> DevicePairingService:
    return DevicePairingService(repo, auth, events)


def get_device_registry(
    repo: DeviceRepository = Depends(get_device_repo),
    events: DeviceEventService = Depends(get_device_events),
) -> DeviceRegistryService:
    return DeviceRegistryService(repo, events)


def get_mobile_voip_service(
    repo: DeviceRepository = Depends(get_device_repo),
    registry: DeviceRegistryService = Depends(get_device_registry),
    events: DeviceEventService = Depends(get_device_events),
    call_svc: CallSessionService = Depends(get_call_session_service),
) -> MobileVoIPService:
    return MobileVoIPService(repo, registry, events, call_svc)


def _require_operator(settings: Settings, authorization: str | None) -> None:
    if not CallAuthorizationService.authorize(settings, authorization):
        raise CallAuthorizationError("Operator authorization is required.")


@router.post(
    "/devices/pairing-codes",
    response_model=ApiResponse[PairingCodePublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_pairing_code(
    payload: PairingCodeCreate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    pairing: DevicePairingService = Depends(get_device_pairing),
) -> ApiResponse[PairingCodePublic]:
    _require_operator(settings, authorization)
    return ok(pairing.create_pairing_code(payload), version=settings.app_version)


@router.post("/devices/pair", response_model=ApiResponse[DevicePairResponse], status_code=status.HTTP_201_CREATED)
async def pair_device(
    payload: DevicePairRequest,
    settings: Settings = Depends(get_settings),
    pairing: DevicePairingService = Depends(get_device_pairing),
) -> ApiResponse[DevicePairResponse]:
    return ok(pairing.pair_device(payload), version=settings.app_version)


@router.get("/devices", response_model=ApiResponse[list[Device]])
async def list_devices(
    settings: Settings = Depends(get_settings),
    registry: DeviceRegistryService = Depends(get_device_registry),
) -> ApiResponse[list[Device]]:
    return ok(registry.list_devices(), version=settings.app_version)


@router.get("/devices/{device_id}", response_model=ApiResponse[Device])
async def get_device(
    device_id: str,
    settings: Settings = Depends(get_settings),
    registry: DeviceRegistryService = Depends(get_device_registry),
) -> ApiResponse[Device]:
    return ok(registry.get_device(device_id), version=settings.app_version)


@router.delete("/devices/{device_id}", response_model=ApiResponse[dict[str, Any]])
async def delete_device(
    device_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    registry: DeviceRegistryService = Depends(get_device_registry),
) -> ApiResponse[dict[str, Any]]:
    _require_operator(settings, authorization)
    return ok({"deleted": registry.delete_device(device_id), "id": device_id}, version=settings.app_version)


@router.post("/devices/{device_id}/revoke", response_model=ApiResponse[Device])
async def revoke_device(
    device_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    auth: DeviceAuthenticationService = Depends(get_device_auth),
) -> ApiResponse[Device]:
    _require_operator(settings, authorization)
    return ok(auth.revoke_device(device_id), version=settings.app_version)


@router.post("/devices/{device_id}/rotate-token", response_model=ApiResponse[dict[str, Any]])
async def rotate_device_token(
    device_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    registry: DeviceRegistryService = Depends(get_device_registry),
    auth: DeviceAuthenticationService = Depends(get_device_auth),
) -> ApiResponse[dict[str, Any]]:
    _require_operator(settings, authorization)
    registry.get_device(device_id)
    token, exp = auth.issue_token(device_id)
    return ok({"device_id": device_id, "device_token": token, "token_expires_at": exp.isoformat()}, version=settings.app_version)


@router.get("/devices/{device_id}/health", response_model=ApiResponse[DeviceHealthSnapshot])
async def get_device_health(
    device_id: str,
    settings: Settings = Depends(get_settings),
    registry: DeviceRegistryService = Depends(get_device_registry),
) -> ApiResponse[DeviceHealthSnapshot]:
    return ok(registry.get_health(device_id), version=settings.app_version)


@router.get("/devices/{device_id}/capabilities", response_model=ApiResponse[DeviceCapabilityProfile])
async def get_device_capabilities(
    device_id: str,
    settings: Settings = Depends(get_settings),
    registry: DeviceRegistryService = Depends(get_device_registry),
) -> ApiResponse[DeviceCapabilityProfile]:
    return ok(registry.get_capabilities(device_id), version=settings.app_version)


@router.post("/devices/{device_id}/heartbeat", response_model=ApiResponse[Device])
async def post_device_heartbeat(
    device_id: str,
    payload: DeviceHeartbeatRequest,
    x_device_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    auth: DeviceAuthenticationService = Depends(get_device_auth),
    registry: DeviceRegistryService = Depends(get_device_registry),
) -> ApiResponse[Device]:
    token = x_device_token or authorization
    auth.authenticate(device_id, token)
    return ok(registry.record_heartbeat(device_id, payload), version=settings.app_version)


@router.get("/devices/{device_id}/events", response_model=ApiResponse[list[DeviceEvent]])
async def get_device_events_route(
    device_id: str,
    settings: Settings = Depends(get_settings),
    registry: DeviceRegistryService = Depends(get_device_registry),
    events: DeviceEventService = Depends(get_device_events),
) -> ApiResponse[list[DeviceEvent]]:
    registry.get_device(device_id)
    return ok(events.list_events(device_id), version=settings.app_version)


@router.post("/devices/{device_id}/commands", response_model=ApiResponse[DeviceCommand], status_code=status.HTTP_201_CREATED)
async def send_device_command(
    device_id: str,
    payload: DeviceCommandCreate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    registry: DeviceRegistryService = Depends(get_device_registry),
) -> ApiResponse[DeviceCommand]:
    _require_operator(settings, authorization)
    return ok(registry.enqueue_command(device_id, payload), version=settings.app_version)


@router.get("/devices/{device_id}/commands/{command_id}", response_model=ApiResponse[DeviceCommand])
async def get_device_command(
    device_id: str,
    command_id: str,
    settings: Settings = Depends(get_settings),
    registry: DeviceRegistryService = Depends(get_device_registry),
) -> ApiResponse[DeviceCommand]:
    return ok(registry.get_command(device_id, command_id), version=settings.app_version)


# --- Mobile VoIP Sessions ---

@router.post("/mobile-voip/sessions", response_model=ApiResponse[MobileVoIPSession], status_code=status.HTTP_201_CREATED)
async def create_mobile_voip_session(
    payload: MobileVoIPSessionCreate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    voip: MobileVoIPService = Depends(get_mobile_voip_service),
) -> ApiResponse[MobileVoIPSession]:
    _require_operator(settings, authorization)
    return ok(await voip.start_session(payload), version=settings.app_version)


@router.get("/mobile-voip/sessions/{session_id}", response_model=ApiResponse[MobileVoIPSession])
async def get_mobile_voip_session(
    session_id: str,
    settings: Settings = Depends(get_settings),
    voip: MobileVoIPService = Depends(get_mobile_voip_service),
) -> ApiResponse[MobileVoIPSession]:
    return ok(voip.get_session(session_id), version=settings.app_version)


@router.post("/mobile-voip/sessions/{session_id}/terminate", response_model=ApiResponse[MobileVoIPSession])
async def terminate_mobile_voip_session(
    session_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    voip: MobileVoIPService = Depends(get_mobile_voip_service),
) -> ApiResponse[MobileVoIPSession]:
    _require_operator(settings, authorization)
    return ok(await voip.terminate_session(session_id), version=settings.app_version)


@router.websocket("/devices/ws")
async def devices_websocket(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
    auth: DeviceAuthenticationService = Depends(get_device_auth),
) -> None:
    device_id = websocket.query_params.get("device_id")
    token = websocket.headers.get("authorization") or websocket.query_params.get("token")
    authorized = False
    if device_id and token:
        try:
            auth.authenticate(device_id, token)
            authorized = True
        except Exception:
            authorized = False
    elif CallAuthorizationService.authorize(settings, token):
        authorized = True

    if not authorized:
        await websocket.close(code=4403)
        return

    await websocket.accept()
    client = monitoring_ws_hub.register(websocket)
    await websocket.send_json({"type": "CONNECTED", "client_id": client.client_id})

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
                continue
            if isinstance(frame, dict) and str(frame.get("type") or "").upper() == "PING":
                await websocket.send_json({"type": "PONG"})
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sender_task
        monitoring_ws_hub.unregister(client.client_id)
