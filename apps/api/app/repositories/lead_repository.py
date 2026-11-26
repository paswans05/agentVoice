"""Repositories for Leads, Groups, Consent, Suppression, and Activities via StorageProvider."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from pydantic import ValidationError

from app.providers.storage import StorageProvider
from app.schemas.leads import (
    ConsentRecord,
    Lead,
    LeadActivity,
    LeadGroup,
    SuppressionRecord,
)

logger = logging.getLogger(__name__)

LEADS_FILE = "leads/leads.jsonl"
GROUPS_FILE = "leads/lead_groups.json"
ACTIVITIES_FILE = "leads/lead_activities.jsonl"
CONSENT_FILE = "leads/consent_records.jsonl"
SUPPRESSION_FILE = "leads/suppression_records.jsonl"
IMPORT_JOBS_DIR = "leads/import_jobs"


class LeadRepository:
    """Persists Lead records in JSONL via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def _rewrite_all(self, leads: list[Lead]) -> None:
        # Atomic rewrite via StorageProvider temp JSON + line-by-line JSONL
        # Use write_json for a staging snapshot or rewrite safely through base_dir?
        # Keep strictly through StorageProvider: delete and append, or store index?
        # Even safer: write_json to leads/leads_index.json AND append_jsonl, OR rewrite via temp?
        # StorageProvider.write_json is atomic! Let's use leads/leads_store.json for atomic random-access CRUD
        # and append_jsonl to leads/leads.jsonl as append-only audit log, OR keep leads_store.json as canonical!
        self._storage.write_json(
            "leads/leads_store.json",
            [lead.model_dump(mode="json") for lead in leads],
        )

    def _load_all(self) -> list[Lead]:
        raw_list = self._storage.read_json("leads/leads_store.json", default=None)
        if raw_list is None:
            # Fallback: migrate/read from leads.jsonl if present
            rows = self._storage.read_jsonl(LEADS_FILE)
            by_id: dict[str, Lead] = {}
            for row in rows:
                try:
                    lead = Lead.model_validate(row)
                    by_id[lead.id] = lead
                except ValidationError:
                    continue
            return list(by_id.values())

        items: list[Lead] = []
        for row in raw_list:
            try:
                items.append(Lead.model_validate(row))
            except ValidationError as exc:
                logger.warning("Skipping invalid lead record: %s", exc)
        return items

    async def list_all(self) -> list[Lead]:
        return self._load_all()

    async def get_by_id(self, lead_id: str) -> Lead | None:
        for lead in self._load_all():
            if lead.id == lead_id:
                return lead
        return None

    async def create(self, lead: Lead) -> Lead:
        leads = self._load_all()
        leads.append(lead)
        self._rewrite_all(leads)
        self._storage.append_jsonl(LEADS_FILE, lead.model_dump(mode="json"))
        return lead

    async def create_many(self, new_leads: list[Lead]) -> list[Lead]:
        if not new_leads:
            return []
        leads = self._load_all()
        leads.extend(new_leads)
        self._rewrite_all(leads)
        for lead in new_leads:
            self._storage.append_jsonl(LEADS_FILE, lead.model_dump(mode="json"))
        return new_leads

    async def update(self, lead: Lead) -> Lead | None:
        leads = self._load_all()
        for idx, existing in enumerate(leads):
            if existing.id == lead.id:
                updated = lead.model_copy(update={"updated_at": datetime.now(timezone.utc)})
                leads[idx] = updated
                self._rewrite_all(leads)
                self._storage.append_jsonl(LEADS_FILE, updated.model_dump(mode="json"))
                return updated
        return None

    async def save_all(self, leads: list[Lead]) -> None:
        self._rewrite_all(leads)

    async def delete(self, lead_id: str) -> bool:
        leads = self._load_all()
        kept = [l for l in leads if l.id != lead_id]
        if len(kept) == len(leads):
            return False
        self._rewrite_all(kept)
        return True

    async def delete_many(self, lead_ids: set[str]) -> int:
        leads = self._load_all()
        kept = [l for l in leads if l.id not in lead_ids]
        removed = len(leads) - len(kept)
        if removed > 0:
            self._rewrite_all(kept)
        return removed


class LeadGroupRepository:
    """Persists LeadGroup records in JSON via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    async def list_all(self) -> list[LeadGroup]:
        raw = self._storage.read_json(GROUPS_FILE, default=[]) or []
        return [LeadGroup.model_validate(item) for item in raw]

    async def save_all(self, groups: list[LeadGroup]) -> None:
        self._storage.write_json(
            GROUPS_FILE,
            [g.model_dump(mode="json") for g in groups],
        )


class ConsentRepository:
    """Append-only JSONL consent audit log via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    async def append(self, record: ConsentRecord) -> ConsentRecord:
        self._storage.append_jsonl(CONSENT_FILE, record.model_dump(mode="json"))
        return record

    async def list_by_lead(self, lead_id: str) -> list[ConsentRecord]:
        rows = self._storage.read_jsonl(CONSENT_FILE)
        items = [ConsentRecord.model_validate(r) for r in rows if r.get("lead_id") == lead_id]
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items


class SuppressionRepository:
    """Persists centralized SuppressionRecord entries via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    async def list_all(self) -> list[SuppressionRecord]:
        raw = self._storage.read_json("leads/suppression_store.json", default=None)
        if raw is None:
            rows = self._storage.read_jsonl(SUPPRESSION_FILE)
            return [SuppressionRecord.model_validate(r) for r in rows]
        return [SuppressionRecord.model_validate(r) for r in raw]

    async def save_all(self, records: list[SuppressionRecord]) -> None:
        self._storage.write_json(
            "leads/suppression_store.json",
            [r.model_dump(mode="json") for r in records],
        )

    async def append_audit(self, record: SuppressionRecord) -> None:
        self._storage.append_jsonl(SUPPRESSION_FILE, record.model_dump(mode="json"))


class LeadActivityRepository:
    """Append-only JSONL lead activity timeline via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    async def append(self, activity: LeadActivity) -> LeadActivity:
        self._storage.append_jsonl(ACTIVITIES_FILE, activity.model_dump(mode="json"))
        return activity

    async def list_by_lead(self, lead_id: str) -> list[LeadActivity]:
        rows = self._storage.read_jsonl(ACTIVITIES_FILE)
        items = [LeadActivity.model_validate(r) for r in rows if r.get("lead_id") == lead_id]
        items.sort(key=lambda a: a.timestamp, reverse=True)
        return items
