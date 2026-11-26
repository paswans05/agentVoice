"""Leads Management, Groups, Consent, Suppression, and CSV Import/Export endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status

from app.api.v1.agents import get_agent_service
from app.api.v1.health import get_storage
from app.core.config import Settings, get_settings
from app.providers.storage import StorageProvider
from app.repositories.lead_repository import (
    ConsentRepository,
    LeadActivityRepository,
    LeadGroupRepository,
    LeadRepository,
    SuppressionRepository,
)
from app.schemas.leads import (
    BulkDeleteRequest,
    BulkUpdateRequest,
    CSVExportRequest,
    CSVImportPreviewResponse,
    CSVImportResult,
    CSVImportValidateRequest,
    ConsentChannel,
    ConsentGrantRequest,
    ConsentRecord,
    ConsentRevokeRequest,
    ConsentStatus,
    EligibilityResult,
    Lead,
    LeadActivity,
    LeadCreate,
    LeadDashboardStats,
    LeadGroup,
    LeadGroupCreate,
    LeadListResponse,
    LeadPriority,
    LeadStatus,
    LeadUpdate,
    SuppressionCreateRequest,
    SuppressionRecord,
)
from app.schemas.response import ApiResponse, ok
from app.services.agent_service import AgentService
from app.services.consent_service import ConsentService
from app.services.lead_csv_service import LeadExportService, LeadImportService
from app.services.lead_service import (
    LeadAssignmentService,
    LeadGroupNotFoundError,
    LeadGroupService,
    LeadNotFoundError,
    LeadService,
    LeadValidationError,
)
from app.services.suppression_service import LeadEligibilityService, SuppressionService

router = APIRouter(tags=["leads"])


def _repos(storage: StorageProvider):
    return (
        LeadRepository(storage),
        LeadGroupRepository(storage),
        ConsentRepository(storage),
        SuppressionRepository(storage),
        LeadActivityRepository(storage),
    )


def get_suppression_service(storage: StorageProvider = Depends(get_storage)) -> SuppressionService:
    lead_repo, _, _, sup_repo, act_repo = _repos(storage)
    return SuppressionService(sup_repo, lead_repo, act_repo)


def get_consent_service(storage: StorageProvider = Depends(get_storage)) -> ConsentService:
    lead_repo, _, cns_repo, _, act_repo = _repos(storage)
    return ConsentService(cns_repo, lead_repo, act_repo)


def get_lead_service(storage: StorageProvider = Depends(get_storage)) -> LeadService:
    lead_repo, _, _, sup_repo, act_repo = _repos(storage)
    sup_svc = SuppressionService(sup_repo, lead_repo, act_repo)
    return LeadService(lead_repo, act_repo, sup_svc)


def get_group_service(storage: StorageProvider = Depends(get_storage)) -> LeadGroupService:
    lead_repo, grp_repo, _, _, act_repo = _repos(storage)
    return LeadGroupService(grp_repo, lead_repo, act_repo)


def get_assignment_service(
    storage: StorageProvider = Depends(get_storage),
    agent_svc: AgentService = Depends(get_agent_service),
) -> LeadAssignmentService:
    lead_repo, _, _, _, act_repo = _repos(storage)
    return LeadAssignmentService(lead_repo, agent_svc, act_repo)


def get_eligibility_service(storage: StorageProvider = Depends(get_storage)) -> LeadEligibilityService:
    lead_repo, _, cns_repo, sup_repo, act_repo = _repos(storage)
    sup_svc = SuppressionService(sup_repo, lead_repo, act_repo)
    cns_svc = ConsentService(cns_repo, lead_repo, act_repo)
    return LeadEligibilityService(lead_repo, sup_svc, cns_svc)


def get_import_service(storage: StorageProvider = Depends(get_storage)) -> LeadImportService:
    lead_repo, _, _, sup_repo, act_repo = _repos(storage)
    sup_svc = SuppressionService(sup_repo, lead_repo, act_repo)
    return LeadImportService(storage, lead_repo, act_repo, sup_svc)


def get_export_service(storage: StorageProvider = Depends(get_storage)) -> LeadExportService:
    lead_repo, _, _, _, _ = _repos(storage)
    return LeadExportService(lead_repo)


# --- Leads Dashboard & CRUD ---

@router.get("/leads/stats", response_model=ApiResponse[LeadDashboardStats])
async def get_lead_stats(
    settings: Settings = Depends(get_settings),
    svc: LeadService = Depends(get_lead_service),
) -> ApiResponse[LeadDashboardStats]:
    return ok(await svc.get_stats(), version=settings.app_version)


@router.get("/leads", response_model=ApiResponse[LeadListResponse])
async def list_leads(
    search: str | None = Query(default=None, max_length=120),
    status_filter: LeadStatus | None = Query(default=None, alias="status"),
    priority: LeadPriority | None = Query(default=None),
    assigned_agent_id: str | None = Query(default=None),
    group_id: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    consent_status: ConsentStatus | None = Query(default=None),
    suppressed: bool | None = Query(default=None),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    settings: Settings = Depends(get_settings),
    svc: LeadService = Depends(get_lead_service),
) -> ApiResponse[LeadListResponse]:
    res = await svc.list_leads(
        search=search,
        status=status_filter,
        priority=priority,
        assigned_agent_id=assigned_agent_id,
        group_id=group_id,
        tag=tag,
        consent_status=consent_status,
        suppressed=suppressed,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return ok(res, version=settings.app_version)


@router.post("/leads", response_model=ApiResponse[Lead], status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    settings: Settings = Depends(get_settings),
    svc: LeadService = Depends(get_lead_service),
) -> ApiResponse[Lead]:
    try:
        return ok(await svc.create_lead(payload), version=settings.app_version)
    except LeadValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/leads/bulk-update", response_model=ApiResponse[dict[str, int]])
async def bulk_update_leads(
    payload: BulkUpdateRequest,
    settings: Settings = Depends(get_settings),
    svc: LeadService = Depends(get_lead_service),
) -> ApiResponse[dict[str, int]]:
    count = await svc.bulk_update(payload)
    return ok({"updated_count": count}, version=settings.app_version)


@router.post("/leads/bulk-delete", response_model=ApiResponse[dict[str, int]])
async def bulk_delete_leads(
    payload: BulkDeleteRequest,
    settings: Settings = Depends(get_settings),
    svc: LeadService = Depends(get_lead_service),
) -> ApiResponse[dict[str, int]]:
    count = await svc.bulk_delete(payload)
    return ok({"deleted_count": count}, version=settings.app_version)


@router.post("/leads/import/preview", response_model=ApiResponse[CSVImportPreviewResponse])
async def preview_csv_import(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    svc: LeadImportService = Depends(get_import_service),
) -> ApiResponse[CSVImportPreviewResponse]:
    try:
        content = await file.read()
        return ok(await svc.preview_csv(file.filename or "leads.csv", content), version=settings.app_version)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/leads/import/validate", response_model=ApiResponse[CSVImportResult])
async def validate_csv_import(
    payload: CSVImportValidateRequest,
    settings: Settings = Depends(get_settings),
    svc: LeadImportService = Depends(get_import_service),
) -> ApiResponse[CSVImportResult]:
    try:
        return ok(await svc.validate_import(payload), version=settings.app_version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/leads/import/execute", response_model=ApiResponse[CSVImportResult])
async def execute_csv_import(
    payload: CSVImportValidateRequest,
    settings: Settings = Depends(get_settings),
    svc: LeadImportService = Depends(get_import_service),
) -> ApiResponse[CSVImportResult]:
    try:
        return ok(await svc.execute_import(payload), version=settings.app_version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/leads/export")
async def export_leads_csv(
    payload: CSVExportRequest,
    svc: LeadExportService = Depends(get_export_service),
) -> Response:
    csv_bytes = await svc.export_csv(payload)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="agentvoice-leads.csv"'},
    )


@router.get("/leads/{lead_id}", response_model=ApiResponse[Lead])
async def get_lead(
    lead_id: str,
    settings: Settings = Depends(get_settings),
    svc: LeadService = Depends(get_lead_service),
) -> ApiResponse[Lead]:
    try:
        return ok(await svc.get_lead(lead_id), version=settings.app_version)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/leads/{lead_id}", response_model=ApiResponse[Lead])
async def update_lead(
    lead_id: str,
    payload: LeadUpdate,
    settings: Settings = Depends(get_settings),
    svc: LeadService = Depends(get_lead_service),
) -> ApiResponse[Lead]:
    try:
        return ok(await svc.update_lead(lead_id, payload), version=settings.app_version)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LeadValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/leads/{lead_id}", response_model=ApiResponse[dict[str, str | bool]])
async def delete_lead(
    lead_id: str,
    settings: Settings = Depends(get_settings),
    svc: LeadService = Depends(get_lead_service),
) -> ApiResponse[dict[str, str | bool]]:
    try:
        await svc.delete_lead(lead_id)
        return ok({"deleted": True, "id": lead_id}, version=settings.app_version)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- Agent Assignment ---

@router.post("/leads/{lead_id}/assign-agent", response_model=ApiResponse[Lead])
async def assign_agent_to_lead(
    lead_id: str,
    agent_id: str = Query(..., min_length=3),
    settings: Settings = Depends(get_settings),
    svc: LeadAssignmentService = Depends(get_assignment_service),
) -> ApiResponse[Lead]:
    try:
        return ok(await svc.assign_agent(lead_id, agent_id), version=settings.app_version)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/leads/{lead_id}/assign-agent", response_model=ApiResponse[Lead])
async def unassign_agent_from_lead(
    lead_id: str,
    settings: Settings = Depends(get_settings),
    svc: LeadAssignmentService = Depends(get_assignment_service),
) -> ApiResponse[Lead]:
    try:
        return ok(await svc.unassign_agent(lead_id), version=settings.app_version)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- Consent & Eligibility ---

@router.get("/leads/{lead_id}/consent", response_model=ApiResponse[list[ConsentRecord]])
async def get_lead_consent(
    lead_id: str,
    settings: Settings = Depends(get_settings),
    svc: ConsentService = Depends(get_consent_service),
) -> ApiResponse[list[ConsentRecord]]:
    return ok(await svc.list_for_lead(lead_id), version=settings.app_version)


@router.post("/leads/{lead_id}/consent", response_model=ApiResponse[ConsentRecord])
async def grant_lead_consent(
    lead_id: str,
    payload: ConsentGrantRequest,
    settings: Settings = Depends(get_settings),
    svc: ConsentService = Depends(get_consent_service),
) -> ApiResponse[ConsentRecord]:
    try:
        return ok(await svc.record_consent(lead_id, payload), version=settings.app_version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/leads/{lead_id}/consent/revoke", response_model=ApiResponse[ConsentRecord])
async def revoke_lead_consent(
    lead_id: str,
    payload: ConsentRevokeRequest,
    settings: Settings = Depends(get_settings),
    svc: ConsentService = Depends(get_consent_service),
) -> ApiResponse[ConsentRecord]:
    try:
        return ok(await svc.revoke_consent(lead_id, payload), version=settings.app_version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/leads/{lead_id}/eligibility", response_model=ApiResponse[EligibilityResult])
async def check_lead_eligibility(
    lead_id: str,
    channel: ConsentChannel = Query(default=ConsentChannel.PHONE),
    purpose: str = Query(default="PRODUCT_INFORMATION"),
    settings: Settings = Depends(get_settings),
    svc: LeadEligibilityService = Depends(get_eligibility_service),
) -> ApiResponse[EligibilityResult]:
    try:
        return ok(
            await svc.check_contact_eligibility(lead_id, channel=channel, purpose=purpose),
            version=settings.app_version,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- Activity Timeline ---

@router.get("/leads/{lead_id}/activities", response_model=ApiResponse[list[LeadActivity]])
async def get_lead_activities(
    lead_id: str,
    settings: Settings = Depends(get_settings),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[list[LeadActivity]]:
    act_repo = LeadActivityRepository(storage)
    return ok(await act_repo.list_by_lead(lead_id), version=settings.app_version)


# --- Lead Groups ---

@router.get("/lead-groups", response_model=ApiResponse[list[LeadGroup]])
async def list_lead_groups(
    settings: Settings = Depends(get_settings),
    svc: LeadGroupService = Depends(get_group_service),
) -> ApiResponse[list[LeadGroup]]:
    return ok(await svc.list_groups(), version=settings.app_version)


@router.post("/lead-groups", response_model=ApiResponse[LeadGroup], status_code=status.HTTP_201_CREATED)
async def create_lead_group(
    payload: LeadGroupCreate,
    settings: Settings = Depends(get_settings),
    svc: LeadGroupService = Depends(get_group_service),
) -> ApiResponse[LeadGroup]:
    return ok(await svc.create_group(payload), version=settings.app_version)


@router.put("/lead-groups/{group_id}", response_model=ApiResponse[LeadGroup])
async def update_lead_group(
    group_id: str,
    payload: LeadGroupCreate,
    settings: Settings = Depends(get_settings),
    svc: LeadGroupService = Depends(get_group_service),
) -> ApiResponse[LeadGroup]:
    try:
        return ok(await svc.update_group(group_id, payload), version=settings.app_version)
    except LeadGroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/lead-groups/{group_id}", response_model=ApiResponse[dict[str, str | bool]])
async def delete_lead_group(
    group_id: str,
    settings: Settings = Depends(get_settings),
    svc: LeadGroupService = Depends(get_group_service),
) -> ApiResponse[dict[str, str | bool]]:
    try:
        await svc.delete_group(group_id)
        return ok({"deleted": True, "id": group_id}, version=settings.app_version)
    except LeadGroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/lead-groups/{group_id}/leads", response_model=ApiResponse[dict[str, int]])
async def add_leads_to_group(
    group_id: str,
    payload: BulkDeleteRequest,
    settings: Settings = Depends(get_settings),
    svc: LeadGroupService = Depends(get_group_service),
) -> ApiResponse[dict[str, int]]:
    try:
        count = await svc.add_leads_to_group(group_id, payload.lead_ids)
        return ok({"added_count": count}, version=settings.app_version)
    except LeadGroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/lead-groups/{group_id}/leads/{lead_id}", response_model=ApiResponse[dict[str, bool]])
async def remove_lead_from_group(
    group_id: str,
    lead_id: str,
    settings: Settings = Depends(get_settings),
    svc: LeadGroupService = Depends(get_group_service),
) -> ApiResponse[dict[str, bool]]:
    try:
        await svc.remove_lead_from_group(group_id, lead_id)
        return ok({"removed": True}, version=settings.app_version)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- Suppression List ---

@router.get("/suppression-list", response_model=ApiResponse[list[SuppressionRecord]])
async def list_suppression(
    include_revoked: bool = Query(default=False),
    search: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
    svc: SuppressionService = Depends(get_suppression_service),
) -> ApiResponse[list[SuppressionRecord]]:
    return ok(
        await svc.list_records(include_revoked=include_revoked, search=search),
        version=settings.app_version,
    )


@router.post(
    "/suppression-list",
    response_model=ApiResponse[SuppressionRecord],
    status_code=status.HTTP_201_CREATED,
)
async def add_suppression(
    payload: SuppressionCreateRequest,
    settings: Settings = Depends(get_settings),
    svc: SuppressionService = Depends(get_suppression_service),
) -> ApiResponse[SuppressionRecord]:
    try:
        return ok(await svc.add_suppression(payload), version=settings.app_version)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/suppression-list/{record_id}", response_model=ApiResponse[SuppressionRecord])
async def get_suppression_record(
    record_id: str,
    settings: Settings = Depends(get_settings),
    svc: SuppressionService = Depends(get_suppression_service),
) -> ApiResponse[SuppressionRecord]:
    rec = await svc.get_by_id(record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Suppression record '{record_id}' not found.")
    return ok(rec, version=settings.app_version)


@router.delete("/suppression-list/{record_id}", response_model=ApiResponse[SuppressionRecord])
async def revoke_suppression_record(
    record_id: str,
    reason: str = Query(default="Operator removed suppression"),
    settings: Settings = Depends(get_settings),
    svc: SuppressionService = Depends(get_suppression_service),
) -> ApiResponse[SuppressionRecord]:
    rec = await svc.revoke_suppression(record_id, reason=reason)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Suppression record '{record_id}' not found.")
    return ok(rec, version=settings.app_version)
