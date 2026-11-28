"""Bidirectional AI voice bridge over Asterisk 23 ARI ExternalMedia RTP."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import struct
import time
from typing import Any

from app.providers.telephony.asterisk_ari import AsteriskARIProvider
from app.providers.telephony.media import AudioFrameBuffer, TelephonyMediaAdapter
from app.services.conversation_service import ConversationService
from app.services.speech_service import STTService, TTSService

logger = logging.getLogger(__name__)

_RTP_HEADER_SIZE = 12


def _strip_rtp_header(packet: bytes) -> bytes:
    if len(packet) <= _RTP_HEADER_SIZE:
        return b""
    cc = packet[0] & 0x0F
    offset = _RTP_HEADER_SIZE + cc * 4
    if len(packet) <= offset:
        return b""
    return packet[offset:]


def _build_rtp_packet(
    payload: bytes,
    *,
    seq: int,
    timestamp: int,
    ssrc: int = 0x41475643,
    payload_type: int = 0,
) -> bytes:
    header = struct.pack(
        "!BBHII",
        0x80,
        payload_type & 0x7F,
        seq & 0xFFFF,
        timestamp & 0xFFFFFFFF,
        ssrc,
    )
    return header + payload


def _pcm16_rms(pcm16: bytes) -> float:
    if len(pcm16) < 2:
        return 0.0
    count = len(pcm16) // 2
    samples = struct.unpack(f"<{count}h", pcm16[: count * 2])
    return (sum(s * s for s in samples) / max(1, count)) ** 0.5


@dataclass
class AICallBridgeSession:
    """Tracks a single active AI call media bridge and audio pipelines."""

    call_id: str
    channel_id: str
    agent_id: str
    bridge_id: str | None = None
    external_media_channel_id: str | None = None
    conversation_id: str | None = None
    active: bool = True
    barge_in_count: int = 0
    turns_completed: int = 0
    inbound_buffer: AudioFrameBuffer = field(default_factory=lambda: AudioFrameBuffer(max_frames=200, frame_bytes=320))
    outbound_queue: asyncio.Queue[bytes] = field(default_factory=lambda: asyncio.Queue(maxsize=250))
    _speech_pcm: bytearray = field(default_factory=bytearray)
    _in_speech: bool = False
    _silence_frames: int = 0
    _speaking_tts: bool = False
    _seq: int = 1
    _timestamp: int = 0
    _task: asyncio.Task[None] | None = None

    def trigger_barge_in(self) -> None:
        """Interrupt active AI TTS playback immediately when caller speaks."""
        if self._speaking_tts or not self.outbound_queue.empty():
            self._speaking_tts = False
            self.barge_in_count += 1
            while not self.outbound_queue.empty():
                try:
                    self.outbound_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break


class AICallBridgeManager:
    """Manages non-blocking bidirectional audio bridging between Asterisk ARI and AgentVoice AI."""

    def __init__(
        self,
        stt_service: STTService | None = None,
        conversation_service: ConversationService | None = None,
        tts_service: TTSService | None = None,
        *,
        vad_rms_threshold: float = 450.0,
        silence_frames_to_commit: int = 15,
    ) -> None:
        self._stt = stt_service
        self._conversations = conversation_service
        self._tts = tts_service
        self._vad_threshold = vad_rms_threshold
        self._silence_frames = silence_frames_to_commit
        self._sessions: dict[str, AICallBridgeSession] = {}

    def get_session(self, call_id: str) -> AICallBridgeSession | None:
        return self._sessions.get(call_id)

    def list_sessions(self) -> list[dict[str, Any]]:
        return [
            {
                "call_id": s.call_id,
                "channel_id": s.channel_id,
                "agent_id": s.agent_id,
                "bridge_id": s.bridge_id,
                "external_media_channel_id": s.external_media_channel_id,
                "active": s.active,
                "barge_in_count": s.barge_in_count,
                "turns_completed": s.turns_completed,
            }
            for s in self._sessions.values()
        ]

    async def attach_call(
        self,
        *,
        call_id: str,
        channel_id: str,
        agent_id: str,
        provider: AsteriskARIProvider | None = None,
        external_host: str = "127.0.0.1:40000",
    ) -> AICallBridgeSession:
        """Create ARI mixing bridge + ExternalMedia channel when provider is supplied."""
        existing = self._sessions.get(call_id)
        if existing and existing.active:
            return existing

        session = AICallBridgeSession(
            call_id=call_id,
            channel_id=channel_id,
            agent_id=agent_id,
        )
        if provider is not None:
            bridge_info = await provider.create_external_media_bridge(
                channel_id=channel_id,
                external_host=external_host,
                format_name="ulaw",
            )
            session.bridge_id = bridge_info["bridge_id"]
            session.external_media_channel_id = bridge_info["external_media_channel_id"]

        self._sessions[call_id] = session
        return session

    async def process_inbound_rtp(self, call_id: str, rtp_packet: bytes) -> str | None:
        """Decode caller RTP PCMU audio, run VAD + barge-in, and trigger STT->LLM->TTS on utterance end."""
        session = self._sessions.get(call_id)
        if session is None or not session.active:
            return None

        ulaw_payload = _strip_rtp_header(rtp_packet)
        if not ulaw_payload:
            return None

        pcm16 = TelephonyMediaAdapter.decode_to_pcm16_16k(
            ulaw_payload, "PCMU", src_rate=8000
        ).audio_bytes
        session.inbound_buffer.push(pcm16)
        rms = _pcm16_rms(pcm16)

        if rms >= self._vad_threshold:
            session.trigger_barge_in()
            session._in_speech = True
            session._silence_frames = 0
            session._speech_pcm.extend(pcm16)
            return None

        if session._in_speech:
            session._speech_pcm.extend(pcm16)
            session._silence_frames += 1
            if session._silence_frames >= self._silence_frames:
                utterance_pcm = bytes(session._speech_pcm)
                session._speech_pcm.clear()
                session._in_speech = False
                session._silence_frames = 0
                return await self._handle_utterance(session, utterance_pcm)
        return None

    async def _handle_utterance(self, session: AICallBridgeSession, pcm16_16khz: bytes) -> str | None:
        if not pcm16_16khz or self._stt is None:
            return None

        transcript_res = await self._stt.transcribe_pcm16(pcm16_16khz, sample_rate=16000)
        text = (transcript_res.text or "").strip() if hasattr(transcript_res, "text") else str(transcript_res).strip()
        if not text:
            return None

        reply_text = text
        if self._conversations is not None:
            if not session.conversation_id:
                conv = await self._conversations.create_conversation(agent_id=session.agent_id, title=f"Call {session.call_id}")
                session.conversation_id = conv.id
            turn = await self._conversations.send_message(session.conversation_id, content=text)
            reply_text = turn.assistant_message.content

        if self._tts is not None and reply_text:
            session._speaking_tts = True
            tts_audio = await self._tts.synthesize_pcm16(reply_text)
            ulaw = TelephonyMediaAdapter.encode_from_pcm16(
                tts_audio, "PCMU", src_rate=16000, dst_rate=8000
            ).audio_bytes
            for i in range(0, len(ulaw), 160):
                chunk = ulaw[i : i + 160]
                if not chunk:
                    continue
                pkt = _build_rtp_packet(chunk, seq=session._seq, timestamp=session._timestamp)
                session._seq += 1
                session._timestamp += len(chunk)
                if not session.outbound_queue.full():
                    session.outbound_queue.put_nowait(pkt)
            session._speaking_tts = False

        session.turns_completed += 1
        return reply_text

    async def pop_outbound_rtp(self, call_id: str) -> bytes | None:
        session = self._sessions.get(call_id)
        if session is None or not session.active:
            return None
        try:
            return session.outbound_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def detach_call(
        self,
        call_id: str,
        *,
        provider: AsteriskARIProvider | None = None,
    ) -> bool:
        """Clean up audio queues, tasks, and ARI bridge on hangup."""
        session = self._sessions.get(call_id)
        if session is None:
            return False
        session.active = False
        session.trigger_barge_in()
        session.inbound_buffer.clear()
        if session._task and not session._task.done():
            session._task.cancel()
        if provider is not None and session.bridge_id:
            try:
                await provider.destroy_bridge(session.bridge_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to destroy ARI bridge %s: %s", session.bridge_id, exc)
        return True
