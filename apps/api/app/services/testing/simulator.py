"""AI Client Simulator & Full Voice-to-Voice pipeline runner."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any

from app.schemas.llm import ConversationCreate, SendMessageRequest
from app.schemas.testing import CustomerPersona, SimulationTurn, TestScenario
from app.services.conversation_service import ConversationService
from app.services.speech_service import AudioSettingsService, STTService, TTSService
from app.services.ws_manager import WebSocketManager, monitoring_ws_hub

logger = logging.getLogger(__name__)


class ClientSimulatorService:
    """Simulates realistic customer turns through production Conversation, STT, and TTS services."""

    def __init__(
        self,
        conversation_service: ConversationService,
        stt_service: STTService | None = None,
        tts_service: TTSService | None = None,
        audio_settings_service: AudioSettingsService | None = None,
        ws_hub: WebSocketManager = monitoring_ws_hub,
    ) -> None:
        self._conversations = conversation_service
        self._stt = stt_service
        self._tts = tts_service
        self._audio_cfg = audio_settings_service
        self._ws = ws_hub

    @staticmethod
    def generate_customer_utterance(
        persona: CustomerPersona,
        scenario: TestScenario | None,
        turn_index: int,
        previous_agent_reply: str | None = None,
    ) -> str:
        if scenario and scenario.kb_questions and turn_index < len(scenario.kb_questions):
            return scenario.kb_questions[turn_index]
        if persona.sample_utterances:
            return persona.sample_utterances[turn_index % len(persona.sample_utterances)]
        if turn_index == 0:
            return f"Hello, I have a question about {scenario.objective if scenario else 'your service'}."
        if previous_agent_reply and "price" not in previous_agent_reply.lower():
            return "Thanks. Can you also share verified pricing and next steps?"
        return "Okay, thank you for the details."

    async def run_simulation(
        self,
        *,
        run_id: str,
        agent_id: str,
        persona: CustomerPersona,
        scenario: TestScenario | None = None,
        max_turns: int = 4,
        voice_enabled: bool = False,
        interruption_enabled: bool = False,
        stop_event: asyncio.Event | None = None,
    ) -> tuple[list[SimulationTurn], list[str], str]:
        """Run multi-turn simulation via production ConversationService (+ optional STT/TTS)."""
        conv = await self._conversations.create_conversation(
            agent_id,
            ConversationCreate(title=f"TestingLab:{run_id}"),
            allow_draft_preview=True,
        )
        turns: list[SimulationTurn] = []
        errors: list[str] = []
        last_agent_reply: str | None = None
        audio_settings = self._audio_cfg.get_settings() if self._audio_cfg else None

        for idx in range(max_turns):
            if stop_event and stop_event.is_set():
                break

            customer_text = self.generate_customer_utterance(
                persona, scenario, idx, last_agent_reply
            )
            self._ws.publish_nonblocking(
                {
                    "type": "TESTING_EVENT",
                    "run_id": run_id,
                    "stage": "CUSTOMER_SPEAKING",
                    "turn": idx + 1,
                    "text": customer_text,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            stt_ms: int | None = None
            tts_ms: int | None = None
            customer_audio_ok = False
            agent_audio_ok = False
            effective_input = customer_text

            # Optional Audio-to-Audio: synthesize synthetic customer audio -> STT
            if voice_enabled and self._tts and self._stt and audio_settings:
                try:
                    cust_wav = await self._tts.synthesize(
                        customer_text,
                        {
                            "provider": audio_settings.tts_provider,
                            "voice_id": audio_settings.default_voice_id,
                            "speed": 1.0,
                            "pitch": 1.0,
                        },
                    )
                    customer_audio_ok = len(cust_wav) > 44
                    stt_t0 = time.monotonic()
                    stt_res = await self._stt.transcribe(
                        cust_wav,
                        {
                            "format": "wav",
                            "model": audio_settings.stt_model,
                            "language": persona.language,
                            "hinglish_script_mode": audio_settings.hinglish_script_mode,
                        },
                    )
                    stt_ms = int((time.monotonic() - stt_t0) * 1000)
                    if stt_res.text.strip():
                        effective_input = stt_res.text.strip()
                except Exception as exc:
                    errors.append(f"Turn {idx + 1} voice input STT/TTS error: {exc}")

            self._ws.publish_nonblocking(
                {
                    "type": "TESTING_EVENT",
                    "run_id": run_id,
                    "stage": "AGENT_THINKING",
                    "turn": idx + 1,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            llm_t0 = time.monotonic()
            llm_ttft_ms: int | None = None
            chunks: list[str] = []
            citations: list[dict[str, Any]] = []
            interrupted = bool(
                (interruption_enabled or persona.interrupt_probability >= 0.5) and idx == 1
            )

            try:
                async for ev in self._conversations.stream_message(
                    conv.id,
                    SendMessageRequest(content=effective_input, allow_draft_preview=True),
                ):
                    ev_type = ev.get("event")
                    if ev_type == "delta":
                        if llm_ttft_ms is None:
                            llm_ttft_ms = int((time.monotonic() - llm_t0) * 1000)
                        chunks.append(str(ev.get("content") or ""))
                        if interrupted and len("".join(chunks)) > 40:
                            break
                    elif ev_type == "done":
                        if isinstance(ev.get("citations"), list):
                            citations = ev["citations"]
                    elif ev_type == "error":
                        errors.append(f"Turn {idx + 1} LLM error: {ev.get('message')}")
            except Exception as exc:
                errors.append(f"Turn {idx + 1} conversation failure: {exc}")

            llm_total_ms = int((time.monotonic() - llm_t0) * 1000)
            agent_reply = "".join(chunks).strip()
            last_agent_reply = agent_reply

            if voice_enabled and agent_reply and self._tts and audio_settings:
                try:
                    tts_t0 = time.monotonic()
                    agent_wav = await self._tts.synthesize(
                        agent_reply,
                        {
                            "provider": audio_settings.tts_provider,
                            "voice_id": audio_settings.default_voice_id,
                            "speed": 1.0,
                            "pitch": 1.0,
                        },
                    )
                    tts_ms = int((time.monotonic() - tts_t0) * 1000)
                    agent_audio_ok = len(agent_wav) > 44
                except Exception as exc:
                    errors.append(f"Turn {idx + 1} agent TTS error: {exc}")

            e2e = (stt_ms or 0) + llm_total_ms + (tts_ms or 0)
            turn = SimulationTurn(
                turn_number=idx + 1,
                customer_text=effective_input,
                agent_text=agent_reply,
                customer_audio_generated=customer_audio_ok,
                agent_audio_generated=agent_audio_ok,
                stt_ms=stt_ms,
                llm_ttft_ms=llm_ttft_ms,
                llm_total_ms=llm_total_ms,
                tts_ms=tts_ms,
                end_to_end_ms=e2e,
                interrupted=interrupted,
                citations=citations,
            )
            turns.append(turn)

            self._ws.publish_nonblocking(
                {
                    "type": "TESTING_EVENT",
                    "run_id": run_id,
                    "stage": "AGENT_SPEAKING",
                    "turn": idx + 1,
                    "text": agent_reply,
                    "latency_ms": e2e,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        return turns, errors, conv.model_id
