"""Automated tests for the End-to-End Testing Lab & AI Client Simulator."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.v1.llm import get_llm_provider
from app.api.v1.speech import get_stt_service, get_tts_service
from app.core.config import Settings, get_settings
from app.main import create_app
from app.schemas.testing import ManualReviewRequest, SimulationTurn
from app.services.speech_service import STTService, TTSService
from app.services.testing_simulator import ConversationEvaluator
from tests.test_conversations import FakeChatProvider
from tests.test_speech_and_voice import FakeSTTProvider, FakeTTSProvider


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app()
    test_settings = Settings(
        app_env="test",
        data_dir=str(tmp_path),
        agentvoice_secret_key="test-lab-secret",
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_llm_provider] = lambda: FakeChatProvider()
    app.dependency_overrides[get_stt_service] = lambda: STTService(FakeSTTProvider())
    app.dependency_overrides[get_tts_service] = lambda: TTSService(FakeTTSProvider())
    return TestClient(app)


def _create_agent(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/agents",
        json={
            "name": "Lab Sales Agent",
            "type": "SALES",
            "instructions": {"system_prompt": "Be polite, disclose AI identity, never invent discounts."},
            "model": {"provider": "ollama", "model_id": "qwen2.5:3b"},
        },
    )
    assert resp.status_code == 201, resp.text
    aid = resp.json()["data"]["id"]
    client.post(f"/api/v1/agents/{aid}/activate")
    return aid


def test_personas_scenarios_and_simulation_text_and_voice(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    agent_id = _create_agent(client)

    # 15 built-in personas + custom persona creation
    personas = client.get("/api/v1/testing/personas").json()["data"]
    assert len(personas) >= 15

    custom_p = client.post(
        "/api/v1/testing/personas",
        json={
            "name": "Enterprise CTO",
            "description": "Asks security and compliance questions.",
            "language": "en",
            "sample_utterances": ["How are SIP credentials encrypted at rest?"],
        },
    )
    assert custom_p.status_code == 201

    # Scenario CRUD
    scen = client.post(
        "/api/v1/testing/scenarios",
        json={
            "name": "Custom Sales Check",
            "agent_id": agent_id,
            "persona_id": "interested",
            "objective": "Verify product explanation and demo offer.",
            "max_turns": 2,
        },
    )
    assert scen.status_code == 201
    scen_id = scen.json()["data"]["id"]

    # Text simulation
    text_sim = client.post(
        "/api/v1/testing/simulate",
        json={
            "agent_id": agent_id,
            "persona_id": "interested",
            "scenario_id": scen_id,
            "voice_enabled": False,
            "max_turns": 2,
        },
    )
    assert text_sim.status_code == 200
    run_text = text_sim.json()["data"]
    assert run_text["execution_mode"] == "local_simulation"
    assert len(run_text["turns"]) == 2
    assert run_text["evaluation"]["overall_score"] >= 65

    # Voice-to-Voice simulation (mocked STT + TTS + LLM)
    voice_sim = client.post(
        "/api/v1/testing/simulate",
        json={
            "agent_id": agent_id,
            "persona_id": "hinglish",
            "voice_enabled": True,
            "max_turns": 2,
        },
    )
    assert voice_sim.status_code == 200
    run_voice = voice_sim.json()["data"]
    assert run_voice["turns"][0]["customer_audio_generated"] is True
    assert run_voice["turns"][0]["agent_audio_generated"] is True

    # Report exports (JSON, CSV, Markdown) & compare
    assert client.get(f"/api/v1/testing/reports/{run_text['id']}?format=markdown").status_code == 200
    assert client.get(f"/api/v1/testing/reports/{run_text['id']}?format=csv").status_code == 200
    cmp_resp = client.get(
        f"/api/v1/testing/reports/compare?run_a={run_text['id']}&run_b={run_voice['id']}"
    )
    assert cmp_resp.status_code == 200

    # Status overview
    st = client.get("/api/v1/testing/status").json()["data"]
    assert st["total_runs"] == 2


def test_deterministic_evaluator_critical_compliance_failures() -> None:
    # Opt-out violation must fail even with manual score override
    turns = [
        SimulationTurn(
            turn_number=1,
            customer_text="No thanks, I am not interested. Please remove me.",
            agent_text="Okay, understood.",
        ),
        SimulationTurn(
            turn_number=2,
            customer_text="Goodbye.",
            agent_text="Wait! Can I still schedule a demo with a 50% discount?",
        ),
    ]
    ev = ConversationEvaluator.evaluate(turns=turns, persona_id="uninterested")
    assert ev.passed is False
    assert any("OPT_OUT" in cf for cf in ev.critical_failures)

    # Manual review cannot hide critical failure
    reviewed = ConversationEvaluator.apply_manual_review(
        ev, ManualReviewRequest(override_score=95, notes="Reviewer tried to pass")
    )
    assert reviewed.passed is False


def test_kb_telephony_perf_failure_and_assistant_suites(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    agent_id = _create_agent(client)

    # KB suite reports missing KB cleanly
    kb = client.post("/api/v1/testing/kb-tests", json={"agent_id": agent_id}).json()["data"]
    assert kb["kb_configured"] is False

    # Telephony dry-run passes; real_test_call without approval is blocked
    tel_dry = client.post(
        "/api/v1/testing/telephony-tests",
        json={"provider_id": "dry_run", "mode": "dry_run", "agent_id": agent_id},
    ).json()["data"]
    assert tel_dry["passed"] is True
    assert tel_dry["real_call_placed"] is False

    tel_real_blocked = client.post(
        "/api/v1/testing/telephony-tests",
        json={"provider_id": "dry_run", "mode": "real_test_call", "agent_id": agent_id},
    ).json()["data"]
    assert tel_real_blocked["passed"] is False

    # Performance & Failure Recovery suites
    perf = client.post(
        "/api/v1/testing/performance-tests",
        json={"agent_id": agent_id, "concurrency": 2, "iterations": 2},
    ).json()["data"]
    assert perf["completed"] == 2

    rec = client.post(
        "/api/v1/testing/failure-recovery-tests",
        json={"agent_id": agent_id},
    ).json()["data"]
    assert rec["passed"] is True

    # Autonomous Testing Assistant
    asst = client.post(
        "/api/v1/testing/assistant",
        json={
            "agent_id": agent_id,
            "instruction": "Test pricing questions, Hindi conversations, and opt-outs.",
            "execute": True,
        },
    ).json()["data"]
    assert asst["readiness"]["llm_available"] is True
    assert len(asst["executed_runs"]) >= 2

    # WebSocket heartbeat
    with client.websocket_connect("/api/v1/testing/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "CONNECTED"
        ws.send_json({"type": "PING"})
        assert ws.receive_json()["type"] == "PONG"
