"""Repositories for CallSessions, CallEvents, Transcripts, and CallMetrics via StorageProvider."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from pydantic import ValidationError

from app.providers.storage import StorageProvider
from app.schemas.live_calls import (
    CallMetricsSnapshot,
    CallMonitoringSettings,
    CallSession,
    NormalizedCallEvent,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)

SESSIONS_STORE = "calls/call_sessions_store.json"
SESSIONS_LOG = "calls/call_sessions.jsonl"
EVENTS_LOG = "calls/call_events.jsonl"
TRANSCRIPTS_LOG = "calls/transcripts.jsonl"
METRICS_LOG = "calls/call_metrics.jsonl"
MONITORING_SETTINGS_PATH = "config/call_monitoring_settings.json"


class CallSessionRepository:
    """Persists CallSession records via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def _load_all(self) -> list[CallSession]:
        raw = self._storage.read_json(SESSIONS_STORE, default=[]) or []
        items: list[CallSession] = []
        for item in raw:
            try:
                items.append(CallSession.model_validate(item))
            except ValidationError as exc:
                logger.warning("Skipping invalid call session: %s", exc)
        return items

    def _save_all(self, sessions: list[CallSession]) -> None:
        self._storage.write_json(
            SESSIONS_STORE,
            [s.model_dump(mode="json") for s in sessions],
        )

    async def list_all(self) -> list[CallSession]:
        items = self._load_all()
        items.sort(key=lambda s: s.started_at, reverse=True)
        return items

    async def get_by_id(self, call_id: str) -> CallSession | None:
        for s in self._load_all():
            if s.id == call_id:
                return s
        return None

    async def create(self, session: CallSession) -> CallSession:
        sessions = self._load_all()
        sessions.append(session)
        self._save_all(sessions)
        self._storage.append_jsonl(SESSIONS_LOG, session.model_dump(mode="json"))
        return session

    async def update(self, session: CallSession) -> CallSession | None:
        sessions = self._load_all()
        for idx, existing in enumerate(sessions):
            if existing.id == session.id:
                updated = session.model_copy(update={"updated_at": datetime.now(timezone.utc)})
                sessions[idx] = updated
                self._save_all(sessions)
                self._storage.append_jsonl(SESSIONS_LOG, updated.model_dump(mode="json"))
                return updated
        return None


class CallEventRepository:
    """Append-only JSONL repository for normalized call events."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    async def append(self, event: NormalizedCallEvent) -> NormalizedCallEvent:
        self._storage.append_jsonl(EVENTS_LOG, event.model_dump(mode="json"))
        return event

    async def list_by_call(self, call_id: str) -> list[NormalizedCallEvent]:
        rows = self._storage.read_jsonl(EVENTS_LOG)
        items = [NormalizedCallEvent.model_validate(r) for r in rows if r.get("call_id") == call_id]
        items.sort(key=lambda e: e.sequence_number)
        return items


class TranscriptRepository:
    """Append-only JSONL repository for transcript segments with deduplication."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    async def append(self, segment: TranscriptSegment) -> TranscriptSegment:
        self._storage.append_jsonl(TRANSCRIPTS_LOG, segment.model_dump(mode="json"))
        return segment

    async def list_by_call(self, call_id: str) -> list[TranscriptSegment]:
        rows = self._storage.read_jsonl(TRANSCRIPTS_LOG)
        by_seg_id: dict[str, TranscriptSegment] = {}
        for r in rows:
            if r.get("call_id") != call_id:
                continue
            seg = TranscriptSegment.model_validate(r)
            existing = by_seg_id.get(seg.segment_id)
            if existing is None or seg.final or not existing.final:
                by_seg_id[seg.segment_id] = seg
        items = list(by_seg_id.values())
        items.sort(key=lambda s: s.timestamp)
        return items

    async def search(self, query: str) -> list[TranscriptSegment]:
        q = query.strip().lower()
        if not q:
            return []
        rows = self._storage.read_jsonl(TRANSCRIPTS_LOG)
        matches: list[TranscriptSegment] = []
        seen: set[str] = set()
        for r in rows:
            seg = TranscriptSegment.model_validate(r)
            if seg.final and q in seg.text.lower() and seg.segment_id not in seen:
                seen.add(seg.segment_id)
                matches.append(seg)
        return matches

    async def search_by_call(self, call_id: str, query: str) -> list[TranscriptSegment]:
        matches = await self.search(query)
        return [m for m in matches if m.call_id == call_id]


class CallMetricsRepository:
    """Persists latest technical metrics snapshots per call."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    async def save(self, snapshot: CallMetricsSnapshot) -> CallMetricsSnapshot:
        self._storage.append_jsonl(METRICS_LOG, snapshot.model_dump(mode="json"))
        return snapshot

    async def get_latest(self, call_id: str) -> CallMetricsSnapshot | None:
        rows = self._storage.read_jsonl(METRICS_LOG)
        latest: CallMetricsSnapshot | None = None
        for r in rows:
            if r.get("call_id") == call_id:
                latest = CallMetricsSnapshot.model_validate(r)
        return latest


class CallMonitoringSettingsService:
    """Persists global live monitoring settings via StorageProvider."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def get_settings(self) -> CallMonitoringSettings:
        raw = self._storage.read_json(MONITORING_SETTINGS_PATH, default=None)
        if not raw:
            return CallMonitoringSettings()
        return CallMonitoringSettings.model_validate(raw)

    def update_settings(self, settings: CallMonitoringSettings) -> CallMonitoringSettings:
        # Recording remains disabled by default unless explicitly opted in
        self._storage.write_json(MONITORING_SETTINGS_PATH, settings.model_dump(mode="json"))
        return settings
