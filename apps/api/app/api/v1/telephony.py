"""Phase 10 Telephony Integration REST & Webhook endpoints."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Header, Request, status

from app.api.v1.agents import get_agent_service
from app.api.v1.health import get_storage
from app.api.v1.leads import get_eligibility_service
from app.api.v1.live_calls import get_call_session_service
from app.core.config import Settings, get_settings
from app.providers.storage import StorageProvider
from app.repositories.telephony_repository import TelephonyRepository
from app.schemas.response import ApiResponse, ok
from app.schemas.telephony import (
    CredentialRotateRequest,
    DtmfActionRequest,
    GsmGatewayCreate,
    GsmGatewayPublic,
    InboundRoute,
    InboundRouteCreate,
    InboundRouteUpdate,
    OutboundRoute,
    OutboundRouteCreate,
    OutboundRouteUpdate,
    ProviderConnectionStatus,
    ProviderToggleRequest,
    SipTrunkCreate,
    SipTrunkPublic,
    SipTrunkUpdate,
    TelephonyOverview,
    TelephonyProviderCreate,
    TelephonyProviderPublic,
    TelephonyProviderType,
    TelephonyProviderUpdate,
    TelephonySettings,
)
from app.services.agent_service import AgentService
from app.services.live_calls_service import CallAuthorizationError, CallAuthorizationService, CallSessionService
from app.services.suppression_service import LeadEligibilityService
from app.services.telephony_service import (
    TelephonyCallRouter,
    TelephonyManagementService,
    TelephonyPolicyError,
)

router = APIRouter(prefix="/telephony", tags=["telephony"])


def get_telephony_repo(
    storage: StorageProvider = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> TelephonyRepository:
    return TelephonyRepository(storage, settings.agentvoice_secret_key)


def get_telephony_mgmt(
    repo: TelephonyRepository = Depends(get_telephony_repo),
    call_svc: CallSessionService = Depends(get_call_session_service),
) -> TelephonyManagementService:
    return TelephonyManagementService(repo, call_svc=call_svc)


def get_telephony_router_svc(
    repo: TelephonyRepository = Depends(get_telephony_repo),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
    call_svc: CallSessionService = Depends(get_call_session_service),
    agent_svc: AgentService = Depends(get_agent_service),
    elig_svc: LeadEligibilityService = Depends(get_eligibility_service),
) -> TelephonyCallRouter:
    return TelephonyCallRouter(repo, mgmt, call_svc, agent_svc, elig_svc)


def _require_auth(settings: Settings, authorization: str | None) -> None:
    if not CallAuthorizationService.authorize(settings, authorization):
        raise CallAuthorizationError("Operator authorization is required.")


@router.get("/overview", response_model=ApiResponse[TelephonyOverview])
async def telephony_overview(
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[TelephonyOverview]:
    return ok(await mgmt.get_overview(), version=settings.app_version)


# --- Providers ---

@router.get("/providers", response_model=ApiResponse[list[TelephonyProviderPublic]])
async def list_telephony_providers(
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[list[TelephonyProviderPublic]]:
    saved = mgmt.list_providers()
    dry_run = TelephonyProviderPublic(
        id="dry_run",
        name="Dry-Run Simulator (Local)",
        provider_type=TelephonyProviderType.DRY_RUN,
        supports_real_calls=False,
        configured=True,
        status=ProviderConnectionStatus.CONNECTED,
        message="Simulates campaign execution locally without placing real phone calls.",
    )
    return ok([dry_run, *saved], version=settings.app_version)


@router.post(
    "/providers",
    response_model=ApiResponse[TelephonyProviderPublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_telephony_provider(
    payload: TelephonyProviderCreate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[TelephonyProviderPublic]:
    _require_auth(settings, authorization)
    return ok(mgmt.create_provider(payload), version=settings.app_version)


@router.get("/providers/{provider_id}", response_model=ApiResponse[TelephonyProviderPublic])
async def get_telephony_provider(
    provider_id: str,
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[TelephonyProviderPublic]:
    return ok(mgmt.get_provider(provider_id), version=settings.app_version)


@router.put("/providers/{provider_id}", response_model=ApiResponse[TelephonyProviderPublic])
async def update_telephony_provider(
    provider_id: str,
    payload: TelephonyProviderUpdate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[TelephonyProviderPublic]:
    _require_auth(settings, authorization)
    return ok(mgmt.update_provider(provider_id, payload), version=settings.app_version)


@router.delete("/providers/{provider_id}", response_model=ApiResponse[dict[str, Any]])
async def delete_telephony_provider(
    provider_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[dict[str, Any]]:
    _require_auth(settings, authorization)
    return ok({"deleted": mgmt.delete_provider(provider_id), "id": provider_id}, version=settings.app_version)


@router.post("/providers/{provider_id}/test", response_model=ApiResponse[dict[str, Any]])
async def test_telephony_provider(
    provider_id: str,
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[dict[str, Any]]:
    return ok(await mgmt.test_provider(provider_id), version=settings.app_version)


@router.post("/providers/{provider_id}/connect", response_model=ApiResponse[TelephonyProviderPublic])
async def connect_telephony_provider(
    provider_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[TelephonyProviderPublic]:
    _require_auth(settings, authorization)
    return ok(await mgmt.connect_provider(provider_id), version=settings.app_version)


@router.post("/providers/{provider_id}/disconnect", response_model=ApiResponse[TelephonyProviderPublic])
async def disconnect_telephony_provider(
    provider_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[TelephonyProviderPublic]:
    _require_auth(settings, authorization)
    return ok(await mgmt.disconnect_provider(provider_id), version=settings.app_version)


@router.get("/providers/{provider_id}/health", response_model=ApiResponse[dict[str, Any]])
async def telephony_provider_health(
    provider_id: str,
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[dict[str, Any]]:
    return ok(await mgmt.test_provider(provider_id), version=settings.app_version)


@router.post("/providers/{provider_id}/rotate-credentials", response_model=ApiResponse[TelephonyProviderPublic])
async def rotate_provider_credentials(
    provider_id: str,
    payload: CredentialRotateRequest,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[TelephonyProviderPublic]:
    _require_auth(settings, authorization)
    return ok(mgmt.rotate_provider_credentials(provider_id, payload), version=settings.app_version)


@router.post("/providers/{provider_id}/toggle", response_model=ApiResponse[TelephonyProviderPublic])
async def toggle_telephony_provider(
    provider_id: str,
    payload: ProviderToggleRequest,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[TelephonyProviderPublic]:
    _require_auth(settings, authorization)
    return ok(mgmt.set_provider_enabled(provider_id, payload.enabled), version=settings.app_version)


# --- SIP Trunks ---

@router.get("/trunks", response_model=ApiResponse[list[SipTrunkPublic]])
async def list_sip_trunks(
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[list[SipTrunkPublic]]:
    return ok(mgmt.list_trunks(), version=settings.app_version)


@router.post("/trunks", response_model=ApiResponse[SipTrunkPublic], status_code=status.HTTP_201_CREATED)
async def create_sip_trunk(
    payload: SipTrunkCreate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[SipTrunkPublic]:
    _require_auth(settings, authorization)
    return ok(mgmt.create_trunk(payload), version=settings.app_version)


@router.put("/trunks/{trunk_id}", response_model=ApiResponse[SipTrunkPublic])
async def update_sip_trunk(
    trunk_id: str,
    payload: SipTrunkUpdate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[SipTrunkPublic]:
    _require_auth(settings, authorization)
    return ok(mgmt.update_trunk(trunk_id, payload), version=settings.app_version)


@router.delete("/trunks/{trunk_id}", response_model=ApiResponse[dict[str, Any]])
async def delete_sip_trunk(
    trunk_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[dict[str, Any]]:
    _require_auth(settings, authorization)
    return ok({"deleted": mgmt.delete_trunk(trunk_id), "id": trunk_id}, version=settings.app_version)


@router.post("/trunks/{trunk_id}/test", response_model=ApiResponse[dict[str, Any]])
async def test_sip_trunk(
    trunk_id: str,
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[dict[str, Any]]:
    return ok(await mgmt.test_trunk(trunk_id), version=settings.app_version)


# --- Inbound Routes ---

@router.get("/inbound-routes", response_model=ApiResponse[list[InboundRoute]])
async def list_inbound_routes(
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[list[InboundRoute]]:
    return ok(mgmt.list_inbound_routes(), version=settings.app_version)


@router.post("/inbound-routes", response_model=ApiResponse[InboundRoute], status_code=status.HTTP_201_CREATED)
async def create_inbound_route(
    payload: InboundRouteCreate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[InboundRoute]:
    _require_auth(settings, authorization)
    return ok(mgmt.create_inbound_route(payload), version=settings.app_version)


@router.put("/inbound-routes/{route_id}", response_model=ApiResponse[InboundRoute])
async def update_inbound_route(
    route_id: str,
    payload: InboundRouteUpdate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[InboundRoute]:
    _require_auth(settings, authorization)
    return ok(mgmt.update_inbound_route(route_id, payload), version=settings.app_version)


@router.delete("/inbound-routes/{route_id}", response_model=ApiResponse[dict[str, Any]])
async def delete_inbound_route(
    route_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[dict[str, Any]]:
    _require_auth(settings, authorization)
    return ok({"deleted": mgmt.delete_inbound_route(route_id), "id": route_id}, version=settings.app_version)


# --- Outbound Routes ---

@router.get("/outbound-routes", response_model=ApiResponse[list[OutboundRoute]])
async def list_outbound_routes(
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[list[OutboundRoute]]:
    return ok(mgmt.list_outbound_routes(), version=settings.app_version)


@router.post("/outbound-routes", response_model=ApiResponse[OutboundRoute], status_code=status.HTTP_201_CREATED)
async def create_outbound_route(
    payload: OutboundRouteCreate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[OutboundRoute]:
    _require_auth(settings, authorization)
    return ok(mgmt.create_outbound_route(payload), version=settings.app_version)


@router.put("/outbound-routes/{route_id}", response_model=ApiResponse[OutboundRoute])
async def update_outbound_route(
    route_id: str,
    payload: OutboundRouteUpdate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[OutboundRoute]:
    _require_auth(settings, authorization)
    return ok(mgmt.update_outbound_route(route_id, payload), version=settings.app_version)


@router.delete("/outbound-routes/{route_id}", response_model=ApiResponse[dict[str, Any]])
async def delete_outbound_route(
    route_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[dict[str, Any]]:
    _require_auth(settings, authorization)
    return ok({"deleted": mgmt.delete_outbound_route(route_id), "id": route_id}, version=settings.app_version)


# --- GSM Gateways ---

@router.get("/gateways", response_model=ApiResponse[list[GsmGatewayPublic]])
async def list_gsm_gateways(
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[list[GsmGatewayPublic]]:
    return ok(mgmt.list_gateways(), version=settings.app_version)


@router.post("/gateways", response_model=ApiResponse[GsmGatewayPublic], status_code=status.HTTP_201_CREATED)
async def create_gsm_gateway(
    payload: GsmGatewayCreate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[GsmGatewayPublic]:
    _require_auth(settings, authorization)
    return ok(mgmt.create_gateway(payload), version=settings.app_version)


@router.get("/gateways/{gateway_id}", response_model=ApiResponse[GsmGatewayPublic])
async def get_gsm_gateway(
    gateway_id: str,
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[GsmGatewayPublic]:
    return ok(mgmt.get_gateway(gateway_id), version=settings.app_version)


@router.post("/gateways/{gateway_id}/test", response_model=ApiResponse[dict[str, Any]])
async def test_gsm_gateway(
    gateway_id: str,
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[dict[str, Any]]:
    return ok(await mgmt.test_gateway(gateway_id), version=settings.app_version)


@router.delete("/gateways/{gateway_id}", response_model=ApiResponse[dict[str, Any]])
async def delete_gsm_gateway(
    gateway_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[dict[str, Any]]:
    _require_auth(settings, authorization)
    return ok({"deleted": mgmt.delete_gateway(gateway_id), "id": gateway_id}, version=settings.app_version)


# --- Telephony Settings, DTMF & Provider Webhooks ---

@router.get("/settings", response_model=ApiResponse[TelephonySettings])
async def get_telephony_settings(
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[TelephonySettings]:
    return ok(mgmt.get_settings(), version=settings.app_version)


@router.put("/settings", response_model=ApiResponse[TelephonySettings])
async def update_telephony_settings(
    payload: TelephonySettings,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> ApiResponse[TelephonySettings]:
    _require_auth(settings, authorization)
    return ok(mgmt.update_settings(payload), version=settings.app_version)


@router.post("/dtmf", response_model=ApiResponse[dict[str, Any]])
async def submit_dtmf_action(
    payload: DtmfActionRequest,
    settings: Settings = Depends(get_settings),
    router_svc: TelephonyCallRouter = Depends(get_telephony_router_svc),
) -> ApiResponse[dict[str, Any]]:
    return ok(await router_svc.handle_dtmf(payload), version=settings.app_version)


@router.post("/events/{provider_id}/webhook", response_model=ApiResponse[dict[str, Any]])
async def receive_provider_webhook(
    provider_id: str,
    request: Request,
    x_telephony_signature: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    repo: TelephonyRepository = Depends(get_telephony_repo),
    router_svc: TelephonyCallRouter = Depends(get_telephony_router_svc),
) -> ApiResponse[dict[str, Any]]:
    raw_bytes = await request.body()
    tel_cfg = repo.get_settings()
    if tel_cfg.webhook_signature_required:
        secret = repo.vault.get_secret(f"provider:{provider_id}:webhook_secret")
        if not TelephonyCallRouter.verify_webhook_signature(raw_bytes, x_telephony_signature, secret):
            raise CallAuthorizationError("Invalid or missing webhook signature.")
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:
        raise TelephonyPolicyError("Invalid JSON webhook payload.") from exc
    return ok(await router_svc.handle_inbound_event(provider_id, payload), version=settings.app_version)
