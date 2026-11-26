"""LeadService, LeadGroupService, LeadAssignmentService, and LeadActivityService."""

from __future__ import annotations

from datetime import datetime, timezone
import math
import uuid

from app.repositories.lead_repository import (
    LeadActivityRepository,
    LeadGroupRepository,
    LeadRepository,
)
from app.schemas.leads import (
    ActivityType,
    BulkDeleteRequest,
    BulkUpdateRequest,
    ConsentStatus,
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
)
from app.services.agent_service import AgentService
from app.services.lead_validation import is_valid_email, is_valid_phone, normalize_phone
from app.services.suppression_service import SuppressionService


class LeadNotFoundError(LookupError):
    """Raised when a lead ID is not found."""


class LeadValidationError(ValueError):
    """Raised when lead data or status transition violates rules."""


class LeadGroupNotFoundError(LookupError):
    """Raised when a lead group ID is not found."""


class LeadService:
    """Core CRUD, filtering, pagination, bulk actions, and dashboard stats."""

    def __init__(
        self,
        lead_repo: LeadRepository,
        activity_repo: LeadActivityRepository,
        suppression_svc: SuppressionService,
    ) -> None:
        self._repo = lead_repo
        self._activity = activity_repo
        self._suppression = suppression_svc

    @staticmethod
    def _build_full_name(first_name: str, last_name: str, full_name: str) -> str:
        if full_name.strip():
            return full_name.strip()
        return f"{first_name.strip()} {last_name.strip()}".strip()

    async def _validate_payload(self, payload: LeadCreate) -> None:
        if not is_valid_email(payload.email):
            raise LeadValidationError("Invalid email address format.")
        if not is_valid_phone(payload.phone):
            raise LeadValidationError("Invalid phone number format.")
        if not is_valid_phone(payload.alternate_phone):
            raise LeadValidationError("Invalid alternate phone number format.")

    async def create_lead(self, payload: LeadCreate, actor: str = "operator") -> Lead:
        await self._validate_payload(payload)
        suppressed = await self._suppression.is_suppressed(
            phone=payload.phone,
            email=payload.email,
        )
        status = LeadStatus.DO_NOT_CONTACT if suppressed else payload.status
        now = datetime.now(timezone.utc)
        lead = Lead(
            id=f"lead_{uuid.uuid4().hex[:12]}",
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            full_name=self._build_full_name(
                payload.first_name, payload.last_name, payload.full_name
            ),
            email=payload.email.strip().lower() if payload.email and payload.email.strip() else None,
            phone=payload.phone.strip() if payload.phone and payload.phone.strip() else None,
            normalized_phone=normalize_phone(payload.phone),
            alternate_phone=(
                payload.alternate_phone.strip()
                if payload.alternate_phone and payload.alternate_phone.strip()
                else None
            ),
            company=payload.company.strip(),
            job_title=payload.job_title.strip(),
            website=payload.website.strip(),
            country=payload.country.strip(),
            state=payload.state.strip(),
            city=payload.city.strip(),
            address=payload.address.strip(),
            source=payload.source.strip() or "manual",
            status=status,
            priority=payload.priority,
            assigned_agent_id=payload.assigned_agent_id,
            group_ids=list(dict.fromkeys(payload.group_ids)),
            tags=[t.strip() for t in payload.tags if t.strip()],
            notes=payload.notes.strip(),
            custom_fields=payload.custom_fields,
            consent_status=ConsentStatus.UNKNOWN,
            suppressed=suppressed,
            created_at=now,
            updated_at=now,
        )
        created = await self._repo.create(lead)
        await self._activity.append(
            LeadActivity(
                activity_id=f"act_{uuid.uuid4().hex[:12]}",
                lead_id=created.id,
                activity_type=ActivityType.LEAD_CREATED,
                description="Lead created",
                metadata={"source": created.source},
                actor=actor,
            )
        )
        return created

    async def get_lead(self, lead_id: str) -> Lead:
        lead = await self._repo.get_by_id(lead_id)
        if lead is None:
            raise LeadNotFoundError(f"Lead '{lead_id}' was not found.")
        return lead

    async def list_leads(
        self,
        *,
        search: str | None = None,
        status: LeadStatus | None = None,
        priority: LeadPriority | None = None,
        assigned_agent_id: str | None = None,
        group_id: str | None = None,
        tag: str | None = None,
        consent_status: ConsentStatus | None = None,
        suppressed: bool | None = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 25,
    ) -> LeadListResponse:
        leads = await self._repo.list_all()

        if search and search.strip():
            q = search.strip().lower()
            leads = [
                l
                for l in leads
                if q in l.full_name.lower()
                or q in (l.email or "").lower()
                or q in (l.phone or "").lower()
                or q in l.company.lower()
            ]
        if status is not None:
            leads = [l for l in leads if l.status == status]
        if priority is not None:
            leads = [l for l in leads if l.priority == priority]
        if assigned_agent_id is not None:
            leads = [l for l in leads if l.assigned_agent_id == assigned_agent_id]
        if group_id is not None:
            leads = [l for l in leads if group_id in l.group_ids]
        if tag is not None:
            tag_low = tag.strip().lower()
            leads = [l for l in leads if any(t.lower() == tag_low for t in l.tags)]
        if consent_status is not None:
            leads = [l for l in leads if l.consent_status == consent_status]
        if suppressed is not None:
            leads = [l for l in leads if l.suppressed == suppressed]

        reverse = sort_order.lower() != "asc"
        if sort_by == "name":
            leads.sort(key=lambda l: l.full_name.lower(), reverse=reverse)
        elif sort_by == "created_at":
            leads.sort(key=lambda l: l.created_at, reverse=reverse)
        else:
            leads.sort(key=lambda l: l.updated_at, reverse=reverse)

        total = len(leads)
        total_pages = max(1, math.ceil(total / page_size))
        start = (page - 1) * page_size
        page_items = leads[start : start + page_size]

        return LeadListResponse(
            items=page_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_stats(self) -> LeadDashboardStats:
        leads = await self._repo.list_all()
        suppressed_records = await self._suppression.list_records()
        return LeadDashboardStats(
            total_leads=len(leads),
            new_leads=sum(1 for l in leads if l.status == LeadStatus.NEW),
            qualified_leads=sum(1 for l in leads if l.status == LeadStatus.QUALIFIED),
            interested_leads=sum(1 for l in leads if l.status == LeadStatus.INTERESTED),
            follow_up_leads=sum(1 for l in leads if l.status == LeadStatus.FOLLOW_UP),
            converted_leads=sum(1 for l in leads if l.status == LeadStatus.CONVERTED),
            suppressed_contacts=len(suppressed_records),
        )

    async def update_lead(
        self, lead_id: str, payload: LeadUpdate, actor: str = "operator"
    ) -> Lead:
        existing = await self.get_lead(lead_id)
        await self._validate_payload(payload)

        # Do not allow normal status update to override a suppression restriction
        if existing.suppressed and payload.status != LeadStatus.DO_NOT_CONTACT:
            raise LeadValidationError(
                "Cannot change status of a suppressed lead away from DO_NOT_CONTACT."
            )

        updated = existing.model_copy(
            update={
                "first_name": payload.first_name.strip(),
                "last_name": payload.last_name.strip(),
                "full_name": self._build_full_name(
                    payload.first_name, payload.last_name, payload.full_name
                ),
                "email": payload.email.strip().lower()
                if payload.email and payload.email.strip()
                else None,
                "phone": payload.phone.strip() if payload.phone and payload.phone.strip() else None,
                "normalized_phone": normalize_phone(payload.phone),
                "company": payload.company.strip(),
                "job_title": payload.job_title.strip(),
                "website": payload.website.strip(),
                "country": payload.country.strip(),
                "state": payload.state.strip(),
                "city": payload.city.strip(),
                "address": payload.address.strip(),
                "source": payload.source.strip() or existing.source,
                "status": payload.status,
                "priority": payload.priority,
                "group_ids": list(dict.fromkeys(payload.group_ids)),
                "tags": [t.strip() for t in payload.tags if t.strip()],
                "notes": payload.notes.strip(),
                "custom_fields": payload.custom_fields,
            }
        )
        saved = await self._repo.update(updated)
        if saved is None:
            raise LeadNotFoundError(f"Lead '{lead_id}' was not found.")

        act_type = (
            ActivityType.STATUS_CHANGED
            if existing.status != saved.status
            else ActivityType.LEAD_UPDATED
        )
        await self._activity.append(
            LeadActivity(
                activity_id=f"act_{uuid.uuid4().hex[:12]}",
                lead_id=saved.id,
                activity_type=act_type,
                description=f"Lead updated (status={saved.status.value})",
                actor=actor,
            )
        )
        return saved

    async def delete_lead(self, lead_id: str) -> None:
        deleted = await self._repo.delete(lead_id)
        if not deleted:
            raise LeadNotFoundError(f"Lead '{lead_id}' was not found.")

    async def bulk_update(self, payload: BulkUpdateRequest) -> int:
        leads = await self._repo.list_all()
        target_ids = set(payload.lead_ids)
        updated_count = 0

        for idx, lead in enumerate(leads):
            if lead.id not in target_ids:
                continue
            updates: dict[str, object] = {"updated_at": datetime.now(timezone.utc)}
            if payload.status is not None and not lead.suppressed:
                updates["status"] = payload.status
            if payload.priority is not None:
                updates["priority"] = payload.priority
            if payload.assigned_agent_id is not None:
                updates["assigned_agent_id"] = payload.assigned_agent_id
            leads[idx] = lead.model_copy(update=updates)
            updated_count += 1

        if updated_count > 0:
            await self._repo.save_all(leads)
        return updated_count

    async def bulk_delete(self, payload: BulkDeleteRequest) -> int:
        return await self._repo.delete_many(set(payload.lead_ids))


class LeadGroupService:
    """Manages LeadGroups without deleting leads when a group is deleted."""

    def __init__(
        self,
        group_repo: LeadGroupRepository,
        lead_repo: LeadRepository,
        activity_repo: LeadActivityRepository,
    ) -> None:
        self._group_repo = group_repo
        self._lead_repo = lead_repo
        self._activity = activity_repo

    async def list_groups(self) -> list[LeadGroup]:
        return await self._group_repo.list_all()

    async def create_group(self, payload: LeadGroupCreate) -> LeadGroup:
        now = datetime.now(timezone.utc)
        group = LeadGroup(
            id=f"grp_{uuid.uuid4().hex[:10]}",
            name=payload.name.strip(),
            description=payload.description.strip(),
            color=payload.color,
            created_at=now,
            updated_at=now,
        )
        groups = await self._group_repo.list_all()
        groups.append(group)
        await self._group_repo.save_all(groups)
        return group

    async def update_group(self, group_id: str, payload: LeadGroupCreate) -> LeadGroup:
        groups = await self._group_repo.list_all()
        for idx, g in enumerate(groups):
            if g.id == group_id:
                updated = g.model_copy(
                    update={
                        "name": payload.name.strip(),
                        "description": payload.description.strip(),
                        "color": payload.color,
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                groups[idx] = updated
                await self._group_repo.save_all(groups)
                return updated
        raise LeadGroupNotFoundError(f"Group '{group_id}' was not found.")

    async def delete_group(self, group_id: str) -> None:
        groups = await self._group_repo.list_all()
        kept = [g for g in groups if g.id != group_id]
        if len(kept) == len(groups):
            raise LeadGroupNotFoundError(f"Group '{group_id}' was not found.")
        await self._group_repo.save_all(kept)

        # Remove group reference from leads without deleting leads
        leads = await self._lead_repo.list_all()
        changed = False
        for idx, lead in enumerate(leads):
            if group_id in lead.group_ids:
                leads[idx] = lead.model_copy(
                    update={"group_ids": [gid for gid in lead.group_ids if gid != group_id]}
                )
                changed = True
        if changed:
            await self._lead_repo.save_all(leads)

    async def add_leads_to_group(self, group_id: str, lead_ids: list[str]) -> int:
        groups = await self._group_repo.list_all()
        if not any(g.id == group_id for g in groups):
            raise LeadGroupNotFoundError(f"Group '{group_id}' was not found.")

        leads = await self._lead_repo.list_all()
        target = set(lead_ids)
        count = 0
        for idx, lead in enumerate(leads):
            if lead.id in target and group_id not in lead.group_ids:
                leads[idx] = lead.model_copy(update={"group_ids": [*lead.group_ids, group_id]})
                count += 1
                await self._activity.append(
                    LeadActivity(
                        activity_id=f"act_{uuid.uuid4().hex[:12]}",
                        lead_id=lead.id,
                        activity_type=ActivityType.GROUP_ADDED,
                        description=f"Added to group {group_id}",
                    )
                )
        if count > 0:
            await self._lead_repo.save_all(leads)
        return count

    async def remove_lead_from_group(self, group_id: str, lead_id: str) -> None:
        lead = await self._lead_repo.get_by_id(lead_id)
        if lead is None:
            raise LeadNotFoundError(f"Lead '{lead_id}' was not found.")
        if group_id in lead.group_ids:
            await self._lead_repo.update(
                lead.model_copy(
                    update={"group_ids": [gid for gid in lead.group_ids if gid != group_id]}
                )
            )
            await self._activity.append(
                LeadActivity(
                    activity_id=f"act_{uuid.uuid4().hex[:12]}",
                    lead_id=lead.id,
                    activity_type=ActivityType.GROUP_REMOVED,
                    description=f"Removed from group {group_id}",
                )
            )


class LeadAssignmentService:
    """Assigns/unassigns leads to validated AI agents."""

    def __init__(
        self,
        lead_repo: LeadRepository,
        agent_service: AgentService,
        activity_repo: LeadActivityRepository,
    ) -> None:
        self._lead_repo = lead_repo
        self._agents = agent_service
        self._activity = activity_repo

    async def assign_agent(self, lead_id: str, agent_id: str) -> Lead:
        lead = await self._lead_repo.get_by_id(lead_id)
        if lead is None:
            raise LeadNotFoundError(f"Lead '{lead_id}' was not found.")
        agent = await self._agents.get_agent(agent_id)

        updated = await self._lead_repo.update(
            lead.model_copy(update={"assigned_agent_id": agent.id})
        )
        await self._activity.append(
            LeadActivity(
                activity_id=f"act_{uuid.uuid4().hex[:12]}",
                lead_id=lead.id,
                activity_type=ActivityType.AGENT_ASSIGNED,
                description=f"Assigned to agent {agent.name}",
                metadata={"agent_id": agent.id},
            )
        )
        return updated or lead

    async def unassign_agent(self, lead_id: str) -> Lead:
        lead = await self._lead_repo.get_by_id(lead_id)
        if lead is None:
            raise LeadNotFoundError(f"Lead '{lead_id}' was not found.")
        updated = await self._lead_repo.update(
            lead.model_copy(update={"assigned_agent_id": None})
        )
        await self._activity.append(
            LeadActivity(
                activity_id=f"act_{uuid.uuid4().hex[:12]}",
                lead_id=lead.id,
                activity_type=ActivityType.AGENT_UNASSIGNED,
                description="Agent assignment removed",
            )
        )
        return updated or lead
