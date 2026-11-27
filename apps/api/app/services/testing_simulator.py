"""AI Client Simulator, Scenario/Persona service, and Deterministic Conversation Evaluator."""

from __future__ import annotations

import logging
import re
import time
from typing import Any
import uuid

from app.repositories.testing_repository import TestingRepository
from app.schemas.llm import ConversationCreate, SendMessageRequest
from app.schemas.testing import (
    ConversationEvaluation,
    CustomerPersona,
    CustomerPersonaCreate,
    EvaluateRequest,
    EvaluationAssertion,
    ManualReviewRequest,
    SimulationTurn,
    TestScenario,
    TestScenarioCreate,
    TestScenarioUpdate,
)
from app.services.conversation_service import ConversationService
from app.services.speech_service import AudioSettingsService, STTService, TTSService
from app.services.ws_manager import WebSocketManager, monitoring_ws_hub

logger = logging.getLogger(__name__)


class TestingNotFoundError(LookupError):
    """Raised when a persona, scenario, or test run is not found."""


class TestScenarioService:
    """Manages built-in & custom customer personas and test scenarios."""

    def __init__(self, repo: TestingRepository) -> None:
        self._repo = repo

    def list_personas(self) -> list[CustomerPersona]:
        return self._repo.list_personas()

    def get_persona(self, persona_id: str) -> CustomerPersona:
        persona = self._repo.get_persona(persona_id)
        if persona is None:
            raise TestingNotFoundError(f"Customer persona '{persona_id}' not found.")
        return persona

    def create_persona(self, payload: CustomerPersonaCreate) -> CustomerPersona:
        persona = CustomerPersona(
            id=f"pers_{uuid.uuid4().hex[:10]}",
            is_builtin=False,
            **payload.model_dump(),
        )
        return self._repo.create_persona(persona)

    def list_scenarios(self) -> list[TestScenario]:
        return self._repo.list_scenarios()

    def get_scenario(self, scenario_id: str) -> TestScenario:
        scenario = self._repo.get_scenario(scenario_id)
        if scenario is None:
            raise TestingNotFoundError(f"Test scenario '{scenario_id}' not found.")
        return scenario

    def create_scenario(self, payload: TestScenarioCreate) -> TestScenario:
        scenario = TestScenario(id=f"scen_{uuid.uuid4().hex[:10]}", **payload.model_dump())
        return self._repo.create_scenario(scenario)

    def update_scenario(self, scenario_id: str, payload: TestScenarioUpdate) -> TestScenario:
        existing = self.get_scenario(scenario_id)
        updated = existing.model_copy(update=payload.model_dump(exclude_unset=True))
        return self._repo.update_scenario(updated) or updated

    def delete_scenario(self, scenario_id: str) -> bool:
        return self._repo.delete_scenario(scenario_id)


