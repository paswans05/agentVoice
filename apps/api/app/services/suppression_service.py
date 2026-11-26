"""Centralized SuppressionList and reusable LeadEligibilityService."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from app.repositories.lead_repository import (
    LeadActivityRepository,
    LeadRepository,
    SuppressionRepository,
)
from app.schemas.leads import (
    ActivityType,
    ConsentChannel,
    ConsentStatus,
    EligibilityResult,
    LeadActivity,
    LeadStatus,
    SuppressionCreateRequest,
    SuppressionRecord,
)
from app.services.consent_service import ConsentService
from app.services.lead_validation import normalize_phone


class SuppressionService:
    """Manages phone-level and email-level do-not-contact suppression records."""

    def __init__(
        self,
        suppression_repo: SuppressionRepository,
        lead_repo: LeadRepository,
        activity_repo: LeadActivityRepository,
    ) -> None:
        self._repo = suppression_repo
        self._lead_repo = lead_repo
        self._activity_repo = activity_repo

    async def list_records(self, *, include_revoked: bool = False, search: str | None = None) -> list[SuppressionRecord]:
        records = await self._repo.list_all()
        if not include_revoked:
            records = [r for r in records if r.revoked_at is None]
        if search and search.strip():
            q = search.strip().lower()
            records = [
                r
                for r in records
                if q in (r.phone or "").lower()
                or q in (r.email or "").lower()
                or q in r.reason.lower()
            ]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records

    async def get_by_id(self, record_id: str) -> SuppressionRecord | None:
        for rec in await self._repo.list_all():
            if rec.id == record_id:
                return rec
        return None

    async def is_suppressed(
        self,
        *,
        lead_id: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        channel: str = "ALL",
    ) -> bool:
        norm_phone = normalize_phone(phone)
        norm_email = email.strip().lower() if email else None
        records = await self._repo.list_all()

        for rec in records:
            if rec.revoked_at is not None:
                continue
            if rec.channel != "ALL" and channel != "ALL" and rec.channel != channel:
                continue
            if lead_id and rec.lead_id == lead_id:
                return True
            if norm_phone and rec.normalized_phone and rec.normalized_phone == norm_phone:
                return True
            if norm_email and rec.email and rec.email.strip().lower() == norm_email:
                return True
        return False

    async def add_suppression(
        self, payload: SuppressionCreateRequest, actor: str = "operator"
    ) -> SuppressionRecord:
        if not payload.lead_id and not payload.phone and not payload.email:
            raise ValueError("At least one of lead_id, phone, or email is required for suppression.")

        phone = payload.phone
        email = payload.email
        if payload.lead_id:
            lead = await self._lead_repo.get_by_id(payload.lead_id)
            if lead:
                phone = phone or lead.phone
                email = email or lead.email
                await self._lead_repo.update(
                    lead.model_copy(
                        update={"suppressed": True, "status": LeadStatus.DO_NOT_CONTACT}
                    )
                )

        record = SuppressionRecord(
            id=f"sup_{uuid.uuid4().hex[:12]}",
            lead_id=payload.lead_id,
            phone=phone,
            normalized_phone=normalize_phone(phone),
            email=email.strip().lower() if email else None,
            channel=payload.channel.upper(),
            reason=payload.reason.strip(),
            source=payload.source,
            created_by=actor,
        )
        records = await self._repo.list_all()
        records.append(record)
        await self._repo.save_all(records)
        await self._repo.append_audit(record)

        if payload.lead_id:
            await self._activity_repo.append(
                LeadActivity(
                    activity_id=f"act_{uuid.uuid4().hex[:12]}",
                    lead_id=payload.lead_id,
                    activity_type=ActivityType.SUPPRESSION_ADDED,
                    description=f"Added to suppression list ({record.channel}): {record.reason}",
                    metadata={"suppression_id": record.id, "channel": record.channel},
                    actor=actor,
                )
            )
        return record

    async def revoke_suppression(
        self, record_id: str, reason: str = "Operator removed suppression", actor: str = "operator"
    ) -> SuppressionRecord | None:
        records = await self._repo.list_all()
        now = datetime.now(timezone.utc)
        target: SuppressionRecord | None = None
        for idx, rec in enumerate(records):
            if rec.id == record_id:
                target = rec.model_copy(
                    update={"revoked_at": now, "revocation_reason": reason}
                )
                records[idx] = target
                break
        if target is None:
            return None

        await self._repo.save_all(records)
        await self._repo.append_audit(target)

        if target.lead_id:
            still_suppressed = await self.is_suppressed(
                lead_id=target.lead_id,
                phone=target.phone,
                email=target.email,
            )
            lead = await self._lead_repo.get_by_id(target.lead_id)
            if lead and not still_suppressed:
                await self._lead_repo.update(lead.model_copy(update={"suppressed": False}))
            await self._activity_repo.append(
                LeadActivity(
                    activity_id=f"act_{uuid.uuid4().hex[:12]}",
                    lead_id=target.lead_id,
                    activity_type=ActivityType.SUPPRESSION_REMOVED,
                    description=f"Suppression removed: {reason}",
                    metadata={"suppression_id": target.id},
                    actor=actor,
                )
            )
        return target


class LeadEligibilityService:
    """Reusable contact eligibility gate for future campaigns and telephony."""

    def __init__(
        self,
        lead_repo: LeadRepository,
        suppression_svc: SuppressionService,
        consent_svc: ConsentService,
    ) -> None:
        self._lead_repo = lead_repo
        self._suppression = suppression_svc
        self._consent = consent_svc

    async def check_contact_eligibility(
        self,
        lead_id: str,
        channel: ConsentChannel = ConsentChannel.PHONE,
        purpose: str = "PRODUCT_INFORMATION",
    ) -> EligibilityResult:
        lead = await self._lead_repo.get_by_id(lead_id)
        if lead is None:
            raise LookupError(f"Lead '{lead_id}' was not found.")

        suppressed = lead.suppressed or await self._suppression.is_suppressed(
            lead_id=lead.id,
            phone=lead.phone,
            email=lead.email,
            channel=channel.value,
        )
        consent_status = await self._consent.get_latest_status(lead.id, channel, purpose)

        if suppressed or lead.status == LeadStatus.DO_NOT_CONTACT:
            return EligibilityResult(
                lead_id=lead.id,
                channel=channel,
                purpose=purpose,
                eligible=False,
                blocked=True,
                reason="Contact is on the do-not-contact suppression list.",
                applicable_consent_status=consent_status,
                suppression_status=True,
            )

        if consent_status != ConsentStatus.GRANTED:
            return EligibilityResult(
                lead_id=lead.id,
                channel=channel,
                purpose=purpose,
                eligible=False,
                blocked=True,
                reason=(
                    f"Consent for {channel.value} / {purpose} is {consent_status.value} "
                    "(GRANTED consent is required)."
                ),
                applicable_consent_status=consent_status,
                suppression_status=False,
            )

        return EligibilityResult(
            lead_id=lead.id,
            channel=channel,
            purpose=purpose,
            eligible=True,
            blocked=False,
            reason="Eligible: explicit consent granted and not suppressed.",
            applicable_consent_status=consent_status,
            suppression_status=False,
        )
