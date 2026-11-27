"""TestOrchestrator, TestReportService, and Autonomous TestingAssistantService."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import logging
from typing import Any
import uuid

from app.providers.llm import LLMProvider
from app.repositories.testing_repository import TestingRepository
from app.schemas.telephony import ProviderConnectionStatus
from app.schemas.testing import (
    AssistantRequest,
    ManualReviewRequest,
    TestCategory,
    TestExecutionMode,
    TestingOverviewStats,
    TestRun,
    TestRunCreate,
    TestRunStatus,
)
from app.services.agent_service import AgentService
from app.services.speech_service import STTService, TTSService
from app.services.telephony_service import TelephonyManagementService
from app.services.testing_simulator import (
    ClientSimulatorService,
    ConversationEvaluator,
    TestingNotFoundError,
    TestScenarioService,
)
from app.services.ws_manager import WebSocketManager, monitoring_ws_hub

logger = logging.getLogger(__name__)


class TestReportService:
    """Exports test run reports in JSON, CSV, and Markdown, and compares two runs."""

    @staticmethod
    def to_markdown(run: TestRun) -> str:
        ev = run.evaluation
        lines = [
            f"# agentVoice Test Report — {run.id}",
            "",
            f"- **Agent**: {run.agent_name} (`{run.agent_id}`)",
            f"- **Scenario**: {run.scenario_name or run.persona_id}",
            f"- **Category**: {run.category.value}",
            f"- **Execution Mode**: `{run.execution_mode.value}`",
            f"- **Status**: `{run.status.value}`",
            f"- **Started**: {run.started_at.isoformat()}",
            f"- **Ended**: {run.ended_at.isoformat() if run.ended_at else '—'}",
            "",
        ]
        if ev:
            lines.extend(
                [
                    f"## Evaluation Score: {ev.overall_score}/100 (Passed: {ev.passed})",
                    "",
                    ev.explanation,
                    "",
                ]
            )
            if ev.critical_failures:
                lines.append("### Critical Failures")
                for cf in ev.critical_failures:
                    lines.append(f"- {cf}")
                lines.append("")
        lines.append("## Transcript")
        for t in run.turns:
            lines.append(f"### Turn {t.turn_number}")
            lines.append(f"- **Customer**: {t.customer_text}")
            lines.append(f"- **Agent**: {t.agent_text}")
            lines.append(f"- **Latency**: {t.end_to_end_ms} ms")
        return "\n".join(lines)

    @staticmethod
    def to_csv(run: TestRun) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "run_id",
                "turn_number",
                "customer_text",
                "agent_text",
                "stt_ms",
                "llm_total_ms",
                "tts_ms",
                "end_to_end_ms",
                "interrupted",
            ]
        )
        for t in run.turns:
            writer.writerow(
                [
                    run.id,
                    t.turn_number,
                    t.customer_text,
                    t.agent_text,
                    t.stt_ms if t.stt_ms is not None else "",
                    t.llm_total_ms if t.llm_total_ms is not None else "",
                    t.tts_ms if t.tts_ms is not None else "",
                    t.end_to_end_ms if t.end_to_end_ms is not None else "",
                    t.interrupted,
                ]
            )
        return buf.getvalue()

    @staticmethod
    def compare_runs(run_a: TestRun, run_b: TestRun) -> dict[str, Any]:
        score_a = run_a.evaluation.overall_score if run_a.evaluation else 0
        score_b = run_b.evaluation.overall_score if run_b.evaluation else 0
        return {
            "run_a_id": run_a.id,
            "run_b_id": run_b.id,
            "score_a": score_a,
            "score_b": score_b,
            "score_delta": score_b - score_a,
            "status_a": run_a.status.value,
            "status_b": run_b.status.value,
            "avg_llm_ms_a": run_a.avg_llm_ms,
            "avg_llm_ms_b": run_b.avg_llm_ms,
        }


class TestOrchestrator:
    """Coordinates end-to-end test runs, evaluation, persistence, and dashboard stats."""

    _stop_flags: dict[str, bool] = {}

    def __init__(
        self,
        repo: TestingRepository,
        agent_svc: AgentService,
        scenario_svc: TestScenarioService,
        sim_svc: ClientSimulatorService,
        telephony_mgmt: TelephonyManagementService | None = None,
        ws_hub: WebSocketManager = monitoring_ws_hub,
    ) -> None:
        self._repo = repo
        self._agents = agent_svc
        self._scenarios = scenario_svc
        self._sim = sim_svc
        self._telephony = telephony_mgmt
        self._ws = ws_hub

    def list_runs(self) -> list[TestRun]:
        return self._repo.list_runs()

    def get_run(self, run_id: str) -> TestRun:
        run = self._repo.get_run(run_id)
        if run is None:
            raise TestingNotFoundError(f"Test run '{run_id}' not found.")
        return run

    def delete_run(self, run_id: str) -> bool:
        return self._repo.delete_run(run_id)

    def stop_run(self, run_id: str) -> TestRun:
        run = self.get_run(run_id)
        self._stop_flags[run_id] = True
        updated = run.model_copy(
            update={"status": TestRunStatus.STOPPED, "ended_at": datetime.now(timezone.utc)}
        )
        return self._repo.save_run(updated)

    def review_run(self, run_id: str, req: ManualReviewRequest) -> TestRun:
        run = self.get_run(run_id)
        if run.evaluation is None:
            raise TestingNotFoundError(f"Test run '{run_id}' has no evaluation to review.")
        updated_eval = ConversationEvaluator.apply_manual_review(run.evaluation, req)
        updated = run.model_copy(
            update={
                "evaluation": updated_eval,
                "status": TestRunStatus.PASSED if updated_eval.passed else TestRunStatus.FAILED,
            }
        )
        return self._repo.save_run(updated)

    async def execute_run(self, payload: TestRunCreate) -> TestRun:
        agent = await self._agents.get_agent(payload.agent_id)
        scenario = (
            self._scenarios.get_scenario(payload.scenario_id) if payload.scenario_id else None
        )
        persona_id = scenario.persona_id if scenario else payload.persona_id
        run_id = f"trun_{uuid.uuid4().hex[:10]}"
        self._stop_flags[run_id] = False

        run = TestRun(
            id=run_id,
            agent_id=agent.id,
            agent_name=agent.name,
            scenario_id=scenario.id if scenario else None,
            scenario_name=scenario.name if scenario else f"Persona: {persona_id}",
            persona_id=persona_id,
            category=payload.category,
            execution_mode=payload.execution_mode,
            status=TestRunStatus.RUNNING,
            model_id=agent.model.model_id,
            stt_provider="faster-whisper",
            tts_provider=agent.voice.provider,
        )
        self._repo.save_run(run)
        self._ws.publish_nonblocking({"type": "TEST_RUN_STARTED", "run_id": run_id})

        turns, errors = await self._sim.run_simulation(
            run_id=run_id,
            agent_id=agent.id,
            persona_id=persona_id,
            scenario=scenario,
            voice_enabled=payload.voice_enabled,
            max_turns=scenario.max_turns if scenario else payload.max_turns,
            interruption_enabled=scenario.interruption_enabled if scenario else False,
            stop_flags=self._stop_flags,
        )

        evaluation = ConversationEvaluator.evaluate(
            turns=turns,
            persona_id=persona_id,
            require_ai_disclosure=True,
            kb_expected=bool(agent.knowledge_base.knowledge_base_id) and payload.include_kb_checks,
        )

        stt_vals = [t.stt_ms for t in turns if t.stt_ms is not None]
        llm_vals = [t.llm_total_ms for t in turns if t.llm_total_ms is not None]
        tts_vals = [t.tts_ms for t in turns if t.tts_ms is not None]

        if self._stop_flags.pop(run_id, False):
            final_status = TestRunStatus.STOPPED
        elif evaluation.requires_review:
            final_status = TestRunStatus.REQUIRES_REVIEW
        elif evaluation.passed:
            final_status = TestRunStatus.PASSED
        else:
            final_status = TestRunStatus.FAILED

        recommendations: list[str] = []
        if evaluation.critical_failures:
            recommendations.append("Resolve critical compliance failures before production deployment.")
        if not agent.knowledge_base.knowledge_base_id:
            recommendations.append("Assign a Knowledge Base to ground product/pricing answers.")
        if errors:
            recommendations.append("Inspect voice/LLM error logs for fallback or timeout events.")

        completed = run.model_copy(
            update={
                "status": final_status,
                "turns": turns,
                "evaluation": evaluation,
                "avg_stt_ms": round(sum(stt_vals) / len(stt_vals), 1) if stt_vals else None,
                "avg_llm_ms": round(sum(llm_vals) / len(llm_vals), 1) if llm_vals else None,
                "avg_tts_ms": round(sum(tts_vals) / len(tts_vals), 1) if tts_vals else None,
                "error_logs": errors,
                "recommendations": recommendations,
                "ended_at": datetime.now(timezone.utc),
            }
        )
        saved = self._repo.save_run(completed)
        self._repo.append_event(
            {"run_id": run_id, "status": final_status.value, "score": evaluation.overall_score}
        )
        self._ws.publish_nonblocking(
            {"type": "TEST_RUN_COMPLETED", "run_id": run_id, "status": final_status.value}
        )
        return saved

    async def rerun_failed(self, run_id: str) -> TestRun:
        old = self.get_run(run_id)
        return await self.execute_run(
            TestRunCreate(
                agent_id=old.agent_id,
                scenario_id=old.scenario_id,
                persona_id=old.persona_id,
                category=old.category,
                execution_mode=old.execution_mode,
                voice_enabled=any(t.agent_audio_generated for t in old.turns),
                max_turns=max(1, len(old.turns) or 4),
            )
        )

    def get_stats(self) -> TestingOverviewStats:
        runs = self._repo.list_runs()
        total = len(runs)
        passed = sum(1 for r in runs if r.status == TestRunStatus.PASSED)
        failed = sum(1 for r in runs if r.status == TestRunStatus.FAILED)
        review = sum(1 for r in runs if r.status == TestRunStatus.REQUIRES_REVIEW)

        llm_avgs = [r.avg_llm_ms for r in runs if r.avg_llm_ms is not None]
        stt_avgs = [r.avg_stt_ms for r in runs if r.avg_stt_ms is not None]
        tts_avgs = [r.avg_tts_ms for r in runs if r.avg_tts_ms is not None]
        scores = [r.evaluation.overall_score for r in runs if r.evaluation is not None]
        voice_errs = sum(len(r.error_logs) for r in runs)

        by_category: dict[str, dict[str, int]] = {}
        for cat in TestCategory:
            cat_runs = [r for r in runs if r.category == cat]
            by_category[cat.value] = {
                "total": len(cat_runs),
                "passed": sum(1 for r in cat_runs if r.status == TestRunStatus.PASSED),
                "failed": sum(1 for r in cat_runs if r.status == TestRunStatus.FAILED),
            }

        by_mode = {
            mode.value: sum(1 for r in runs if r.execution_mode == mode)
            for mode in TestExecutionMode
        }

        tel_status = "Not connected"
        if self._telephony is not None:
            provs = self._telephony.list_providers()
            if any(p.status == ProviderConnectionStatus.CONNECTED for p in provs):
                tel_status = "Connected"

        return TestingOverviewStats(
            total_runs=total,
            passed_runs=passed,
            failed_runs=failed,
            requires_review_runs=review,
            avg_ai_response_ms=round(sum(llm_avgs) / len(llm_avgs), 1) if llm_avgs else None,
            avg_stt_ms=round(sum(stt_avgs) / len(stt_avgs), 1) if stt_avgs else None,
            avg_tts_ms=round(sum(tts_avgs) / len(tts_avgs), 1) if tts_avgs else None,
            completion_rate_percent=round((passed / total) * 100, 1) if total else 0.0,
            avg_quality_score=round(sum(scores) / len(scores), 1) if scores else None,
            voice_pipeline_errors=voice_errs,
            telephony_status=tel_status,
            by_category=by_category,
            by_execution_mode=by_mode,
        )


class TestingAssistantService:
    """Autonomous Testing Assistant: inspects readiness, plans tests, and executes authorized runs."""

    def __init__(
        self,
        agent_svc: AgentService,
        llm_provider: LLMProvider,
        stt_svc: STTService,
        tts_svc: TTSService,
        telephony_mgmt: TelephonyManagementService,
        orchestrator: TestOrchestrator,
    ) -> None:
        self._agents = agent_svc
        self._llm = llm_provider
        self._stt = stt_svc
        self._tts = tts_svc
        self._telephony = telephony_mgmt
        self._orchestrator = orchestrator

    async def analyze_and_run(self, req: AssistantRequest) -> dict[str, Any]:
        agent = await self._agents.get_agent(req.agent_id)
        llm_health = await self._llm.health_check()
        stt_health = await self._stt.health_check()
        tts_health = await self._tts.health_check()
        provs = self._telephony.list_providers()
        tel_connected = any(p.status == ProviderConnectionStatus.CONNECTED for p in provs)
        kb_assigned = bool(agent.knowledge_base.knowledge_base_id)

        warnings: list[str] = []
        missing_dependencies: list[str] = []

        if not llm_health.available:
            missing_dependencies.append("Local LLM service (Ollama) is unavailable.")
            warnings.append("Local LLM service is unavailable. Start Ollama before running voice/AI tests.")
        if not kb_assigned:
            warnings.append(
                "No knowledge base is configured for this agent. General conversation can be tested, "
                "but product accuracy cannot be fully evaluated."
            )
        if not tel_connected:
            warnings.append("Telephony is not connected; telephony tests will be skipped (microphone & local simulation remain available).")
        if req.voice_enabled and (not stt_health.available or not tts_health.available):
            warnings.append("STT or TTS provider is unavailable; falling back to text simulation if needed.")

        # Derive persona plan from natural-language instruction
        lower = req.instruction.lower()
        planned_personas: list[str] = []
        if "pricing" in lower or "sales" in lower or "discount" in lower:
            planned_personas.extend(["interested", "price_sensitive"])
        if "objection" in lower or "skeptic" in lower:
            planned_personas.append("skeptical")
        if "hindi" in lower:
            planned_personas.append("hindi")
        if "hinglish" in lower:
            planned_personas.append("hinglish")
        if "interrupt" in lower or "barge" in lower:
            planned_personas.append("interrupting")
        if "opt" in lower or "refus" in lower:
            planned_personas.append("uninterested")
        if not planned_personas:
            planned_personas = ["interested", "price_sensitive", "uninterested"]

        executed_runs: list[dict[str, Any]] = []
        if req.execute and llm_health.available:
            for pid in planned_personas:
                run = await self._orchestrator.execute_run(
                    TestRunCreate(
                        agent_id=agent.id,
                        persona_id=pid,
                        category=TestCategory.E2E if req.voice_enabled else TestCategory.AI_CONVERSATION,
                        execution_mode=TestExecutionMode.LOCAL_SIMULATION,
                        voice_enabled=req.voice_enabled and stt_health.available and tts_health.available,
                        max_turns=3,
                    )
                )
                executed_runs.append(
                    {
                        "run_id": run.id,
                        "persona_id": pid,
                        "status": run.status.value,
                        "score": run.evaluation.overall_score if run.evaluation else None,
                        "critical_failures": run.evaluation.critical_failures if run.evaluation else [],
                    }
                )

        return {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "readiness": {
                "llm_available": llm_health.available,
                "stt_available": stt_health.available,
                "tts_available": tts_health.available,
                "kb_assigned": kb_assigned,
                "telephony_connected": tel_connected,
            },
            "missing_dependencies": missing_dependencies,
            "warnings": warnings,
            "planned_personas": planned_personas,
            "executed_runs": executed_runs,
        }
