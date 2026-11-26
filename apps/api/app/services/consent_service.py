"""ConsentManagement service with strict channel/purpose scoping and audit log."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from app.repositories.lead_repository import ConsentRepository, LeadActivityRepository, LeadRepository
from app.schemas.leads import (
    ActivityType,
    ConsentChannel,
    ConsentGrantRequest,
    ConsentRecord,
    ConsentRevokeRequest,
    ConsentStatus,
    LeadActivity,
)


class ConsentService:
    """Tracks auditable consent per (lead, channel, purpose). Missing defaults to UNKNOWN."""

    def __init__(
        self,
        consent_repo: ConsentRepository,
        lead_repo: LeadRepository,
        activity_repo: LeadActivityRepository,
    ) -> None:
        self._consent_repo = consent_repo
        self._lead_repo = lead_repo
        self._activity_repo = activity_repo

    async def list_for_lead(self, lead_id: str) -> list[ConsentRecord]:
        return await self._consent_repo.list_by_lead(lead_id)

    async def get_latest_status(
        self, lead_id: str, channel: ConsentChannel, purpose: str
    ) -> ConsentStatus:
        records = await self._consent_repo.list_by_lead(lead_id)
        purpose_norm = purpose.strip().upper()
        for rec in records:
            if rec.channel == channel and rec.purpose.strip().upper() == purpose_norm:
                if rec.expires_at and rec.expires_at < datetime.now(timezone.utc):
                    return ConsentStatus.EXPIRED
                return rec.consent_status
        return ConsentStatus.UNKNOWN

    async def record_consent(
        self, lead_id: str, payload: ConsentGrantRequest, actor: str = "operator"
    ) -> ConsentRecord:
        lead = await self._lead_repo.get_by_id(lead_id)
        if lead is None:
            raise LookupError(f"Lead '{lead_id}' was not found.")

        now = datetime.now(timezone.utc)
        record = ConsentRecord(
            id=f"cns_{uuid.uuid4().hex[:12]}",
            lead_id=lead_id,
            consent_status=payload.consent_status,
            consent_type=payload.consent_type,
            purpose=payload.purpose.strip().upper(),
            channel=payload.channel,
            source=payload.source,
            captured_at=now if payload.consent_status == ConsentStatus.GRANTED else None,
            evidence_reference=payload.evidence_reference,
            privacy_notice_version=payload.privacy_notice_version,
            created_at=now,
        )
        await self._consent_repo.append(record)

        # Update summary consent_status on lead (never elevate if already REVOKED/DENIED unless explicitly GRANTED)
        await self._lead_repo.update(
            lead.model_copy(update={"consent_status": payload.consent_status})
        )

        act_type = (
            ActivityType.CONSENT_REVOKED
            if payload.consent_status in (ConsentStatus.REVOKED, ConsentStatus.DENIED)
            else ActivityType.CONSENT_GRANTED
        )
        await self._activity_repo.append(
            LeadActivity(
                activity_id=f"act_{uuid.uuid4().hex[:12]}",
                lead_id=lead_id,
                activity_type=act_type,
                description=(
                    f"Consent {payload.consent_status.value} for "
                    f"{payload.channel.value} / {record.purpose}"
                ),
                metadata={"channel": payload.channel.value, "purpose": record.purpose},
                actor=actor,
            )
        )
        return record

    async def revoke_consent(
        self, lead_id: str, payload: ConsentRevokeRequest, actor: str = "operator"
    ) -> ConsentRecord:
        lead = await self._lead_repo.get_by_id(lead_id)
        if lead is None:
            raise LookupError(f"Lead '{lead_id}' was not found.")

        now = datetime.now(timezone.utc)
        record = ConsentRecord(
            id=f"cns_{uuid.uuid4().hex[:12]}",
            lead_id=lead_id,
            consent_status=ConsentStatus.REVOKED,
            consent_type="EXPLICIT",
            purpose=payload.purpose.strip().upper(),
            channel=payload.channel,
            source="revocation",
            revoked_at=now,
            revocation_reason=payload.reason,
            created_at=now,
        )
        await self._consent_repo.append(record)
        await self._lead_repo.update(
            lead.model_copy(update={"consent_status": ConsentStatus.REVOKED})
        )
        await self._activity_repo.append(
            LeadActivity(
                activity_id=f"act_{uuid.uuid4().hex[:12]}",
                lead_id=lead_id,
                activity_type=ActivityType.CONSENT_REVOKED,
                description=(
                    f"Consent REVOKED for {payload.channel.value} / {record.purpose}"
                ),
                metadata={"channel": payload.channel.value, "purpose": record.purpose},
                actor=actor,
            )
        )
        return record