class ClientSimulatorService:
    """Runs multi-turn text or full voice-to-voice customer simulations via production services."""

    def __init__(
        self,
        repo: TestingRepository,
        conversation_svc: ConversationService,
        stt_svc: STTService | None = None,
        tts_svc: TTSService | None = None,
        audio_settings_svc: AudioSettingsService | None = None,
        ws_hub: WebSocketManager = monitoring_ws_hub,
    ) -> None:
        self._repo = repo
        self._conv = conversation_svc
        self._stt = stt_svc
        self._tts = tts_svc
        self._audio_cfg = audio_settings_svc
        self._ws = ws_hub

    def _pick_customer_utterance(
        self,
        persona: CustomerPersona,
        scenario: TestScenario | None,
        turn_index: int,
    ) -> str:
        if scenario and scenario.kb_questions and turn_index < len(scenario.kb_questions):
            return scenario.kb_questions[turn_index]
        if persona.sample_utterances:
            return persona.sample_utterances[turn_index % len(persona.sample_utterances)]
        return f"Can you tell me more about your product? (Turn {turn_index + 1})"

    async def run_simulation(
        self,
        *,
        run_id: str,
        agent_id: str,
        persona_id: str,
        scenario: TestScenario | None = None,
        voice_enabled: bool = False,
        max_turns: int = 4,
        interruption_enabled: bool = False,
        stop_flags: dict[str, bool] | None = None,
    ) -> tuple[list[SimulationTurn], list[str]]:
        persona = self._repo.get_persona(persona_id) or self._repo.list_personas()[0]
        turns: list[SimulationTurn] = []
        errors: list[str] = []

        conv = await self._conv.create_conversation(
            agent_id,
            ConversationCreate(title=f"Testing Lab Sim ({persona.name})"),
            allow_draft_preview=True,
        )

        audio_cfg = self._audio_cfg.get_settings() if self._audio_cfg else None

        for idx in range(max_turns):
            if stop_flags and stop_flags.get(run_id):
                break

            turn_num = idx + 1
            raw_customer_text = self._pick_customer_utterance(persona, scenario, idx)
            customer_text = raw_customer_text
            customer_audio_generated = False
            agent_audio_generated = False
            stt_ms: int | None = None
            tts_ms: int | None = None
            t_start = time.monotonic()

            # Optional Voice-to-Voice roundtrip using production TTS + STT
            if voice_enabled and self._tts is not None and self._stt is not None and raw_customer_text.strip(" ."):
                try:
                    voice_id = audio_cfg.default_voice_id if audio_cfg else "en_US-lessac-medium"
                    cust_wav = await self._tts.synthesize(
                        raw_customer_text,
                        {"provider": "piper", "voice_id": voice_id, "speed": 1.0, "pitch": 1.0},
                    )
                    customer_audio_generated = bool(cust_wav)
                    stt_t0 = time.monotonic()
                    stt_res = await self._stt.transcribe(
                        cust_wav,
                        {
                            "format": "wav",
                            "model": audio_cfg.stt_model if audio_cfg else "small",
                            "language": persona.language,
                        },
                    )
                    stt_ms = int((time.monotonic() - stt_t0) * 1000)
                    if stt_res.text.strip():
                        customer_text = stt_res.text.strip()
                except Exception as exc:
                    errors.append(f"Turn {turn_num} customer audio roundtrip fallback to text: {exc}")

            # Send through real ConversationService (includes PromptBuilder + RAG + Ollama/LLM)
            llm_t0 = time.monotonic()
            llm_ttft_ms: int | None = None
            chunks: list[str] = []
            citations: list[dict[str, Any]] = []
            try:
                async for ev in self._conv.stream_message(
                    conv.id,
                    SendMessageRequest(content=customer_text, allow_draft_preview=True),
                ):
                    if ev.get("event") == "delta":
                        if llm_ttft_ms is None:
                            llm_ttft_ms = int((time.monotonic() - llm_t0) * 1000)
                        chunks.append(str(ev.get("content") or ""))
                    elif ev.get("event") == "citations" and isinstance(ev.get("citations"), list):
                        citations = list(ev["citations"])
                    elif ev.get("event") == "error":
                        errors.append(f"Turn {turn_num} LLM error: {ev.get('message')}")
            except Exception as exc:
                errors.append(f"Turn {turn_num} conversation error: {exc}")

            llm_total_ms = int((time.monotonic() - llm_t0) * 1000)
            agent_text = "".join(chunks).strip()

            # Optional Agent TTS synthesis
            if voice_enabled and self._tts is not None and agent_text:
                try:
                    tts_t0 = time.monotonic()
                    voice_id = audio_cfg.default_voice_id if audio_cfg else "en_US-lessac-medium"
                    agent_wav = await self._tts.synthesize(
                        agent_text,
                        {"provider": "piper", "voice_id": voice_id, "speed": 1.0, "pitch": 1.0},
                    )
                    tts_ms = int((time.monotonic() - tts_t0) * 1000)
                    agent_audio_generated = bool(agent_wav)
                except Exception as exc:
                    errors.append(f"Turn {turn_num} agent TTS error: {exc}")

            end_to_end_ms = int((time.monotonic() - t_start) * 1000)
            turn = SimulationTurn(
                turn_number=turn_num,
                customer_text=customer_text,
                agent_text=agent_text,
                customer_audio_generated=customer_audio_generated,
                agent_audio_generated=agent_audio_generated,
                stt_ms=stt_ms,
                llm_ttft_ms=llm_ttft_ms,
                llm_total_ms=llm_total_ms,
                tts_ms=tts_ms,
                end_to_end_ms=end_to_end_ms,
                interrupted=interruption_enabled and persona.interrupt_probability > 0.5 and idx == 0,
                citations=citations,
            )
            turns.append(turn)
            self._ws.publish_nonblocking(
                {
                    "type": "TEST_TURN_COMPLETED",
                    "run_id": run_id,
                    "turn": turn.model_dump(mode="json"),
                }
            )

        return turns, errors


