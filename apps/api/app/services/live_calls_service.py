"""Live Calls, CallSession, Transcript, Metrics, Authorization, and Control services."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import uuid

from app.core.config import Settings
from app.providers.telephony import TelephonyProviderFactory, TelephonyUnavailableError
from app.repositories.call_session_repository import (
    CallEventRepository,
    CallMetricsRepository,
    CallSessionRepository,
    TranscriptRepository,
)
from app.schemas.live_calls import (
    CallDirection,
    CallEventType,
    CallMetricsSnapshot,
    CallSession,
    CallSessionStatus,
    CallSessionType,
    LiveCallsStats,
    NormalizedCallEvent,
    TranscriptSegment,
    TranscriptSpeaker,
)
from app.services.lead_validation import mask_phone
from app.services.ws_manager import WebSocketManager, monitoring_ws_hub

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {
    CallSessionStatus.CREATED,
    CallSessionStatus.INITIATING,
    CallSessionStatus.RINGING,
    CallSessionStatus.ANSWERED,
    CallSessionStatus.ACTIVE,
    CallSessionStatus.ON_HOLD,
    CallSessionStatus.TRANSFERRING,
}

TERMINAL_STATUSES = {
    CallSessionStatus.COMPLETED,
    CallSessionStatus.FAILED,
    CallSessionStatus.BUSY,
    CallSessionStatus.NO_ANSWER,
    CallSessionStatus.TERMINATED,
    CallSessionStatus.DISCONNECTED,
}


class CallSessionNotFoundError(LookupError):
    """Raised when a call session ID is not found."""


class CallControlUnsupportedError(ValueError):
    """Raised when a provider does not support the requested call control."""


class CallAuthorizationError(PermissionError):
    """Raised when monitoring/control access is unauthorized."""


class CallAuthorizationService:
    """Validates operator authorization for live monitoring and controls."""

    @staticmethod
    def authorize(settings: Settings, token: str | None) -> bool:
        if not settings.require_auth:
            return True
        if not token:
            return False
        cleaned = token.replace("Bearer ", "").strip()
        return cleaned == settings.agentvoice_secret_key


class CallSessionService:
    """Manages active and completed CallSession lifecycles and normalized events."""

    _seq_counters: dict[str, int] = {}
    _seen_event_ids: set[str] = set()

    def __init__(
        self,
        session_repo: CallSessionRepository,
        event_repo: CallEventRepository,
        transcript_repo: TranscriptRepository,
        metrics_repo: CallMetricsRepository,
        ws_hub: WebSocketManager = monitoring_ws_hub,
    ) -> None:
        self._sessions = session_repo
        self._events = event_repo
        self._transcripts = transcript_repo
        self._metrics = metrics_repo
        self._ws = ws_hub

    def _next_seq(self, call_id: str) -> int:
        seq = self._seq_counters.get(call_id, 0) + 1
        self._seq_counters[call_id] = seq
        return seq

    async def create_session(
        self,
        *,
        agent_id: str,
        session_type: CallSessionType = CallSessionType.BROWSER,
        direction: CallDirection = CallDirection.INBOUND,
        provider: str = "browser",
        conversation_id: str | None = None,
        campaign_id: str | None = None,
        lead_id: str | None = None,
        caller_number: str | None = None,
        destination_number: str | None = None,
        external_call_id: str | None = None,
    ) -> CallSession:
        now = datetime.now(timezone.utc)
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        session = CallSession(
            id=call_id,
            external_call_id=external_call_id,
            campaign_id=campaign_id,
            lead_id=lead_id,
            agent_id=agent_id,
            conversation_id=conversation_id,
            session_type=session_type,
            direction=direction,
            status=CallSessionStatus.ACTIVE
            if session_type == CallSessionType.BROWSER
            else CallSessionStatus.INITIATING,
            caller_number_masked=mask_phone(caller_number),
            destination_number_masked=mask_phone(destination_number),
            started_at=now,
            answered_at=now if session_type == CallSessionType.BROWSER else None,
            current_agent_state="LISTENING" if session_type == CallSessionType.BROWSER else "IDLE",
            last_activity_at=now,
            provider=provider,
            recording_enabled=False,  # Always disabled by default
        )
        created = await self._sessions.create(session)
        await self.publish_event(
            call_id=created.id,
            event_type=CallEventType.CALL_CREATED,
            source=provider,
            payload={"status": created.status.value, "session_type": session_type.value},
            metadata={"campaign_id": campaign_id, "agent_id": agent_id},
        )
        return created

    async def get_session(self, call_id: str) -> CallSession:
        session = await self._sessions.get_by_id(call_id)
        if session is None:
            raise CallSessionNotFoundError(f"Call session '{call_id}' was not found.")
        return session

    async def list_sessions(
        self,
        *,
        active_only: bool = False,
        status: CallSessionStatus | None = None,
        campaign_id: str | None = None,
        agent_id: str | None = None,
        search: str | None = None,
    ) -> list[CallSession]:
        sessions = await self._sessions.list_all()
        if active_only:
            sessions = [s for s in sessions if s.status in ACTIVE_STATUSES]
        if status is not None:
            sessions = [s for s in sessions if s.status == status]
        if campaign_id is not None:
            sessions = [s for s in sessions if s.campaign_id == campaign_id]
        if agent_id is not None:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        if search and search.strip():
            q = search.strip().lower()
            sessions = [
                s
                for s in sessions
                if q in s.id.lower()
                or q in (s.campaign_id or "").lower()
                or q in s.agent_id.lower()
                or q in s.caller_number_masked.lower()
            ]
        return sessions

    async def get_stats(self) -> LiveCallsStats:
        sessions = await self._sessions.list_all()
        return LiveCallsStats(
            active_calls=sum(1 for s in sessions if s.status in ACTIVE_STATUSES),
            ringing_calls=sum(1 for s in sessions if s.status == CallSessionStatus.RINGING),
            in_progress_calls=sum(
                1 for s in sessions if s.status in (CallSessionStatus.ACTIVE, CallSessionStatus.ANSWERED)
            ),
            on_hold_calls=sum(1 for s in sessions if s.status == CallSessionStatus.ON_HOLD),
            attention_required_calls=sum(
                1 for s in sessions if s.flagged_for_review or s.status == CallSessionStatus.FAILED
            ),
            recently_completed_calls=sum(
                1 for s in sessions if s.status in TERMINAL_STATUSES
            ),
            provider_status="Browser Voice Ready · Telephony Phase 9",
        )

    async def publish_event(
        self,
        *,
        call_id: str,
        event_type: CallEventType,
        source: str = "voice_engine",
        payload: dict | None = None,
        metadata: dict | None = None,
        event_id: str | None = None,
    ) -> NormalizedCallEvent | None:
        eid = event_id or f"cevt_{uuid.uuid4().hex[:12]}"
        if eid in self._seen_event_ids:
            return None
        self._seen_event_ids.add(eid)
        if len(self._seen_event_ids) > 10000:
            self._seen_event_ids.clear()

        seq = self._next_seq(call_id)
        event = NormalizedCallEvent(
            event_id=eid,
            call_id=call_id,
            event_type=event_type,
            sequence_number=seq,
            source=source,
            payload=payload or {},
            metadata=metadata or {},
        )
        await self._events.append(event)
        self._ws.publish_nonblocking(
            {
                "type": "CALL_EVENT",
                "event_type": event.event_type.value,
                "call_id": call_id,
                "timestamp": event.timestamp.isoformat(),
                "sequence_number": seq,
                "data": event.payload,
                "metadata": event.metadata,
            }
        )
        return event

    async def update_agent_state(self, call_id: str, agent_state: str) -> None:
        session = await self._sessions.get_by_id(call_id)
        if not session:
            return
        speaker = (
            TranscriptSpeaker.CUSTOMER
            if agent_state in ("SPEECH_DETECTED", "TRANSCRIBING")
            else TranscriptSpeaker.AI_AGENT
            if agent_state in ("THINKING", "GENERATING_SPEECH", "SPEAKING")
            else None
        )
        await self._sessions.update(
            session.model_copy(
                update={
                    "current_agent_state": agent_state,
                    "current_speaker": speaker,
                    "last_activity_at": datetime.now(timezone.utc),
                }
            )
        )
        self._ws.publish_nonblocking(
            {
                "type": "CALL_STATUS_CHANGED",
                "call_id": call_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sequence_number": self._next_seq(call_id),
                "data": {
                    "status": session.status.value,
                    "agent_state": agent_state,
                    "current_speaker": speaker.value if speaker else None,
                },
                "metadata": {"campaign_id": session.campaign_id, "agent_id": session.agent_id},
            }
        )

    async def record_transcript_segment(
        self,
        *,
        call_id: str,
        speaker: TranscriptSpeaker,
        text: str,
        final: bool = True,
        segment_id: str | None = None,
        language: str | None = None,
        source: str = "stt",
    ) -> TranscriptSegment:
        seg = TranscriptSegment(
            segment_id=segment_id or f"seg_{uuid.uuid4().hex[:12]}",
            call_id=call_id,
            speaker=speaker,
            text=text,
            final=final,
            language=language,
            source=source,
        )
        await self._transcripts.append(seg)
        self._ws.publish_nonblocking(
            {
                "type": "TRANSCRIPT_SEGMENT",
                "call_id": call_id,
                "timestamp": seg.timestamp.isoformat(),
                "sequence_number": self._next_seq(call_id),
                "data": seg.model_dump(mode="json"),
            }
        )
        return seg

    async def record_metrics(
        self,
        *,
        call_id: str,
        stt_ms: int | None = None,
        llm_ttft_ms: int | None = None,
        llm_total_ms: int | None = None,
        tts_ms: int | None = None,
        end_to_end_ms: int | None = None,
    ) -> CallMetricsSnapshot:
        snap = CallMetricsSnapshot(
            call_id=call_id,
            stt_latency_ms=stt_ms,
            llm_ttft_ms=llm_ttft_ms,
            llm_total_ms=llm_total_ms,
            tts_latency_ms=tts_ms,
            end_to_end_ms=end_to_end_ms,
        )
        await self._metrics.save(snap)
        self._ws.publish_nonblocking(
            {
                "type": "CALL_METRICS",
                "call_id": call_id,
                "timestamp": snap.updated_at.isoformat(),
                "sequence_number": self._next_seq(call_id),
                "data": snap.model_dump(mode="json"),
            }
        )
        return snap

    async def end_session(
        self,
        call_id: str,
        *,
        status: CallSessionStatus = CallSessionStatus.COMPLETED,
        end_reason: str = "Session ended",
        outcome: str | None = None,
    ) -> CallSession:
        session = await self.get_session(call_id)
        if session.status in TERMINAL_STATUSES:
            return session
        now = datetime.now(timezone.utc)
        duration = max(0, int((now - session.started_at).total_seconds()))
        updated = await self._sessions.update(
            session.model_copy(
                update={
                    "status": status,
                    "ended_at": now,
                    "duration_seconds": duration,
                    "current_agent_state": "COMPLETED",
                    "current_speaker": None,
                    "end_reason": end_reason,
                    "outcome": outcome or session.outcome,
                }
            )
        )
        await self.publish_event(
            call_id=call_id,
            event_type=CallEventType.CALL_ENDED,
            source=session.provider,
            payload={"status": status.value, "duration_seconds": duration, "end_reason": end_reason},
            metadata={"campaign_id": session.campaign_id, "agent_id": session.agent_id},
        )
        return updated or session


class CallControlService:
    """Performs capability-checked call controls (terminate, hold, resume, transfer, flag)."""

    def __init__(self, session_service: CallSessionService, session_repo: CallSessionRepository) -> None:
        self._sessions = session_service
        self._repo = session_repo

    async def terminate_call(self, call_id: str, reason: str = "Operator terminated") -> CallSession:
        session = await self._sessions.get_session(call_id)
        if session.session_type == CallSessionType.TELEPHONY and session.provider_call_id:
            try:
                provider = TelephonyProviderFactory.create(session.provider)
                await provider.terminate_call(session.provider_call_id)
            except TelephonyUnavailableError as exc:
                raise CallControlUnsupportedError(str(exc)) from exc
        return await self._sessions.end_session(
            call_id, status=CallSessionStatus.TERMINATED, end_reason=reason
        )

    async def hold_call(self, call_id: str) -> CallSession:
        session = await self._sessions.get_session(call_id)
        if session.session_type == CallSessionType.BROWSER:
            raise CallControlUnsupportedError(
                "Hold is not supported for browser microphone sessions."
            )
        raise CallControlUnsupportedError(
            f"Provider '{session.provider}' does not support call hold."
        )

    async def resume_call(self, call_id: str) -> CallSession:
        session = await self._sessions.get_session(call_id)
        if session.status != CallSessionStatus.ON_HOLD:
            raise CallControlUnsupportedError("Call is not currently on hold.")
        raise CallControlUnsupportedError(
            f"Provider '{session.provider}' does not support resuming held calls."
        )

    async def transfer_call(self, call_id: str, destination: str, reason: str) -> CallSession:
        session = await self._sessions.get_session(call_id)
        raise CallControlUnsupportedError(
            f"Human transfer to '{destination}' is unavailable: provider '{session.provider}' "
            "does not have an authorized SIP/PBX transfer trunk configured."
        )

    async def flag_call(self, call_id: str, reason: str) -> CallSession:
        session = await self._sessions.get_session(call_id)
        updated = await self._repo.update(
            session.model_copy(update={"flagged_for_review": True, "flag_reason": reason})
        )
        await self._sessions.publish_event(
            call_id=call_id,
            event_type=CallEventType.CALL_WARNING,
            source="operator",
            payload={"flagged": True, "reason": reason},
        )
        return updated or session
