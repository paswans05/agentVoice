"""Campaign Management, Execution, Analytics, Call History, and Telephony Status endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.agents import get_agent_service
from app.api.v1.health import get_storage
from app.api.v1.leads import get_eligibility_service, get_suppression_service
from app.core.config import Settings, get_settings
from app.providers.storage import StorageProvider
from app.providers.telephony import TelephonyProviderFactory, TelephonyUnavailableError
from app.repositories.campaign_repository import (
    CampaignCallRepository,
    CampaignEventRepository,
    CampaignJobRepository,
    CampaignRepository,
)
from app.repositories.lead_repository import LeadRepository
from app.schemas.campaigns import (
    Campaign,
    CampaignAnalytics,
    CampaignAnalyticsOverview,
    CampaignCallRecord,
    CampaignCreate,
    CampaignEligibilitySummary,
    CampaignEvent,
    CampaignJob,
    CampaignProgress,
    CampaignUpdate,
    CampaignValidationResult,
    TelephonyProviderInfo,
)
from app.schemas.leads import BulkDeleteRequest
from app.schemas.response import ApiResponse, ok
from app.services.agent_service import AgentService
from app.services.campaign_eligibility import CampaignEligibilityService
from app.services.campaign_service import (
    CampaignAnalyticsService,
    CampaignExecutionService,
    CampaignNotFoundError,
    CampaignService,
    CampaignStateError,
)
from app.services.suppression_service import LeadEligibilityService, SuppressionService

router = APIRouter(tags=["campaigns"])


def get_campaign_eligibility(
    storage: StorageProvider = Depends(get_storage),
    lead_elig: LeadEligibilityService = Depends(get_eligibility_service),
    agent_svc: AgentService = Depends(get_agent_service),
) -> CampaignEligibilityService:
    return CampaignEligibilityService(LeadRepository(storage), lead_elig, agent_svc)


def get_campaign_service(
    storage: StorageProvider = Depends(get_storage),
    elig: CampaignEligibilityService = Depends(get_campaign_eligibility),
    agent_svc: AgentService = Depends(get_agent_service),
) -> CampaignService:
    return CampaignService(
        CampaignRepository(storage),
        CampaignJobRepository(storage),
        CampaignEventRepository(storage),
        elig,
        agent_svc,
    )


def get_execution_service(
    storage: StorageProvider = Depends(get_storage),
    campaign_svc: CampaignService = Depends(get_campaign_service),
    elig: CampaignEligibilityService = Depends(get_campaign_eligibility),
    sup_svc: SuppressionService = Depends(get_suppression_service),
) -> CampaignExecutionService:
    return CampaignExecutionService(
        campaign_service=campaign_svc,
        campaign_repo=CampaignRepository(storage),
        job_repo=CampaignJobRepository(storage),
        call_repo=CampaignCallRepository(storage),
        event_repo=CampaignEventRepository(storage),
        lead_repo=LeadRepository(storage),
        eligibility_svc=elig,
        suppression_svc=sup_svc,
    )


def get_analytics_service(
    storage: StorageProvider = Depends(get_storage),
    elig: CampaignEligibilityService = Depends(get_campaign_eligibility),
) -> CampaignAnalyticsService:
    return CampaignAnalyticsService(
        CampaignRepository(storage),
        CampaignJobRepository(storage),
        CampaignCallRepository(storage),
        elig,
    )


# --- Campaign Analytics Overview (must be before /campaigns/{campaign_id}) ---

@router.get("/campaigns/analytics/overview", response_model=ApiResponse[CampaignAnalyticsOverview])
async def campaign_analytics_overview(
    settings: Settings = Depends(get_settings),
    svc: CampaignAnalyticsService = Depends(get_analytics_service),
) -> ApiResponse[CampaignAnalyticsOverview]:
    return ok(await svc.get_overview(), version=settings.app_version)


# --- Campaign CRUD ---

@router.get("/campaigns", response_model=ApiResponse[list[Campaign]])
async def list_campaigns(
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
) -> ApiResponse[list[Campaign]]:
    return ok(await svc.list_campaigns(), version=settings.app_version)


@router.post("/campaigns", response_model=ApiResponse[Campaign], status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
) -> ApiResponse[Campaign]:
    return ok(await svc.create_campaign(payload), version=settings.app_version)


@router.get("/campaigns/{campaign_id}", response_model=ApiResponse[Campaign])
async def get_campaign(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
) -> ApiResponse[Campaign]:
    try:
        return ok(await svc.get_campaign(campaign_id), version=settings.app_version)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/campaigns/{campaign_id}", response_model=ApiResponse[Campaign])
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
) -> ApiResponse[Campaign]:
    try:
        return ok(await svc.update_campaign(campaign_id, payload), version=settings.app_version)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CampaignStateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/campaigns/{campaign_id}", response_model=ApiResponse[dict[str, str | bool]])
async def delete_campaign(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
) -> ApiResponse[dict[str, str | bool]]:
    try:
        await svc.delete_campaign(campaign_id)
        return ok({"deleted": True, "id": campaign_id}, version=settings.app_version)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CampaignStateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# --- Validation & Lifecycle Controls ---

@router.post("/campaigns/{campaign_id}/validate", response_model=ApiResponse[CampaignValidationResult])
async def validate_campaign(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
) -> ApiResponse[CampaignValidationResult]:
    try:
        return ok(await svc.validate_campaign(campaign_id), version=settings.app_version)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/activate", response_model=ApiResponse[Campaign])
async def activate_campaign(
    campaign_id: str,
    run_inline: bool = Query(default=False),
    bypass_window: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
    exec_svc: CampaignExecutionService = Depends(get_execution_service),
) -> ApiResponse[Campaign]:
    try:
        return ok(
            await exec_svc.start_or_resume(
                campaign_id, bypass_window_for_dry_run=bypass_window, run_inline=run_inline
            ),
            version=settings.app_version,
        )
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (CampaignStateError, TelephonyUnavailableError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/pause", response_model=ApiResponse[Campaign])
async def pause_campaign(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
) -> ApiResponse[Campaign]:
    try:
        return ok(await svc.pause_campaign(campaign_id), version=settings.app_version)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CampaignStateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/resume", response_model=ApiResponse[Campaign])
async def resume_campaign(
    campaign_id: str,
    run_inline: bool = Query(default=False),
    bypass_window: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
    exec_svc: CampaignExecutionService = Depends(get_execution_service),
) -> ApiResponse[Campaign]:
    try:
        return ok(
            await exec_svc.start_or_resume(
                campaign_id, bypass_window_for_dry_run=bypass_window, run_inline=run_inline
            ),
            version=settings.app_version,
        )
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (CampaignStateError, TelephonyUnavailableError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/stop", response_model=ApiResponse[Campaign])
async def stop_campaign(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
) -> ApiResponse[Campaign]:
    try:
        return ok(await svc.stop_campaign(campaign_id), version=settings.app_version)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/cancel", response_model=ApiResponse[Campaign])
async def cancel_campaign(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
) -> ApiResponse[Campaign]:
    try:
        return ok(await svc.cancel_campaign(campaign_id), version=settings.app_version)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CampaignStateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# --- Campaign Leads & Eligibility ---

@router.get("/campaigns/{campaign_id}/leads", response_model=ApiResponse[CampaignEligibilitySummary])
async def get_campaign_leads(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
    elig: CampaignEligibilityService = Depends(get_campaign_eligibility),
) -> ApiResponse[CampaignEligibilitySummary]:
    try:
        campaign = await svc.get_campaign(campaign_id)
        return ok(await elig.summarize_campaign(campaign), version=settings.app_version)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/leads", response_model=ApiResponse[Campaign])
async def add_campaign_leads(
    campaign_id: str,
    payload: BulkDeleteRequest,
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[Campaign]:
    try:
        campaign = await svc.get_campaign(campaign_id)
        merged = list(dict.fromkeys([*campaign.selected_lead_ids, *payload.lead_ids]))
        saved = await CampaignRepository(storage).update(
            campaign.model_copy(update={"selected_lead_ids": merged})
        )
        return ok(saved or campaign, version=settings.app_version)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- Progress, Jobs, Calls, Events & Analytics ---

@router.get("/campaigns/{campaign_id}/progress", response_model=ApiResponse[CampaignProgress])
async def get_campaign_progress(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    exec_svc: CampaignExecutionService = Depends(get_execution_service),
) -> ApiResponse[CampaignProgress]:
    try:
        return ok(await exec_svc.get_progress(campaign_id), version=settings.app_version)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/campaigns/{campaign_id}/jobs", response_model=ApiResponse[list[CampaignJob]])
async def get_campaign_jobs(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[list[CampaignJob]]:
    return ok(await CampaignJobRepository(storage).list_by_campaign(campaign_id), version=settings.app_version)


@router.get("/campaigns/{campaign_id}/calls", response_model=ApiResponse[list[CampaignCallRecord]])
async def get_campaign_calls(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[list[CampaignCallRecord]]:
    return ok(
        await CampaignCallRepository(storage).list_by_campaign(campaign_id),
        version=settings.app_version,
    )


@router.get("/campaigns/{campaign_id}/events", response_model=ApiResponse[list[CampaignEvent]])
async def get_campaign_events(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[list[CampaignEvent]]:
    return ok(
        await CampaignEventRepository(storage).list_by_campaign(campaign_id),
        version=settings.app_version,
    )


@router.get("/campaigns/{campaign_id}/analytics", response_model=ApiResponse[CampaignAnalytics])
async def get_campaign_analytics(
    campaign_id: str,
    settings: Settings = Depends(get_settings),
    svc: CampaignService = Depends(get_campaign_service),
    analytics_svc: CampaignAnalyticsService = Depends(get_analytics_service),
) -> ApiResponse[CampaignAnalytics]:
    try:
        campaign = await svc.get_campaign(campaign_id)
        return ok(await analytics_svc.get_campaign_analytics(campaign), version=settings.app_version)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/calls", response_model=ApiResponse[list[CampaignCallRecord]])
async def list_all_calls(
    settings: Settings = Depends(get_settings),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[list[CampaignCallRecord]]:
    return ok(await CampaignCallRepository(storage).list_all(), version=settings.app_version)


@router.get("/calls/{call_id}", response_model=ApiResponse[CampaignCallRecord])
async def get_call(
    call_id: str,
    settings: Settings = Depends(get_settings),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[CampaignCallRecord]:
    call = await CampaignCallRepository(storage).get_by_id(call_id)
    if call is None:
        raise HTTPException(status_code=404, detail=f"Call '{call_id}' was not found.")
    return ok(call, version=settings.app_version)


# --- Telephony Provider Status (Phase 9 handles real SIP/Asterisk) ---

@router.get("/telephony/providers", response_model=ApiResponse[list[TelephonyProviderInfo]])
async def list_telephony_providers(
    settings: Settings = Depends(get_settings),
) -> ApiResponse[list[TelephonyProviderInfo]]:
    providers = [
        TelephonyProviderInfo(
            id="dry_run",
            name="Dry-Run Simulator (Local)",
            supports_real_calls=False,
            configured=True,
            status="READY",
            message="Simulates campaign execution locally without placing real phone calls.",
        ),
        TelephonyProviderInfo(
            id="sip",
            name="Authorized SIP Provider (Phase 9)",
            supports_real_calls=True,
            configured=False,
            status="UNAVAILABLE",
            message="Real SIP/Asterisk calling requires Phase 9 configuration.",
        ),
    ]
    return ok(providers, version=settings.app_version)


@router.get("/telephony/status", response_model=ApiResponse[dict[str, object]])
async def telephony_status(
    settings: Settings = Depends(get_settings),
) -> ApiResponse[dict[str, object]]:
    dry = TelephonyProviderFactory.create("dry_run")
    return ok(
        {
            "real_telephony_configured": False,
            "dry_run_available": True,
            "default_provider": await dry.check_connection(),
            "message": "Dry-run mode is available. Real phone calling requires Phase 9 authorized telephony.",
        },
        version=settings.app_version,
    )


@router.post("/telephony/test-connection", response_model=ApiResponse[dict[str, object]])
async def test_telephony_connection(
    provider_id: str = Query(default="dry_run"),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[dict[str, object]]:
    try:
        provider = TelephonyProviderFactory.create(provider_id)
        return ok(await provider.check_connection(), version=settings.app_version)
    except TelephonyUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
