"""Voice session REST and WebSocket bidirectional audio streaming endpoints."""

import base64
import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from app.api.v1.conversations import get_conversation_service
from app.api.v1.live_calls import get_call_session_service
from app.api.v1.speech import get_audio_settings_service, get_stt_service, get_tts_service
from app.core.config import Settings, get_settings
from app.schemas.live_calls import (
    CallDirection,
    CallEventType,
    CallSessionStatus,
    CallSessionType,
    TranscriptSpeaker,
)
from app.schemas.response import ApiResponse, ok
from app.schemas.speech import VoiceSessionCreate, VoiceSessionInfo, VoiceSessionState
from app.services.conversation_service import ConversationService
from app.services.live_calls_service import CallSessionService
from app.services.speech_service import AudioSettingsService, STTService, TTSService
from app.services.voice_session_manager import (
    AudioSessionManager,
    VoiceConversationService,
    VoiceSessionNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

_session_manager = AudioSessionManager()


def get_voice_service(
    conversation_service: ConversationService = Depends(get_conversation_service),
    stt_service: STTService = Depends(get_stt_service),
    tts_service: TTSService = Depends(get_tts_service),
) -> VoiceConversationService:
    """Dependency providing VoiceConversationService."""
    return VoiceConversationService(
        session_manager=_session_manager,
        conversation_service=conversation_service,
        stt_service=stt_service,
        tts_service=tts_service,
    )


@router.post("/sessions", response_model=ApiResponse[VoiceSessionInfo], status_code=status.HTTP_201_CREATED)
async def create_voice_session(
    payload: VoiceSessionCreate,
    settings: Settings = Depends(get_settings),
    audio_svc: AudioSettingsService = Depends(get_audio_settings_service),
    voice_svc: VoiceConversationService = Depends(get_voice_service),
) -> ApiResponse[VoiceSessionInfo]:
    """Create and validate a new real-time voice session."""
    info = await voice_svc.start_session(payload, audio_svc.get_settings())
    return ok(info, version=settings.app_version)


@router.get("/sessions/{session_id}", response_model=ApiResponse[VoiceSessionInfo])
async def get_voice_session(
    session_id: str,
    settings: Settings = Depends(get_settings),
    voice_svc: VoiceConversationService = Depends(get_voice_service),
) -> ApiResponse[VoiceSessionInfo]:
    """Retrieve current status of a voice session."""
    return ok(voice_svc.get_session(session_id), version=settings.app_version)


@router.delete("/sessions/{session_id}", response_model=ApiResponse[dict[str, str | bool]])
async def delete_voice_session(
    session_id: str,
    settings: Settings = Depends(get_settings),
    voice_svc: VoiceConversationService = Depends(get_voice_service),
) -> ApiResponse[dict[str, str | bool]]:
    """Terminate and clean up a voice session."""
    removed = voice_svc.end_session(session_id)
    if not removed:
        raise VoiceSessionNotFoundError(f"Voice session '{session_id}' was not found.")
    return ok({"deleted": True, "session_id": session_id}, version=settings.app_version)


@router.websocket("/sessions/{session_id}/stream")
async def voice_session_stream(
    websocket: WebSocket,
    session_id: str,
    voice_svc: VoiceConversationService = Depends(get_voice_service),
    call_svc: CallSessionService = Depends(get_call_session_service),
) -> None:
    """Bidirectional WebSocket audio and control stream for a voice session."""
    await websocket.accept()

    try:
        ctx = _session_manager.get(session_id)
    except VoiceSessionNotFoundError as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close(code=4404)
        return

    call_session = None
    try:
        call_session = await call_svc.create_session(
            agent_id=ctx.info.agent_id,
            session_type=CallSessionType.BROWSER,
            direction=CallDirection.INBOUND,
            provider="browser",
            conversation_id=ctx.info.conversation_id,
            external_call_id=session_id,
        )
    except Exception as exc:
        logger.debug("Live call monitoring registration skipped: %s", exc)

    async def _forward_monitoring(event: dict[str, object]) -> None:
        if call_session is None:
            return
        try:
            ev_type = event.get("type")
            if ev_type == "session.state":
                state_val = str(event.get("state") or "")
                await call_svc.update_agent_state(call_session.id, state_val)
            elif ev_type == "transcript.final":
                await call_svc.record_transcript_segment(
                    call_id=call_session.id,
                    speaker=TranscriptSpeaker.CUSTOMER,
                    text=str(event.get("text") or ""),
                    final=True,
                    language=str(event.get("language")) if event.get("language") else None,
                    source="stt",
                )
            elif ev_type == "response.text":
                await call_svc.record_transcript_segment(
                    call_id=call_session.id,
                    speaker=TranscriptSpeaker.AI_AGENT,
                    text=str(event.get("text") or ""),
                    final=True,
                    source="llm",
                )
            elif ev_type == "metrics" and isinstance(event.get("data"), dict):
                m = event["data"]
                await call_svc.record_metrics(
                    call_id=call_session.id,
                    stt_ms=m.get("stt_ms"),
                    llm_ttft_ms=m.get("llm_ttft_ms"),
                    llm_total_ms=m.get("llm_total_ms"),
                    tts_ms=m.get("tts_ms"),
                    end_to_end_ms=m.get("total_ms"),
                )
            elif ev_type == "error":
                await call_svc.publish_event(
                    call_id=call_session.id,
                    event_type=CallEventType.CALL_ERROR,
                    source="voice_engine",
                    payload={"message": str(event.get("message") or "Voice error")},
                )
        except Exception as exc:
            logger.debug("Live call monitoring forward error: %s", exc)

    async def emit(event: dict[str, object]) -> None:
        if event.get("type") == "response.audio.wav":
            wav_bytes = event.get("bytes")
            if isinstance(wav_bytes, (bytes, bytearray)):
                await websocket.send_bytes(bytes(wav_bytes))
            return
        await websocket.send_json(event)
        await _forward_monitoring(event)

    await VoiceConversationService._set_state(ctx, VoiceSessionState.LISTENING, emit)

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            if "bytes" in message and message["bytes"] is not None:
                await voice_svc.process_audio_chunk(
                    session_id,
                    message["bytes"],
                    ctx.sample_rate,
                    emit,
                )
            elif "text" in message and message["text"] is not None:
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    await emit({"type": "error", "message": "Invalid JSON control frame."})
                    continue

                msg_type = data.get("type")
                if msg_type == "audio.input" and isinstance(data.get("data"), str):
                    try:
                        pcm = base64.b64decode(data["data"])
                    except Exception:
                        await emit({"type": "error", "message": "Invalid base64 audio payload."})
                        continue
                    sr = int(data.get("sample_rate") or ctx.sample_rate)
                    await voice_svc.process_audio_chunk(session_id, pcm, sr, emit)
                elif msg_type == "session.interrupt":
                    await voice_svc.interrupt_session(session_id, emit)
                elif msg_type == "session.end":
                    await VoiceConversationService._set_state(
                        ctx, VoiceSessionState.COMPLETED, emit
                    )
                    break
    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected (session=%s)", session_id)
    finally:
        if call_session is not None:
            try:
                await call_svc.end_session(
                    call_session.id,
                    status=CallSessionStatus.COMPLETED,
                    end_reason="Voice session ended",
                )
            except Exception as exc:
                logger.debug("Live call monitoring end_session error: %s", exc)
        voice_svc.end_session(session_id)