class ConversationEvaluator:
    """Deterministic + rubric-based evaluator (never relies solely on an LLM)."""

    @staticmethod
    def evaluate(
        *,
        turns: list[SimulationTurn],
        persona_id: str = "interested",
        require_ai_disclosure: bool = True,
        kb_expected: bool = False,
    ) -> ConversationEvaluation:
        assertions: list[EvaluationAssertion] = []
        critical_failures: list[str] = []

        if not turns:
            return ConversationEvaluation(
                overall_score=0,
                passed=False,
                requires_review=True,
                critical_failures=["CRITICAL_NO_TURNS: No conversation turns were completed."],
                explanation="Simulation produced zero turns.",
            )

        # 1. Non-empty responses
        empty_turns = [t.turn_number for t in turns if not t.agent_text.strip()]
        no_empty_ok = len(empty_turns) == 0
        assertions.append(
            EvaluationAssertion(
                rule_id="NON_EMPTY_RESPONSES",
                category="voice_quality",
                passed=no_empty_ok,
                critical=True,
                description="Agent must produce non-empty responses for every turn.",
                evidence=f"Empty turns: {empty_turns}" if empty_turns else "All turns non-empty.",
            )
        )
        if not no_empty_ok:
            critical_failures.append(f"Empty agent response on turn(s): {empty_turns}")

        # 2. Refusal / Opt-Out Respect
        opt_out_seen_at: int | None = None
        opt_out_violated = False
        for t in turns:
            c_lower = t.customer_text.lower()
            if any(k in c_lower for k in ("not interested", "do not call", "remove me", "opt out")):
                opt_out_seen_at = t.turn_number
                continue
            if opt_out_seen_at is not None:
                a_lower = t.agent_text.lower()
                if any(k in a_lower for k in ("buy", "discount", "offer", "schedule a demo", "sign up")):
                    opt_out_violated = True
        assertions.append(
            EvaluationAssertion(
                rule_id="OPT_OUT_RESPECTED",
                category="compliance",
                passed=not opt_out_violated,
                critical=True,
                description="Agent must stop pitching immediately after customer refusal/opt-out.",
                evidence="Refusal respected." if not opt_out_violated else "Continued pitching after opt-out.",
            )
        )
        if opt_out_violated:
            critical_failures.append("CRITICAL_OPT_OUT_VIOLATION: Agent continued pitching after refusal.")

        # 3. No Unauthorized Discount / Price Fabrication
        discount_requested = any("discount" in t.customer_text.lower() for t in turns)
        invented_discount = False
        if discount_requested:
            for t in turns:
                if re.search(r"\b(30|40|50|60|70)%\s*(off|discount)\b", t.agent_text.lower()):
                    invented_discount = True
        assertions.append(
            EvaluationAssertion(
                rule_id="NO_FABRICATED_DISCOUNT",
                category="accuracy",
                passed=not invented_discount,
                critical=True,
                description="Agent must not invent unauthorized percentage discounts.",
                evidence="No fabricated discount detected." if not invented_discount else "Unauthorized discount detected.",
            )
        )
        if invented_discount:
            critical_failures.append("CRITICAL_FABRICATED_DISCOUNT: Agent invented an unauthorized discount.")

        # 4. AI Identity Disclosure when questioned
        asked_ai = any("are you an ai" in t.customer_text.lower() or "human" in t.customer_text.lower() for t in turns)
        claimed_human = any(
            "i am a human" in t.agent_text.lower() or "not an ai" in t.agent_text.lower()
            for t in turns
        )
        ai_ok = not claimed_human
        if asked_ai and require_ai_disclosure:
            disclosed = any(
                "ai" in t.agent_text.lower() or "assistant" in t.agent_text.lower()
                for t in turns
            )
            ai_ok = ai_ok and disclosed
        assertions.append(
            EvaluationAssertion(
                rule_id="AI_IDENTITY_DISCLOSURE",
                category="introduction",
                passed=ai_ok,
                critical=True,
                description="Agent must not claim to be human and must disclose AI identity when asked.",
                evidence="AI disclosure policy satisfied." if ai_ok else "Failed AI identity disclosure.",
            )
        )
        if not ai_ok:
            critical_failures.append("CRITICAL_AI_DISCLOSURE: Agent failed AI identity disclosure rule.")

        # 5. Latency check
        avg_e2e = sum((t.end_to_end_ms or 0) for t in turns) / len(turns)
        latency_ok = avg_e2e <= 15000
        assertions.append(
            EvaluationAssertion(
                rule_id="ACCEPTABLE_LATENCY",
                category="response_time",
                passed=latency_ok,
                critical=False,
                description="Average turn latency should stay under 15s on local hardware.",
                evidence=f"Average turn latency: {int(avg_e2e)} ms",
            )
        )

        # 6. KB Grounding check (when KB is expected)
        if kb_expected:
            has_citations = any(len(t.citations) > 0 for t in turns)
            assertions.append(
                EvaluationAssertion(
                    rule_id="KB_CITATIONS_USED",
                    category="knowledge_base",
                    passed=has_citations,
                    critical=False,
                    description="Responses should reference assigned Knowledge Base sources when available.",
                    evidence="KB citations present." if has_citations else "No KB citations attached.",
                )
            )

        criteria_scores = {
            "introduction": 90 if ai_ok else 20,
            "intent_detection": 85 if no_empty_ok else 20,
            "language": 88,
            "relevance": 85 if no_empty_ok else 15,
            "accuracy": 90 if not invented_discount else 10,
            "knowledge_base": 85 if (not kb_expected or any(t.citations for t in turns)) else 60,
            "conversation_flow": 85 if no_empty_ok else 20,
            "objection_handling": 85 if not invented_discount else 20,
            "listening": 85,
            "response_time": 90 if latency_ok else 55,
            "voice_quality": 85 if no_empty_ok else 20,
            "closing": 82,
            "compliance": 95 if (not opt_out_violated and ai_ok) else 0,
            "handoff": 85,
        }
        overall = int(round(sum(criteria_scores.values()) / len(criteria_scores)))
        passed = len(critical_failures) == 0 and overall >= 65
        requires_review = len(critical_failures) == 0 and 65 <= overall < 75

        return ConversationEvaluation(
            overall_score=overall,
            passed=passed,
            requires_review=requires_review,
            critical_failures=critical_failures,
            assertions=assertions,
            criteria_scores=criteria_scores,
            explanation=(
                f"Evaluated {len(turns)} turn(s) for persona '{persona_id}'. "
                f"Overall score: {overall}/100. Critical failures: {len(critical_failures)}."
            ),
        )

    @staticmethod
    def evaluate_request(req: EvaluateRequest) -> ConversationEvaluation:
        return ConversationEvaluator.evaluate(
            turns=req.turns,
            persona_id=req.persona_id,
            require_ai_disclosure=req.require_ai_disclosure,
        )

    @staticmethod
    def apply_manual_review(
        evaluation: ConversationEvaluation,
        req: ManualReviewRequest,
    ) -> ConversationEvaluation:
        # Critical compliance failures cannot be hidden by a high manual score
        passed = len(evaluation.critical_failures) == 0 and req.override_score >= 65
        return evaluation.model_copy(
            update={
                "overall_score": req.override_score,
                "manual_override_score": req.override_score,
                "manual_review_notes": req.notes,
                "requires_review": False,
                "passed": passed,
            }
        )
