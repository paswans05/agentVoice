"""End-to-End Testing Lab, AI Client Simulator, Evaluation, and Assistant API endpoints."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import PlainTextResponse

from app.api.v1.agents import get_agent_service
from app.api.v1.conversations import get_conversation_service
from app.api.v1.health import get_storage
from app.api.v1.knowledge import get_rag_service
from app.api.v1.llm import get_llm_provider
from app.api.v1.speech import get_audio_settings_service, get_stt_service, get_tts_service
from app.api.v1.telephony import get_telephony_mgmt, get_telephony_router_svc
from app.core.config import Settings, get_settings
from app.providers.llm import LLMProvider
from app.providers.storage import StorageProvider
from app.repositories.testing_repository import TestingRepository
from app.schemas.response import ApiResponse, ok
from app.schemas.testing import (
    AssistantRequest,
    ConversationEvaluation,
    CustomerPersona,
    CustomerPersonaCreate,
    EvaluateRequest,
    FailureRecoveryTestRequest,
    KnowledgeBaseTestRequest,
    ManualReviewRequest,
    PerformanceTestRequest,
    SimulateRequest,
    TelephonyTestRequest,
    TestCategory,
    TestExecutionMode,
    TestingOverviewStats,
    TestRun,
    TestRunCreate,
    TestScenario,
    TestScenarioCreate,
    TestScenarioUpdate,
)
from app.services.agent_service import AgentService
from app.services.conversation_service import ConversationService
from app.services.live_calls_service import CallAuthorizationError, CallAuthorizationService
from app.services.rag_service import RAGService
from app.services.speech_service import AudioSettingsService, STTService, TTSService
from app.services.telephony_service import TelephonyCallRouter, TelephonyManagementService
from app.services.testing_orchestrator import (
    TestingAssistantService,
    TestOrchestrator,
    TestReportService,
)
from app.services.testing_simulator import (
    ClientSimulatorService,
    ConversationEvaluator,
    TestScenarioService,
)
from app.services.testing_suites import (
    FailureRecoveryTestService,
    KnowledgeBaseTestService,
    PerformanceTestService,
    TelephonyTestService,
)
from app.services.ws_manager import monitoring_ws_hub

router = APIRouter(prefix="/testing", tags=["testing"])


def get_testing_repo(storage: StorageProvider = Depends(get_storage)) -> TestingRepository:
    return TestingRepository(storage)


def get_scenario_service(
    repo: TestingRepository = Depends(get_testing_repo),
) -> TestScenarioService:
    return TestScenarioService(repo)


def get_simulator_service(
    repo: TestingRepository = Depends(get_testing_repo),
    conv_svc: ConversationService = Depends(get_conversation_service),
    stt_svc: STTService = Depends(get_stt_service),
    tts_svc: TTSService = Depends(get_tts_service),
    audio_cfg: AudioSettingsService = Depends(get_audio_settings_service),
) -> ClientSimulatorService:
    return ClientSimulatorService(
        repo=repo,
        conversation_svc=conv_svc,
        stt_svc=stt_svc,
        tts_svc=tts_svc,
        audio_settings_svc=audio_cfg,
        ws_hub=monitoring_ws_hub,
    )


def get_orchestrator(
    repo: TestingRepository = Depends(get_testing_repo),
    agent_svc: AgentService = Depends(get_agent_service),
    scenario_svc: TestScenarioService = Depends(get_scenario_service),
    sim_svc: ClientSimulatorService = Depends(get_simulator_service),
    telephony_mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
) -> TestOrchestrator:
    return TestOrchestrator(
        repo=repo,
        agent_svc=agent_svc,
        scenario_svc=scenario_svc,
        sim_svc=sim_svc,
        telephony_mgmt=telephony_mgmt,
        ws_hub=monitoring_ws_hub,
    )


def _require_auth(settings: Settings, authorization: str | None) -> None:
    if not CallAuthorizationService.authorize(settings, authorization):
        raise CallAuthorizationError("Operator authorization is required.")


@router.get("/status", response_model=ApiResponse[TestingOverviewStats])
async def testing_status(
    settings: Settings = Depends(get_settings),
    orch: TestOrchestrator = Depends(get_orchestrator),
) -> ApiResponse[TestingOverviewStats]:
    return ok(orch.get_stats(), version=settings.app_version)


# --- Personas & Scenarios ---

@router.get("/personas", response_model=ApiResponse[list[CustomerPersona]])
async def list_personas(
    settings: Settings = Depends(get_settings),
    svc: TestScenarioService = Depends(get_scenario_service),
) -> ApiResponse[list[CustomerPersona]]:
    return ok(svc.list_personas(), version=settings.app_version)


@router.post("/personas", response_model=ApiResponse[CustomerPersona], status_code=status.HTTP_201_CREATED)
async def create_persona(
    payload: CustomerPersonaCreate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    svc: TestScenarioService = Depends(get_scenario_service),
) -> ApiResponse[CustomerPersona]:
    _require_auth(settings, authorization)
    return ok(svc.create_persona(payload), version=settings.app_version)


@router.get("/scenarios", response_model=ApiResponse[list[TestScenario]])
async def list_scenarios(
    settings: Settings = Depends(get_settings),
    svc: TestScenarioService = Depends(get_scenario_service),
) -> ApiResponse[list[TestScenario]]:
    return ok(svc.list_scenarios(), version=settings.app_version)


@router.post("/scenarios", response_model=ApiResponse[TestScenario], status_code=status.HTTP_201_CREATED)
async def create_scenario(
    payload: TestScenarioCreate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    svc: TestScenarioService = Depends(get_scenario_service),
) -> ApiResponse[TestScenario]:
    _require_auth(settings, authorization)
    return ok(svc.create_scenario(payload), version=settings.app_version)


@router.put("/scenarios/{scenario_id}", response_model=ApiResponse[TestScenario])
async def update_scenario(
    scenario_id: str,
    payload: TestScenarioUpdate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    svc: TestScenarioService = Depends(get_scenario_service),
) -> ApiResponse[TestScenario]:
    _require_auth(settings, authorization)
    return ok(svc.update_scenario(scenario_id, payload), version=settings.app_version)


@router.delete("/scenarios/{scenario_id}", response_model=ApiResponse[dict[str, Any]])
async def delete_scenario(
    scenario_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    svc: TestScenarioService = Depends(get_scenario_service),
) -> ApiResponse[dict[str, Any]]:
    _require_auth(settings, authorization)
    return ok({"deleted": svc.delete_scenario(scenario_id), "id": scenario_id}, version=settings.app_version)


# --- Runs, Simulation, Evaluation, Reports ---

@router.post("/runs", response_model=ApiResponse[TestRun], status_code=status.HTTP_201_CREATED)
async def create_test_run(
    payload: TestRunCreate,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    orch: TestOrchestrator = Depends(get_orchestrator),
) -> ApiResponse[TestRun]:
    _require_auth(settings, authorization)
    return ok(await orch.execute_run(payload), version=settings.app_version)


@router.get("/runs", response_model=ApiResponse[list[TestRun]])
async def list_test_runs(
    settings: Settings = Depends(get_settings),
    orch: TestOrchestrator = Depends(get_orchestrator),
) -> ApiResponse[list[TestRun]]:
    return ok(orch.list_runs(), version=settings.app_version)


@router.get("/runs/{run_id}", response_model=ApiResponse[TestRun])
async def get_test_run(
    run_id: str,
    settings: Settings = Depends(get_settings),
    orch: TestOrchestrator = Depends(get_orchestrator),
) -> ApiResponse[TestRun]:
    return ok(orch.get_run(run_id), version=settings.app_version)


@router.delete("/runs/{run_id}", response_model=ApiResponse[dict[str, Any]])
async def delete_test_run(
    run_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    orch: TestOrchestrator = Depends(get_orchestrator),
) -> ApiResponse[dict[str, Any]]:
    _require_auth(settings, authorization)
    return ok({"deleted": orch.delete_run(run_id), "id": run_id}, version=settings.app_version)


@router.post("/runs/{run_id}/stop", response_model=ApiResponse[TestRun])
async def stop_test_run(
    run_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    orch: TestOrchestrator = Depends(get_orchestrator),
) -> ApiResponse[TestRun]:
    _require_auth(settings, authorization)
    return ok(orch.stop_run(run_id), version=settings.app_version)


@router.post("/runs/{run_id}/rerun-failed", response_model=ApiResponse[TestRun])
async def rerun_failed_test(
    run_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    orch: TestOrchestrator = Depends(get_orchestrator),
) -> ApiResponse[TestRun]:
    _require_auth(settings, authorization)
    return ok(await orch.rerun_failed(run_id), version=settings.app_version)


@router.post("/runs/{run_id}/review", response_model=ApiResponse[TestRun])
async def review_test_run(
    run_id: str,
    payload: ManualReviewRequest,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    orch: TestOrchestrator = Depends(get_orchestrator),
) -> ApiResponse[TestRun]:
    _require_auth(settings, authorization)
    return ok(orch.review_run(run_id, payload), version=settings.app_version)


@router.post("/simulate", response_model=ApiResponse[TestRun])
async def run_simulation(
    payload: SimulateRequest,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    orch: TestOrchestrator = Depends(get_orchestrator),
) -> ApiResponse[TestRun]:
    _require_auth(settings, authorization)
    run = await orch.execute_run(
        TestRunCreate(
            agent_id=payload.agent_id,
            scenario_id=payload.scenario_id,
            persona_id=payload.persona_id,
            category=TestCategory.VOICE if payload.voice_enabled else TestCategory.AI_CONVERSATION,
            execution_mode=TestExecutionMode.LOCAL_SIMULATION,
            voice_enabled=payload.voice_enabled,
            max_turns=payload.max_turns,
        )
    )
    return ok(run, version=settings.app_version)


@router.post("/evaluate", response_model=ApiResponse[ConversationEvaluation])
async def evaluate_conversation(
    payload: EvaluateRequest,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[ConversationEvaluation]:
    return ok(ConversationEvaluator.evaluate_request(payload), version=settings.app_version)


@router.get("/reports/compare", response_model=ApiResponse[dict[str, Any]])
async def compare_reports(
    run_a: str = Query(...),
    run_b: str = Query(...),
    settings: Settings = Depends(get_settings),
    orch: TestOrchestrator = Depends(get_orchestrator),
) -> ApiResponse[dict[str, Any]]:
    a = orch.get_run(run_a)
    b = orch.get_run(run_b)
    return ok(TestReportService.compare_runs(a, b), version=settings.app_version)


@router.get("/reports/{run_id}")
async def get_test_report(
    run_id: str,
    format: str = Query(default="json", pattern="^(json|csv|markdown)$"),
    settings: Settings = Depends(get_settings),
    orch: TestOrchestrator = Depends(get_orchestrator),
):
    run = orch.get_run(run_id)
    if format == "markdown":
        return PlainTextResponse(TestReportService.to_markdown(run), media_type="text/markdown")
    if format == "csv":
        return PlainTextResponse(TestReportService.to_csv(run), media_type="text/csv")
    return ok(run, version=settings.app_version)


# --- Specialized Suites & Autonomous Testing Assistant ---

@router.post("/kb-tests", response_model=ApiResponse[dict[str, Any]])
async def run_kb_tests(
    payload: KnowledgeBaseTestRequest,
    settings: Settings = Depends(get_settings),
    agent_svc: AgentService = Depends(get_agent_service),
    rag_svc: RAGService = Depends(get_rag_service),
) -> ApiResponse[dict[str, Any]]:
    svc = KnowledgeBaseTestService(agent_svc, rag_svc._retrieval)
    return ok(await svc.run_kb_tests(payload), version=settings.app_version)


@router.post("/telephony-tests", response_model=ApiResponse[dict[str, Any]])
async def run_telephony_tests(
    payload: TelephonyTestRequest,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
    tel_router: TelephonyCallRouter = Depends(get_telephony_router_svc),
) -> ApiResponse[dict[str, Any]]:
    _require_auth(settings, authorization)
    svc = TelephonyTestService(mgmt, tel_router)
    return ok(await svc.run_telephony_test(payload), version=settings.app_version)


@router.post("/performance-tests", response_model=ApiResponse[dict[str, Any]])
async def run_performance_tests(
    payload: PerformanceTestRequest,
    settings: Settings = Depends(get_settings),
    agent_svc: AgentService = Depends(get_agent_service),
    conv_svc: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[dict[str, Any]]:
    svc = PerformanceTestService(agent_svc, conv_svc)
    return ok(await svc.run_benchmark(payload), version=settings.app_version)


@router.post("/failure-recovery-tests", response_model=ApiResponse[dict[str, Any]])
async def run_failure_recovery_tests(
    payload: FailureRecoveryTestRequest,
    settings: Settings = Depends(get_settings),
    agent_svc: AgentService = Depends(get_agent_service),
    conv_svc: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[dict[str, Any]]:
    svc = FailureRecoveryTestService(agent_svc, conv_svc)
    return ok(await svc.run_failure_checks(payload), version=settings.app_version)


@router.post("/assistant", response_model=ApiResponse[dict[str, Any]])
async def run_testing_assistant(
    payload: AssistantRequest,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    agent_svc: AgentService = Depends(get_agent_service),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    stt_svc: STTService = Depends(get_stt_service),
    tts_svc: TTSService = Depends(get_tts_service),
    mgmt: TelephonyManagementService = Depends(get_telephony_mgmt),
    orch: TestOrchestrator = Depends(get_orchestrator),
) -> ApiResponse[dict[str, Any]]:
    _require_auth(settings, authorization)
    assistant = TestingAssistantService(
        agent_svc=agent_svc,
        llm_provider=llm_provider,
        stt_svc=stt_svc,
        tts_svc=tts_svc,
        telephony_mgmt=mgmt,
        orchestrator=orch,
    )
    return ok(await assistant.analyze_and_run(payload), version=settings.app_version)


@router.websocket("/ws")
async def testing_lab_websocket(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
) -> None:
    token = websocket.headers.get("authorization") or websocket.query_params.get("token")
    if not CallAuthorizationService.authorize(settings, token):
        await websocket.close(code=4403)
        return

    await websocket.accept()
    client = monitoring_ws_hub.register(websocket)
    await websocket.send_json({"type": "CONNECTED", "client_id": client.client_id})

    async def _sender() -> None:
        while True:
            msg = await client.queue.get()
            await websocket.send_json(msg)

    sender_task = asyncio.create_task(_sender())
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                frame = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(frame, dict) and str(frame.get("type") or "").upper() == "PING":
                await websocket.send_json({"type": "PONG"})
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sender_task
        monitoring_ws_hub.unregister(client.client_id)
