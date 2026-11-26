"""Real-time VoiceSessionManager & VoiceConversationService.

Coordinates:
- Explicit 11-state voice session machine
- Pre-speech ring buffer + VAD utterance boundary detection
- STT -> ConversationService (Phase 3) -> TTS pipeline
- Barge-in / interruption cancellation
- Stage latency measurement
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import time
import uuid

from app.providers.vad import VADProvider, VADProviderFactory
from app.schemas.agent import Agent
from app.schemas.llm import ConversationCreate, SendMessageRequest
from app.schemas.speech import (
    AudioSettings,
    LatencyMetrics,
    VoiceSessionCreate,
    VoiceSessionInfo,
    VoiceSessionState,
)
from app.services.conversation_service import ConversationService
from app.services.speech_service import STTService, TTSService

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, object]], Awaitable[None]]


@dataclass
class VoiceSessionContext:
    """In-memory runtime state for an active voice session."""

    info: VoiceSessionInfo
    agent: Agent
    audio_settings: AudioSettings
    vad: VADProvider
    pre_roll: deque[bytes] = field(default_factory=lambda: deque(maxlen=8))
    utterance_buffer: bytearray = field(default_factory=bytearray)
    in_speech: bool = False
    active_turn_task: asyncio.Task[None] | None = None
    sample_rate: int = 16000


class VoiceSessionNotFoundError(LookupError):
    """Raised when a voice session ID does not exist."""


class AudioSessionManager:
    """In-memory registry of active voice sessions."""

    _sessions: dict[str, VoiceSessionContext] = {}

    def create(
        self,
        *,
        agent: Agent,
        conversation_id: str,
        model_id: str,
        audio_settings: AudioSettings,
    ) -> VoiceSessionContext:
        session_id = f"vsess_{uuid.uuid4().hex[:12]}"
        # Precedence: Agent-specific > User-level audio defaults > Provider defaults
        tts_provider = agent.voice.provider or audio_settings.tts_provider
        voice_id = (
            agent.voice.voice_id
            if agent.voice.voice_id and agent.voice.voice_id != "default"
            else audio_settings.default_voice_id
        )

        vad = VADProviderFactory.create(
            "energy",
            threshold=audio_settings.vad_threshold,
            min_speech_ms=audio_settings.min_speech_ms,
            min_silence_ms=audio_settings.min_silence_ms,
            max_utterance_ms=audio_settings.max_utterance_ms,
        )

        info = VoiceSessionInfo(
            session_id=session_id,
            agent_id=agent.id,
            conversation_id=conversation_id,
            model_id=model_id,
            state=VoiceSessionState.IDLE,
            stt_provider=audio_settings.stt_provider,
            tts_provider=tts_provider,
            voice_id=voice_id,
        )
        ctx = VoiceSessionContext(
            info=info,
            agent=agent,
            audio_settings=audio_settings,
            vad=vad,
            sample_rate=audio_settings.input_sample_rate,
        )
        self._sessions[session_id] = ctx
        return ctx

    def get(self, session_id: str) -> VoiceSessionContext:
        ctx = self._sessions.get(session_id)
        if ctx is None:
            raise VoiceSessionNotFoundError(f"Voice session '{session_id}' was not found.")
        return ctx

    def remove(self, session_id: str) -> bool:
        ctx = self._sessions.pop(session_id, None)
        if ctx is None:
            return False
        if ctx.active_turn_task and not ctx.active_turn_task.done():
            ctx.active_turn_task.cancel()
        return True


class VoiceConversationService:
    """Orchestrates real-time voice turns using ConversationService, STTService, and TTSService."""

    def __init__(
        self,
        session_manager: AudioSessionManager,
        conversation_service: ConversationService,
        stt_service: STTService,
        tts_service: TTSService,
    ) -> None:
        self._sessions = session_manager
        self._conversations = conversation_service
        self._stt = stt_service
        self._tts = tts_service

    async def start_session(
        self, payload: VoiceSessionCreate, audio_settings: AudioSettings
    ) -> VoiceSessionInfo:
        """Validate agent/model via ConversationService and open a voice session."""
        if payload.conversation_id:
            conv = await self._conversations.get_conversation(payload.conversation_id)
            agent, model_id = await self._conversations._resolve_agent_and_model(
                payload.agent_id,
                override_model_id=conv.model_id,
                allow_draft_preview=payload.allow_draft_preview,
            )
        else:
            conv = await self._conversations.create_conversation(
                payload.agent_id,
                ConversationCreate(title="Voice Session"),
                allow_draft_preview=payload.allow_draft_preview,
            )
            agent = await self._conversations._agents.get_agent(payload.agent_id)
            model_id = conv.model_id

        ctx = self._sessions.create(
            agent=agent,
            conversation_id=conv.id,
            model_id=model_id,
            audio_settings=audio_settings,
        )
        logger.info(
            "Created voice session %s (agent=%s, conv=%s, model=%s)",
            ctx.info.session_id,
            agent.id,
            conv.id,
            model_id,
        )
        return ctx.info

    def get_session(self, session_id: str) -> VoiceSessionInfo:
        return self._sessions.get(session_id).info

    def end_session(self, session_id: str) -> bool:
        return self._sessions.remove(session_id)

    @staticmethod
    async def _set_state(
        ctx: VoiceSessionContext,
        state: VoiceSessionState,
        emit: EventCallback,
    ) -> None:
        ctx.info.state = state
        ctx.info.updated_at = datetime.now(timezone.utc).isoformat()
        await emit({"type": "session.state", "state": state.value, "session_id": ctx.info.session_id})

    async def interrupt_session(self, session_id: str, emit: EventCallback) -> None:
        """Cancel any in-flight LLM/TTS turn immediately (barge-in)."""
        ctx = self._sessions.get(session_id)
        if ctx.active_turn_task and not ctx.active_turn_task.done():
            ctx.active_turn_task.cancel()
            try:
                await ctx.active_turn_task
            except asyncio.CancelledError:
                pass
            ctx.active_turn_task = None
        await self._set_state(ctx, VoiceSessionState.INTERRUPTED, emit)
        await emit({"type": "response.interrupted", "session_id": session_id})
        await self._set_state(ctx, VoiceSessionState.LISTENING, emit)

    async def process_audio_chunk(
        self,
        session_id: str,
        pcm_chunk: bytes,
        sample_rate: int,
        emit: EventCallback,
    ) -> None:
        """Feed PCM s16le audio into VAD, handle barge-in, and trigger turn on speech_end."""
        ctx = self._sessions.get(session_id)
        ctx.sample_rate = sample_rate
        vad_res = await ctx.vad.detect_speech(pcm_chunk, sample_rate=sample_rate)

        if vad_res.event == "speech_start":
            # Barge-in if AI is currently thinking/generating/speaking
            if ctx.info.state in (
                VoiceSessionState.THINKING,
                VoiceSessionState.GENERATING_SPEECH,
                VoiceSessionState.SPEAKING,
            ):
                await self.interrupt_session(session_id, emit)

            ctx.in_speech = True
            ctx.utterance_buffer.clear()
            for pre in ctx.pre_roll:
                ctx.utterance_buffer.extend(pre)
            ctx.utterance_buffer.extend(pcm_chunk)
            await self._set_state(ctx, VoiceSessionState.SPEECH_DETECTED, emit)
            return

        if vad_res.event == "speech_continue" and ctx.in_speech:
            ctx.utterance_buffer.extend(pcm_chunk)
            return

        if vad_res.event == "speech_end" and ctx.in_speech:
            ctx.utterance_buffer.extend(pcm_chunk)
            ctx.in_speech = False
            utterance = bytes(ctx.utterance_buffer)
            ctx.utterance_buffer.clear()
            ctx.pre_roll.clear()

            if ctx.active_turn_task and not ctx.active_turn_task.done():
                ctx.active_turn_task.cancel()

            ctx.active_turn_task = asyncio.create_task(
                self._run_voice_turn(ctx, utterance, sample_rate, emit)
            )
            return

        # Idle/listening: keep pre-roll ring buffer so start of speech is not clipped
        ctx.pre_roll.append(pcm_chunk)

    async def _run_voice_turn(
        self,
        ctx: VoiceSessionContext,
        utterance_pcm: bytes,
        sample_rate: int,
        emit: EventCallback,
    ) -> None:
        """Execute STT -> ConversationService -> TTS for one user utterance."""
        turn_start = time.monotonic()
        try:
            # 1. STT
            await self._set_state(ctx, VoiceSessionState.TRANSCRIBING, emit)
            stt_start = time.monotonic()
            stt_res = await self._stt.transcribe(
                utterance_pcm,
                {
                    "format": "pcm_s16le",
                    "sample_rate": sample_rate,
                    "model": ctx.audio_settings.stt_model,
                    "language": ctx.agent.language.primary_language,
                    "hinglish_script_mode": ctx.audio_settings.hinglish_script_mode,
                },
            )
            stt_ms = int((time.monotonic() - stt_start) * 1000)

            transcript = stt_res.text.strip()
            if not transcript:
                await self._set_state(ctx, VoiceSessionState.LISTENING, emit)
                return

            await emit(
                {
                    "type": "transcript.final",
                    "text": transcript,
                    "language": stt_res.language,
                    "duration_seconds": stt_res.duration_seconds,
                }
            )

            # 2. LLM via Phase 3 ConversationService
            await self._set_state(ctx, VoiceSessionState.THINKING, emit)
            llm_start = time.monotonic()
            llm_ttft_ms = 0
            reply_chunks: list[str] = []

            async for event in self._conversations.stream_message(
                ctx.info.conversation_id,
                SendMessageRequest(content=transcript, allow_draft_preview=True),
            ):
                ev_type = event.get("event")
                if ev_type == "delta":
                    if llm_ttft_ms == 0:
                        llm_ttft_ms = int((time.monotonic() - llm_start) * 1000)
                    reply_chunks.append(str(event.get("content") or ""))
                elif ev_type == "error":
                    raise RuntimeError(str(event.get("message") or "LLM generation failed"))

            llm_total_ms = int((time.monotonic() - llm_start) * 1000)
            reply_text = "".join(reply_chunks).strip()
            if not reply_text:
                await self._set_state(ctx, VoiceSessionState.LISTENING, emit)
                return

            await emit({"type": "response.text", "text": reply_text})

            # 3. TTS
            await self._set_state(ctx, VoiceSessionState.GENERATING_SPEECH, emit)
            tts_start = time.monotonic()
            speed = (
                ctx.agent.voice.speed
                if ctx.agent.voice.speed != 1.0
                else ctx.audio_settings.default_speed
            )
            pitch = (
                ctx.agent.voice.pitch
                if ctx.agent.voice.pitch != 1.0
                else ctx.audio_settings.default_pitch
            )
            wav_bytes = await self._tts.synthesize(
                reply_text,
                {
                    "provider": ctx.info.tts_provider,
                    "voice_id": ctx.info.voice_id,
                    "speed": speed,
                    "pitch": pitch,
                },
            )
            tts_ms = int((time.monotonic() - tts_start) * 1000)

            total_ms = int((time.monotonic() - turn_start) * 1000)
            metrics = LatencyMetrics(
                vad_ms=ctx.audio_settings.min_silence_ms,
                stt_ms=stt_ms,
                llm_ttft_ms=llm_ttft_ms,
                llm_total_ms=llm_total_ms,
                tts_ms=tts_ms,
                total_ms=total_ms,
            )
            ctx.info.last_latency = metrics

            await self._set_state(ctx, VoiceSessionState.SPEAKING, emit)
            await emit({"type": "metrics", "data": metrics.model_dump(mode="json")})
            await emit({"type": "response.audio.wav", "bytes": wav_bytes})
            await self._set_state(ctx, VoiceSessionState.LISTENING, emit)

        except asyncio.CancelledError:
            logger.info("Voice turn cancelled (session=%s)", ctx.info.session_id)
            raise
        except Exception as exc:
            logger.warning("Voice turn error (session=%s): %s", ctx.info.session_id, exc)
            await self._set_state(ctx, VoiceSessionState.ERROR, emit)
            await emit({"type": "error", "message": str(exc)})
            await self._set_state(ctx, VoiceSessionState.LISTENING, emit)
