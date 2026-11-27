"""Repositories for Campaigns, Jobs, Calls, and Audit Events via StorageProvider."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from pydantic import ValidationError

from app.providers.storage import StorageProvider
from app.schemas.campaigns import (
    Campaign,
    CampaignCallRecord,
    CampaignEvent,
    CampaignJob,
)

logger = logging.getLogger(__name__)

CAMPAIGNS_FILE = "campaigns/campaigns.json"
JOBS_STORE_FILE = "campaigns/campaign_jobs_store.json"
JOBS_LOG_FILE = "campaigns/campaign_jobs.jsonl"
CALLS_LOG_FILE = "campaigns/campaign_calls.jsonl"
EVENTS_LOG_FILE = "campaigns/campaign_events.jsonl"


class CampaignRepository:
    """Persists Campaign definitions via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    async def list_all(self) -> list[Campaign]:
        raw = self._storage.read_json(CAMPAIGNS_FILE, default=[]) or []
        items: list[Campaign] = []
        for item in raw:
            try:
                items.append(Campaign.model_validate(item))
            except ValidationError as exc:
                logger.warning("Skipping invalid campaign record: %s", exc)
        items.sort(key=lambda c: c.updated_at, reverse=True)
        return items

    async def get_by_id(self, campaign_id: str) -> Campaign | None:
        for c in await self.list_all():
            if c.id == campaign_id:
                return c
        return None

    async def save_all(self, campaigns: list[Campaign]) -> None:
        self._storage.write_json(
            CAMPAIGNS_FILE,
            [c.model_dump(mode="json") for c in campaigns],
        )

    async def create(self, campaign: Campaign) -> Campaign:
        campaigns = await self.list_all()
        campaigns.append(campaign)
        await self.save_all(campaigns)
        return campaign

    async def update(self, campaign: Campaign) -> Campaign | None:
        campaigns = await self.list_all()
        for idx, existing in enumerate(campaigns):
            if existing.id == campaign.id:
                updated = campaign.model_copy(update={"updated_at": datetime.now(timezone.utc)})
                campaigns[idx] = updated
                await self.save_all(campaigns)
                return updated
        return None

    async def delete(self, campaign_id: str) -> bool:
        campaigns = await self.list_all()
        kept = [c for c in campaigns if c.id != campaign_id]
        if len(kept) == len(campaigns):
            return False
        await self.save_all(kept)
        return True


class CampaignJobRepository:
    """Persistent local queue of idempotent CampaignJobs."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def _load_all(self) -> list[CampaignJob]:
        raw = self._storage.read_json(JOBS_STORE_FILE, default=[]) or []
        return [CampaignJob.model_validate(item) for item in raw]

    def _save_all(self, jobs: list[CampaignJob]) -> None:
        self._storage.write_json(
            JOBS_STORE_FILE,
            [j.model_dump(mode="json") for j in jobs],
        )

    async def list_by_campaign(self, campaign_id: str) -> list[CampaignJob]:
        return [j for j in self._load_all() if j.campaign_id == campaign_id]

    async def has_idempotency_key(self, idempotency_key: str) -> bool:
        return any(j.idempotency_key == idempotency_key for j in self._load_all())

    async def enqueue_many(self, new_jobs: list[CampaignJob]) -> list[CampaignJob]:
        if not new_jobs:
            return []
        jobs = self._load_all()
        existing_keys = {j.idempotency_key for j in jobs}
        added: list[CampaignJob] = []
        for job in new_jobs:
            if job.idempotency_key in existing_keys:
                continue
            existing_keys.add(job.idempotency_key)
            jobs.append(job)
            added.append(job)
            self._storage.append_jsonl(JOBS_LOG_FILE, job.model_dump(mode="json"))
        if added:
            self._save_all(jobs)
        return added

    async def update_job(self, job: CampaignJob) -> CampaignJob:
        jobs = self._load_all()
        updated = job.model_copy(update={"updated_at": datetime.now(timezone.utc)})
        for idx, existing in enumerate(jobs):
            if existing.id == updated.id:
                jobs[idx] = updated
                self._save_all(jobs)
                self._storage.append_jsonl(JOBS_LOG_FILE, updated.model_dump(mode="json"))
                return updated
        jobs.append(updated)
        self._save_all(jobs)
        return updated


class CampaignCallRepository:
    """Append-only JSONL repository for campaign call records."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    async def append(self, call: CampaignCallRecord) -> CampaignCallRecord:
        self._storage.append_jsonl(CALLS_LOG_FILE, call.model_dump(mode="json"))
        return call

    async def list_all(self) -> list[CampaignCallRecord]:
        rows = self._storage.read_jsonl(CALLS_LOG_FILE)
        items = [CampaignCallRecord.model_validate(r) for r in rows]
        items.sort(key=lambda c: c.started_at, reverse=True)
        return items

    async def list_by_campaign(self, campaign_id: str) -> list[CampaignCallRecord]:
        return [c for c in await self.list_all() if c.campaign_id == campaign_id]

    async def get_by_id(self, call_id: str) -> CampaignCallRecord | None:
        for c in await self.list_all():
            if c.call_id == call_id:
                return c
        return None


class CampaignEventRepository:
    """Append-only JSONL repository for campaign audit events."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    async def append(self, event: CampaignEvent) -> CampaignEvent:
        self._storage.append_jsonl(EVENTS_LOG_FILE, event.model_dump(mode="json"))
        return event

    async def list_by_campaign(self, campaign_id: str) -> list[CampaignEvent]:
        rows = self._storage.read_jsonl(EVENTS_LOG_FILE)
        items = [CampaignEvent.model_validate(r) for r in rows if r.get("campaign_id") == campaign_id]
        items.sort(key=lambda e: e.timestamp, reverse=True)
        return items
