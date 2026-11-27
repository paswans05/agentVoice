"""CampaignService, CampaignExecutionService, CampaignWorker, and CampaignAnalyticsService."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import uuid

from app.providers.telephony import TelephonyProviderFactory
from app.repositories.campaign_repository import (
    CampaignCallRepository,
    CampaignEventRepository,
    CampaignJobRepository,
    CampaignRepository,
)
from app.repositories.lead_repository import LeadRepository
from app.schemas.agent import AgentStatus
from app.schemas.campaigns import (
    CallOutcome,
    Campaign,
    CampaignAnalytics,
    CampaignAnalyticsOverview,
    CampaignCallRecord,
    CampaignCreate,
    CampaignEvent,
    CampaignJob,
    CampaignLeadStatus,
    CampaignProgress,
    CampaignStatus,
    CampaignUpdate,
    CampaignValidationResult,
)
from app.schemas.leads import SuppressionCreateRequest
from app.services.agent_service import AgentNotFoundError, AgentService
from app.services.campaign_eligibility import CampaignEligibilityService
from app.services.campaign_policy import (
    CampaignPolicyService,
    CampaignRetryService,
    CampaignScheduler,
)
from app.services.suppression_service import SuppressionService

logger = logging.getLogger(__name__)


class CampaignNotFoundError(LookupError):
    """Raised when a campaign ID is not found."""


class CampaignStateError(ValueError):
    """Raised when a campaign transition or validation fails."""


class CampaignService:
    """CRUD, validation, lifecycle controls, and audit logging for campaigns."""

    def __init__(
        self,
        campaign_repo: CampaignRepository,
        job_repo: CampaignJobRepository,
        event_repo: CampaignEventRepository,
        eligibility_svc: CampaignEligibilityService,
        agent_svc: AgentService,
    ) -> None:
        self._repo = campaign_repo
        self._jobs = job_repo
        self._events = event_repo
        self._eligibility = eligibility_svc
        self._agents = agent_svc

    async def _log_event(
        self, campaign_id: str, event_type: str, description: str, actor: str = "operator"
    ) -> None:
        await self._events.append(
            CampaignEvent(
                event_id=f"cevt_{uuid.uuid4().hex[:12]}",
                campaign_id=campaign_id,
                event_type=event_type,
                description=description,
                actor=actor,
            )
        )

    async def list_campaigns(self) -> list[Campaign]:
        return await self._repo.list_all()

    async def get_campaign(self, campaign_id: str) -> Campaign:
        campaign = await self._repo.get_by_id(campaign_id)
        if campaign is None:
            raise CampaignNotFoundError(f"Campaign '{campaign_id}' was not found.")
        return campaign

    async def create_campaign(self, payload: CampaignCreate) -> Campaign:
        now = datetime.now(timezone.utc)
        campaign = Campaign(
            id=f"cmp_{uuid.uuid4().hex[:12]}",
            name=payload.name.strip(),
            description=payload.description.strip(),
            notes=payload.notes.strip(),
            campaign_type=payload.campaign_type,
            status=CampaignStatus.DRAFT,
            agent_id=payload.agent_id,
            knowledge_base_id=payload.knowledge_base_id,
            calling_purpose=payload.calling_purpose.strip().upper(),
            lead_group_ids=list(dict.fromkeys(payload.lead_group_ids)),
            selected_lead_ids=list(dict.fromkeys(payload.selected_lead_ids)),
            timezone=payload.timezone,
            calling_days=payload.calling_days,
            start_date=payload.start_date,
            end_date=payload.end_date,
            start_time=payload.start_time,
            end_time=payload.end_time,
            maximum_calls=payload.maximum_calls,
            maximum_concurrent_calls=payload.maximum_concurrent_calls,
            maximum_attempts_per_lead=payload.maximum_attempts_per_lead,
            retry_interval_minutes=payload.retry_interval_minutes,
            minimum_interval_between_attempts_minutes=payload.minimum_interval_between_attempts_minutes,
            retry_policy=payload.retry_policy,
            dry_run=payload.dry_run,
            telephony_provider=payload.telephony_provider,
            recording_enabled=payload.recording_enabled,
            created_at=now,
            updated_at=now,
        )
        created = await self._repo.create(campaign)
        await self._log_event(created.id, "CAMPAIGN_CREATED", f"Created campaign '{created.name}'")
        return created

    async def update_campaign(self, campaign_id: str, payload: CampaignUpdate) -> Campaign:
        existing = await self.get_campaign(campaign_id)
        if existing.status not in (CampaignStatus.DRAFT, CampaignStatus.PAUSED, CampaignStatus.READY):
            raise CampaignStateError(
                f"Cannot edit campaign while in '{existing.status.value}' status."
            )
        updated = existing.model_copy(
            update={
                "name": payload.name.strip(),
                "description": payload.description.strip(),
                "notes": payload.notes.strip(),
                "campaign_type": payload.campaign_type,
                "agent_id": payload.agent_id,
                "knowledge_base_id": payload.knowledge_base_id,
                "calling_purpose": payload.calling_purpose.strip().upper(),
                "lead_group_ids": list(dict.fromkeys(payload.lead_group_ids)),
                "selected_lead_ids": list(dict.fromkeys(payload.selected_lead_ids)),
                "timezone": payload.timezone,
                "calling_days": payload.calling_days,
                "start_date": payload.start_date,
                "end_date": payload.end_date,
                "start_time": payload.start_time,
                "end_time": payload.end_time,
                "maximum_calls": payload.maximum_calls,
                "maximum_concurrent_calls": payload.maximum_concurrent_calls,
                "maximum_attempts_per_lead": payload.maximum_attempts_per_lead,
                "retry_interval_minutes": payload.retry_interval_minutes,
                "minimum_interval_between_attempts_minutes": payload.minimum_interval_between_attempts_minutes,
                "retry_policy": payload.retry_policy,
                "dry_run": payload.dry_run,
                "telephony_provider": payload.telephony_provider,
                "recording_enabled": payload.recording_enabled,
            }
        )
        saved = await self._repo.update(updated)
        if saved is None:
            raise CampaignNotFoundError(f"Campaign '{campaign_id}' was not found.")
        await self._log_event(saved.id, "CAMPAIGN_UPDATED", "Updated campaign configuration")
        return saved

    async def delete_campaign(self, campaign_id: str) -> None:
        existing = await self.get_campaign(campaign_id)
        if existing.status == CampaignStatus.RUNNING:
            raise CampaignStateError("Stop or pause a running campaign before deleting it.")
        await self._repo.delete(campaign_id)

    async def validate_campaign(self, campaign_id: str) -> CampaignValidationResult:
        campaign = await self.get_campaign(campaign_id)
        errors: list[str] = []
        warnings: list[str] = []

        # Schedule validation
        errors.extend(CampaignScheduler.validate_schedule(campaign))

        # Policy / Telephony validation
        policy_ok, policy_msg = CampaignPolicyService.check_policy(campaign)
        if not policy_ok:
            errors.append(policy_msg)
        elif campaign.dry_run:
            warnings.append("Dry-run mode enabled: no real phone calls will be placed.")

        # Agent validation
        try:
            agent = await self._agents.get_agent(campaign.agent_id)
            if agent.status != AgentStatus.ACTIVE:
                errors.append(f"Agent '{agent.name}' is {agent.status.value} (must be ACTIVE).")
        except AgentNotFoundError:
            errors.append(f"Assigned agent '{campaign.agent_id}' was not found.")

        # Leads & Eligibility
        eligibility = await self._eligibility.summarize_campaign(campaign)
        if eligibility.total_selected == 0:
            errors.append("Select at least one lead or lead group.")
        elif eligibility.eligible_count == 0:
            errors.append(
                "No selected leads are currently eligible (check phone numbers, consent, and suppression)."
            )

        return CampaignValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            eligibility=eligibility,
        )

    async def pause_campaign(self, campaign_id: str) -> Campaign:
        campaign = await self.get_campaign(campaign_id)
        if campaign.status not in (CampaignStatus.RUNNING, CampaignStatus.SCHEDULED):
            raise CampaignStateError(f"Cannot pause campaign in '{campaign.status.value}' status.")
        saved = await self._repo.update(
            campaign.model_copy(
                update={"status": CampaignStatus.PAUSED, "paused_at": datetime.now(timezone.utc)}
            )
        )
        await self._log_event(campaign_id, "CAMPAIGN_PAUSED", "Campaign paused by operator")
        return saved or campaign

    async def stop_campaign(self, campaign_id: str) -> Campaign:
        campaign = await self.get_campaign(campaign_id)
        if campaign.status in (CampaignStatus.COMPLETED, CampaignStatus.CANCELLED, CampaignStatus.STOPPED):
            return campaign
        jobs = await self._jobs.list_by_campaign(campaign_id)
        for job in jobs:
            if job.status in (
                CampaignLeadStatus.PENDING,
                CampaignLeadStatus.QUEUED,
                CampaignLeadStatus.RETRY_SCHEDULED,
            ):
                await self._jobs.update_job(job.model_copy(update={"status": CampaignLeadStatus.SKIPPED}))
        saved = await self._repo.update(
            campaign.model_copy(
                update={
                    "status": CampaignStatus.STOPPED,
                    "completed_at": datetime.now(timezone.utc),
                }
            )
        )
        await self._log_event(campaign_id, "CAMPAIGN_STOPPED", "Campaign stopped by operator")
        return saved or campaign

    async def cancel_campaign(self, campaign_id: str) -> Campaign:
        campaign = await self.get_campaign(campaign_id)
        if campaign.status not in (CampaignStatus.DRAFT, CampaignStatus.READY, CampaignStatus.SCHEDULED):
            raise CampaignStateError(
                "Only DRAFT, READY, or SCHEDULED campaigns can be cancelled; use stop instead."
            )
        saved = await self._repo.update(
            campaign.model_copy(update={"status": CampaignStatus.CANCELLED})
        )
        await self._log_event(campaign_id, "CAMPAIGN_CANCELLED", "Campaign cancelled")
        return saved or campaign


class CampaignExecutionService:
    """Idempotent local campaign queue & bounded asyncio worker."""

    _active_tasks: dict[str, asyncio.Task[None]] = {}

    def __init__(
        self,
        campaign_service: CampaignService,
        campaign_repo: CampaignRepository,
        job_repo: CampaignJobRepository,
        call_repo: CampaignCallRepository,
        event_repo: CampaignEventRepository,
        lead_repo: LeadRepository,
        eligibility_svc: CampaignEligibilityService,
        suppression_svc: SuppressionService,
    ) -> None:
        self._campaigns = campaign_service
        self._campaign_repo = campaign_repo
        self._jobs = job_repo
        self._calls = call_repo
        self._events = event_repo
        self._leads = lead_repo
        self._eligibility = eligibility_svc
        self._suppression = suppression_svc

    async def start_or_resume(
        self,
        campaign_id: str,
        *,
        bypass_window_for_dry_run: bool = False,
        run_inline: bool = False,
    ) -> Campaign:
        val = await self._campaigns.validate_campaign(campaign_id)
        if not val.valid:
            raise CampaignStateError(" ".join(val.errors))

        campaign = await self._campaigns.get_campaign(campaign_id)
        provider = TelephonyProviderFactory.create(campaign.telephony_provider)
        ok_cfg, msg_cfg = await provider.validate_configuration()
        if not ok_cfg:
            raise CampaignStateError(msg_cfg)

        # Enqueue eligible target leads idempotently
        leads = await self._eligibility.resolve_target_leads(campaign)
        new_jobs: list[CampaignJob] = []
        for lead in leads[: campaign.maximum_calls]:
            idem_key = f"{campaign.id}:{lead.id}:1"
            if await self._jobs.has_idempotency_key(idem_key):
                continue
            new_jobs.append(
                CampaignJob(
                    id=f"cjob_{uuid.uuid4().hex[:12]}",
                    idempotency_key=idem_key,
                    campaign_id=campaign.id,
                    lead_id=lead.id,
                    attempt_number=1,
                    status=CampaignLeadStatus.QUEUED,
                )
            )
        await self._jobs.enqueue_many(new_jobs)

        now = datetime.now(timezone.utc)
        running = await self._campaign_repo.update(
            campaign.model_copy(
                update={
                    "status": CampaignStatus.RUNNING,
                    "started_at": campaign.started_at or now,
                    "paused_at": None,
                }
            )
        )
        await self._events.append(
            CampaignEvent(
                event_id=f"cevt_{uuid.uuid4().hex[:12]}",
                campaign_id=campaign.id,
                event_type="CAMPAIGN_STARTED",
                description=f"Queued {len(new_jobs)} job(s) (dry_run={campaign.dry_run})",
            )
        )

        if run_inline:
            await self._run_worker(campaign.id, bypass_window_for_dry_run=bypass_window_for_dry_run)
        else:
            existing_task = self._active_tasks.get(campaign.id)
            if not existing_task or existing_task.done():
                self._active_tasks[campaign.id] = asyncio.create_task(
                    self._run_worker(campaign.id, bypass_window_for_dry_run=bypass_window_for_dry_run)
                )

        return await self._campaigns.get_campaign(campaign_id)

    async def _run_worker(self, campaign_id: str, *, bypass_window_for_dry_run: bool = False) -> None:
        try:
            campaign = await self._campaigns.get_campaign(campaign_id)
            provider = TelephonyProviderFactory.create(campaign.telephony_provider)
            sem = asyncio.Semaphore(campaign.maximum_concurrent_calls)

            jobs = await self._jobs.list_by_campaign(campaign_id)
            runnable = [
                j
                for j in jobs
                if j.status
                in (
                    CampaignLeadStatus.PENDING,
                    CampaignLeadStatus.QUEUED,
                    CampaignLeadStatus.RETRY_SCHEDULED,
                )
            ]

            async def process_job(job: CampaignJob) -> None:
                async with sem:
                    latest_campaign = await self._campaigns.get_campaign(campaign_id)
                    if latest_campaign.status != CampaignStatus.RUNNING:
                        return

                    lead = await self._leads.get_by_id(job.lead_id)
                    if lead is None:
                        await self._jobs.update_job(
                            job.model_copy(
                                update={
                                    "status": CampaignLeadStatus.SKIPPED,
                                    "error_message": "Lead not found.",
                                }
                            )
                        )
                        return

                    # Re-check eligibility immediately before call initiation
                    enforce_win = not (latest_campaign.dry_run and bypass_window_for_dry_run)
                    elig = await self._eligibility.check_single_lead(
                        latest_campaign, lead, enforce_calling_window=enforce_win
                    )
                    if not elig.eligible:
                        next_status = (
                            CampaignLeadStatus.DO_NOT_CONTACT
                            if elig.suppression_status
                            else CampaignLeadStatus.SKIPPED
                        )
                        await self._jobs.update_job(
                            job.model_copy(
                                update={"status": next_status, "error_message": elig.reason}
                            )
                        )
                        return

                    await self._jobs.update_job(
                        job.model_copy(update={"status": CampaignLeadStatus.INITIATING})
                    )
                    started_at = datetime.now(timezone.utc)
                    res = await provider.initiate_call(
                        to_number=lead.normalized_phone or "",
                        agent_id=latest_campaign.agent_id,
                        campaign_id=latest_campaign.id,
                        idempotency_key=job.idempotency_key,
                    )
                    ended_at = datetime.now(timezone.utc)
                    outcome = CallOutcome(res.outcome)

                    await self._calls.append(
                        CampaignCallRecord(
                            call_id=f"call_{uuid.uuid4().hex[:12]}",
                            campaign_id=latest_campaign.id,
                            lead_id=lead.id,
                            agent_id=latest_campaign.agent_id,
                            attempt_id=job.id,
                            provider_id=provider.provider_id,
                            provider_call_id=res.provider_call_id,
                            is_dry_run=res.is_dry_run,
                            started_at=started_at,
                            ended_at=ended_at,
                            duration_seconds=res.duration_seconds,
                            outcome=outcome,
                            summary=res.summary,
                        )
                    )

                    if outcome == CallOutcome.DO_NOT_CALL:
                        await self._suppression.add_suppression(
                            SuppressionCreateRequest(
                                lead_id=lead.id,
                                reason="Requested DO_NOT_CALL during campaign",
                                source="campaign_call",
                            )
                        )
                        await self._jobs.update_job(
                            job.model_copy(update={"status": CampaignLeadStatus.DO_NOT_CONTACT})
                        )
                        return

                    if CampaignRetryService.should_retry(latest_campaign, outcome, job.attempt_number):
                        retry_at = CampaignRetryService.next_retry_time(
                            latest_campaign, job.attempt_number
                        )
                        await self._jobs.update_job(
                            job.model_copy(
                                update={
                                    "status": CampaignLeadStatus.RETRY_SCHEDULED,
                                    "next_retry_at": retry_at,
                                }
                            )
                        )
                        next_num = job.attempt_number + 1
                        await self._jobs.enqueue_many(
                            [
                                CampaignJob(
                                    id=f"cjob_{uuid.uuid4().hex[:12]}",
                                    idempotency_key=f"{latest_campaign.id}:{lead.id}:{next_num}",
                                    campaign_id=latest_campaign.id,
                                    lead_id=lead.id,
                                    attempt_number=next_num,
                                    status=CampaignLeadStatus.RETRY_SCHEDULED,
                                    scheduled_for=retry_at,
                                )
                            ]
                        )
                    else:
                        final_job_status = (
                            CampaignLeadStatus.FAILED
                            if outcome == CallOutcome.FAILED
                            else CampaignLeadStatus.COMPLETED
                        )
                        await self._jobs.update_job(job.model_copy(update={"status": final_job_status}))

            await asyncio.gather(*(process_job(j) for j in runnable))

            latest = await self._campaigns.get_campaign(campaign_id)
            if latest.status == CampaignStatus.RUNNING:
                await self._campaign_repo.update(
                    latest.model_copy(
                        update={
                            "status": CampaignStatus.COMPLETED,
                            "completed_at": datetime.now(timezone.utc),
                        }
                    )
                )
                await self._events.append(
                    CampaignEvent(
                        event_id=f"cevt_{uuid.uuid4().hex[:12]}",
                        campaign_id=campaign_id,
                        event_type="CAMPAIGN_COMPLETED",
                        description="Campaign execution finished",
                    )
                )
        except Exception as exc:
            logger.exception("Campaign worker failed (%s)", campaign_id)
            latest = await self._campaigns.get_campaign(campaign_id)
            await self._campaign_repo.update(
                latest.model_copy(update={"status": CampaignStatus.FAILED})
            )
            await self._events.append(
                CampaignEvent(
                    event_id=f"cevt_{uuid.uuid4().hex[:12]}",
                    campaign_id=campaign_id,
                    event_type="CAMPAIGN_FAILED",
                    description=str(exc),
                )
            )
        finally:
            self._active_tasks.pop(campaign_id, None)

    async def get_progress(self, campaign_id: str) -> CampaignProgress:
        campaign = await self._campaigns.get_campaign(campaign_id)
        jobs = await self._jobs.list_by_campaign(campaign_id)
        return CampaignProgress(
            campaign_id=campaign.id,
            status=campaign.status,
            dry_run=campaign.dry_run,
            total_jobs=len(jobs),
            pending_jobs=sum(
                1 for j in jobs if j.status in (CampaignLeadStatus.PENDING, CampaignLeadStatus.QUEUED)
            ),
            completed_jobs=sum(1 for j in jobs if j.status == CampaignLeadStatus.COMPLETED),
            failed_jobs=sum(1 for j in jobs if j.status == CampaignLeadStatus.FAILED),
            skipped_jobs=sum(
                1
                for j in jobs
                if j.status in (CampaignLeadStatus.SKIPPED, CampaignLeadStatus.DO_NOT_CONTACT)
            ),
            retry_scheduled_jobs=sum(
                1 for j in jobs if j.status == CampaignLeadStatus.RETRY_SCHEDULED
            ),
        )


class CampaignAnalyticsService:
    """Computes campaign and platform analytics separating real vs dry-run execution."""

    def __init__(
        self,
        campaign_repo: CampaignRepository,
        job_repo: CampaignJobRepository,
        call_repo: CampaignCallRepository,
        eligibility_svc: CampaignEligibilityService,
    ) -> None:
        self._campaigns = campaign_repo
        self._jobs = job_repo
        self._calls = call_repo
        self._eligibility = eligibility_svc

    async def get_campaign_analytics(self, campaign: Campaign) -> CampaignAnalytics:
        elig = await self._eligibility.summarize_campaign(campaign)
        jobs = await self._jobs.list_by_campaign(campaign.id)
        calls = await self._calls.list_by_campaign(campaign.id)

        real_calls = [c for c in calls if not c.is_dry_run]
        dry_calls = [c for c in calls if c.is_dry_run]

        avg_real_dur = (
            round(sum(c.duration_seconds for c in real_calls) / len(real_calls), 1)
            if real_calls
            else 0.0
        )
        completed_jobs = sum(1 for j in jobs if j.status == CampaignLeadStatus.COMPLETED)
        completion_rate = round((completed_jobs / len(jobs)) * 100.0, 1) if jobs else 0.0

        return CampaignAnalytics(
            campaign_id=campaign.id,
            total_selected_leads=elig.total_selected,
            eligible_leads=elig.eligible_count,
            ineligible_leads=elig.ineligible_count,
            queued_leads=sum(1 for j in jobs if j.status == CampaignLeadStatus.QUEUED),
            real_calls_initiated=len(real_calls),
            real_calls_completed=sum(1 for c in real_calls if c.outcome != CallOutcome.FAILED),
            real_calls_failed=sum(1 for c in real_calls if c.outcome == CallOutcome.FAILED),
            dry_run_calls_simulated=len(dry_calls),
            no_answer_count=sum(1 for c in calls if c.outcome == CallOutcome.NO_ANSWER),
            busy_count=sum(1 for c in calls if c.outcome == CallOutcome.BUSY),
            interested_count=sum(1 for c in calls if c.outcome == CallOutcome.INTERESTED),
            not_interested_count=sum(1 for c in calls if c.outcome == CallOutcome.NOT_INTERESTED),
            callback_requests=sum(1 for c in calls if c.outcome == CallOutcome.CALLBACK_REQUESTED),
            appointments_booked=sum(1 for c in calls if c.outcome == CallOutcome.APPOINTMENT_BOOKED),
            average_real_duration_seconds=avg_real_dur,
            completion_rate_percent=completion_rate,
        )

    async def get_overview(self) -> CampaignAnalyticsOverview:
        campaigns = await self._campaigns.list_all()
        calls = await self._calls.list_all()
        return CampaignAnalyticsOverview(
            total_campaigns=len(campaigns),
            draft_campaigns=sum(1 for c in campaigns if c.status == CampaignStatus.DRAFT),
            scheduled_campaigns=sum(1 for c in campaigns if c.status == CampaignStatus.SCHEDULED),
            running_campaigns=sum(1 for c in campaigns if c.status == CampaignStatus.RUNNING),
            paused_campaigns=sum(1 for c in campaigns if c.status == CampaignStatus.PAUSED),
            completed_campaigns=sum(1 for c in campaigns if c.status == CampaignStatus.COMPLETED),
            failed_campaigns=sum(1 for c in campaigns if c.status == CampaignStatus.FAILED),
            total_real_calls=sum(1 for c in calls if not c.is_dry_run),
            total_dry_run_calls=sum(1 for c in calls if c.is_dry_run),
        )
