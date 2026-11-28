"""CampaignEligibilityService integrating Phase 7 consent, suppression, agent, and schedule checks."""

from __future__ import annotations

from datetime import datetime

from app.repositories.lead_repository import LeadRepository
from app.repositories.telephony_repository import TelephonyRepository
from app.schemas.agent import AgentStatus
from app.schemas.campaigns import (
    Campaign,
    CampaignEligibilitySummary,
    CampaignLeadEligibilityDetail,
)
from app.schemas.leads import ConsentChannel, ConsentStatus, Lead
from app.services.agent_service import AgentNotFoundError, AgentService
from app.services.campaign_policy import CampaignPolicyService, CampaignScheduler
from app.services.suppression_service import LeadEligibilityService


class CampaignEligibilityService:
    """Resolves campaign target leads and enforces pre-call eligibility."""

    def __init__(
        self,
        lead_repo: LeadRepository,
        lead_eligibility: LeadEligibilityService,
        agent_service: AgentService,
        telephony_repo: TelephonyRepository | None = None,
    ) -> None:
        self._lead_repo = lead_repo
        self._lead_eligibility = lead_eligibility
        self._agents = agent_service
        self._telephony_repo = telephony_repo

    async def resolve_target_leads(self, campaign: Campaign) -> list[Lead]:
        all_leads = await self._lead_repo.list_all()
        selected_set = set(campaign.selected_lead_ids)
        group_set = set(campaign.lead_group_ids)

        resolved: list[Lead] = []
        seen: set[str] = set()
        for lead in all_leads:
            if lead.id in seen:
                continue
            in_selected = lead.id in selected_set
            in_group = bool(group_set and any(gid in group_set for gid in lead.group_ids))
            if in_selected or in_group:
                seen.add(lead.id)
                resolved.append(lead)
        return resolved

    async def check_single_lead(
        self,
        campaign: Campaign,
        lead: Lead,
        *,
        enforce_calling_window: bool = False,
        now_utc: datetime | None = None,
    ) -> CampaignLeadEligibilityDetail:
        # 1. Valid contact number
        if not lead.normalized_phone:
            return CampaignLeadEligibilityDetail(
                lead_id=lead.id,
                full_name=lead.full_name,
                phone=lead.phone,
                eligible=False,
                blocked=True,
                reason="Lead does not have a valid phone number.",
                consent_status=lead.consent_status.value,
                suppression_status=lead.suppressed,
            )

        # 2. Agent exists & is ACTIVE
        try:
            agent = await self._agents.get_agent(campaign.agent_id)
            if agent.status != AgentStatus.ACTIVE:
                return CampaignLeadEligibilityDetail(
                    lead_id=lead.id,
                    full_name=lead.full_name,
                    phone=lead.phone,
                    eligible=False,
                    blocked=True,
                    reason=f"Assigned agent '{agent.name}' is {agent.status.value} (must be ACTIVE).",
                    consent_status=lead.consent_status.value,
                    suppression_status=lead.suppressed,
                )
        except AgentNotFoundError:
            return CampaignLeadEligibilityDetail(
                lead_id=lead.id,
                full_name=lead.full_name,
                phone=lead.phone,
                eligible=False,
                blocked=True,
                reason="Assigned AI agent does not exist.",
                consent_status=lead.consent_status.value,
                suppression_status=lead.suppressed,
            )

        # 3. Phase 7 LeadEligibilityService (suppression + channel/purpose consent)
        elig = await self._lead_eligibility.check_contact_eligibility(
            lead.id,
            channel=ConsentChannel.PHONE,
            purpose=campaign.calling_purpose,
        )
        if not elig.eligible:
            return CampaignLeadEligibilityDetail(
                lead_id=lead.id,
                full_name=lead.full_name,
                phone=lead.phone,
                eligible=False,
                blocked=True,
                reason=elig.reason,
                consent_status=elig.applicable_consent_status.value,
                suppression_status=elig.suppression_status,
            )

        # 4. Policy check
        policy_ok, policy_msg = CampaignPolicyService.check_policy(
            campaign, telephony_repo=self._telephony_repo
        )
        if not policy_ok:
            return CampaignLeadEligibilityDetail(
                lead_id=lead.id,
                full_name=lead.full_name,
                phone=lead.phone,
                eligible=False,
                blocked=True,
                reason=policy_msg,
                consent_status=elig.applicable_consent_status.value,
                suppression_status=elig.suppression_status,
            )

        # 5. Calling window check (at execution time)
        if enforce_calling_window:
            win_ok, win_msg = CampaignScheduler.is_within_calling_window(campaign, now_utc=now_utc)
            if not win_ok:
                return CampaignLeadEligibilityDetail(
                    lead_id=lead.id,
                    full_name=lead.full_name,
                    phone=lead.phone,
                    eligible=False,
                    blocked=True,
                    reason=win_msg,
                    consent_status=elig.applicable_consent_status.value,
                    suppression_status=elig.suppression_status,
                )

        return CampaignLeadEligibilityDetail(
            lead_id=lead.id,
            full_name=lead.full_name,
            phone=lead.phone,
            eligible=True,
            blocked=False,
            reason="Eligible for campaign execution.",
            consent_status=elig.applicable_consent_status.value,
            suppression_status=False,
        )

    async def summarize_campaign(self, campaign: Campaign) -> CampaignEligibilitySummary:
        leads = await self.resolve_target_leads(campaign)
        details: list[CampaignLeadEligibilityDetail] = []
        eligible_count = 0
        suppressed_count = 0
        unknown_consent_count = 0
        invalid_phone_count = 0

        for lead in leads:
            d = await self.check_single_lead(campaign, lead, enforce_calling_window=False)
            details.append(d)
            if d.eligible:
                eligible_count += 1
            if d.suppression_status:
                suppressed_count += 1
            if d.consent_status == ConsentStatus.UNKNOWN.value:
                unknown_consent_count += 1
            if not lead.normalized_phone:
                invalid_phone_count += 1

        return CampaignEligibilitySummary(
            campaign_id=campaign.id,
            total_selected=len(leads),
            eligible_count=eligible_count,
            ineligible_count=len(leads) - eligible_count,
            suppressed_count=suppressed_count,
            unknown_consent_count=unknown_consent_count,
            invalid_phone_count=invalid_phone_count,
            details=details,
        )
