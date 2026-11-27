"""Phase 9 Live Calls & Real-Time Monitoring automated tests."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
import pytest

from app.api.v1.llm import get_llm_provider
from app.core.config import Settings, get_settings
from app.main import create_app
from tests.test_conversations import FakeChatProvider
from app.providers.storage import JSONStorageProvider
from app.repositories.call_session_repository import (
    CallEventRepository,
    CallMetricsRepository,
    CallSessionRepository,
    TranscriptRepository,
)
from app.schemas.live_calls import (
    CallDirection,
    CallEventType,
    CallSessionStatus,
    CallSessionType,
    TranscriptSpeaker,
)
from app.services.live_calls_service import CallSessionService


def _make_client(tmp_path, monkeypatch, *, require_auth: bool = False) -> TestClient:
    app = create_app()
    test_settings = Settings(
        app_env="test",
        data_dir=str(tmp_path),
        require_auth=require_auth,
        agentvoice_secret_key="test-operator-secret",
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_llm_provider] = lambda: FakeChatProvider()
    return TestClient(app)


def _create_test_agent(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/agents",
        json={
            "name": "Monitor Agent",
            "type": "SALES",
            "instructions": {"system_prompt": "Assist callers politely."},
            "model": {"provider": "ollama", "model_id": "qwen2.5:3b"},
        },
    )
    assert resp.status_code == 201, resp.text
    agent_id = resp.json()["data"]["id"]
    client.post(f"/api/v1/agents/{agent_id}/activate")
    return agent_id


def test_call_session_lifecycle_dedup_and_transcript_search(tmp_path, monkeypatch) -> None:
    storage = JSONStorageProvider(tmp_path)
    storage.ensure_initialized()
    svc = CallSessionService(
        session_repo=CallSessionRepository(storage),
        event_repo=CallEventRepository(storage),
        transcript_repo=TranscriptRepository(storage),
        metrics_repo=CallMetricsRepository(storage),
    )

    async def _run() -> None:
        session = await svc.create_session(
            agent_id="agent_1",
            session_type=CallSessionType.TELEPHONY,
            direction=CallDirection.OUTBOUND,
            provider="dry_run",
            caller_number="+919876543210",
            destination_number="+919811223344",
        )
        assert session.recording_enabled is False
        assert "3210" in session.caller_number_masked
        assert "987654" not in session.caller_number_masked

        # Duplicate event_id should be ignored
        ev1 = await svc.publish_event(
            call_id=session.id,
            event_type=CallEventType.CALL_RINGING,
            event_id="evt_dup_1",
        )
        ev2 = await svc.publish_event(
            call_id=session.id,
            event_type=CallEventType.CALL_RINGING,
            event_id="evt_dup_1",
        )
        assert ev1 is not None
        assert ev2 is None

        # Partial -> Final transcript replacement & Hindi search
        await svc.record_transcript_segment(
            call_id=session.id,
            speaker=TranscriptSpeaker.CUSTOMER,
            text="आपके product",
            final=False,
            segment_id="seg_1",
        )
        await svc.record_transcript_segment(
            call_id=session.id,
            speaker=TranscriptSpeaker.CUSTOMER,
            text="आपके product की कीमत क्या है?",
            final=True,
            segment_id="seg_1",
        )
        await svc.record_metrics(
            call_id=session.id,
            stt_ms=120,
            llm_ttft_ms=180,
            llm_total_ms=420,
            tts_ms=150,
            end_to_end_ms=870,
        )

        transcript = await TranscriptRepository(storage).list_by_call(session.id)
        assert len(transcript) == 1
        assert transcript[0].final is True
        assert "कीमत" in transcript[0].text

        matches = await TranscriptRepository(storage).search_by_call(session.id, "कीमत")
        assert len(matches) == 1

        ended = await svc.end_session(session.id, status=CallSessionStatus.COMPLETED, outcome="ANSWERED")
        assert ended.status == CallSessionStatus.COMPLETED
        assert ended.duration_seconds >= 0

    asyncio.run(_run())


def test_live_calls_rest_controls_and_settings(tmp_path, monkeypatch) -> None:
    client = _make_client(tmp_path, monkeypatch, require_auth=False)
    storage = JSONStorageProvider(tmp_path)
    storage.ensure_initialized()
    svc = CallSessionService(
        session_repo=CallSessionRepository(storage),
        event_repo=CallEventRepository(storage),
        transcript_repo=TranscriptRepository(storage),
        metrics_repo=CallMetricsRepository(storage),
    )

    session = asyncio.run(
        svc.create_session(
            agent_id="agent_ctrl",
            session_type=CallSessionType.BROWSER,
            direction=CallDirection.INBOUND,
            provider="browser",
        )
    )

    # Stats & list
    stats_resp = client.get("/api/v1/live-calls/stats")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["data"]["active_calls"] == 1

    list_resp = client.get("/api/v1/live-calls?active_only=true")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) == 1

    # Hold & Transfer fail closed (422) on browser session
    hold_resp = client.post(f"/api/v1/live-calls/{session.id}/hold")
    assert hold_resp.status_code == 422

    transfer_resp = client.post(
        f"/api/v1/live-calls/{session.id}/transfer",
        json={"destination": "+919900112233", "reason": "Escalate"},
    )
    assert transfer_resp.status_code == 422

    # Flag & Terminate succeed
    flag_resp = client.post(
        f"/api/v1/live-calls/{session.id}/flag",
        json={"reason": "Supervisor review requested"},
    )
    assert flag_resp.status_code == 200
    assert flag_resp.json()["data"]["flagged_for_review"] is True

    term_resp = client.post(
        f"/api/v1/live-calls/{session.id}/terminate",
        json={"reason": "Operator ended call"},
    )
    assert term_resp.status_code == 200
    assert term_resp.json()["data"]["status"] == "TERMINATED"

    # Settings default: recording disabled
    cfg_resp = client.get("/api/v1/live-calls/settings")
    assert cfg_resp.status_code == 200
    assert cfg_resp.json()["data"]["recording_enabled_by_default"] is False


def test_live_calls_ws_auth_subscribe_heartbeat_and_voice_integration(tmp_path, monkeypatch) -> None:
    # 1. Auth enforcement when require_auth=True
    auth_client = _make_client(tmp_path, monkeypatch, require_auth=True)
    with pytest.raises(Exception):
        with auth_client.websocket_connect("/api/v1/live-calls/ws") as ws:
            ws.receive_json()

    with auth_client.websocket_connect("/api/v1/live-calls/ws?token=test-operator-secret") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "CONNECTED"
        ws.send_json({"type": "PING"})
        assert ws.receive_json()["type"] == "PONG"
        ws.send_json({"type": "SUBSCRIBE", "call_ids": ["call_demo"]})
        assert ws.receive_json()["type"] == "SUBSCRIBED"
        ws.send_text("{bad-json")
        err = ws.receive_json()
        assert err["type"] == "ERROR"

    # 2. Browser Voice Session -> Live Calls monitoring integration
    client = _make_client(tmp_path, monkeypatch, require_auth=False)
    agent_id = _create_test_agent(client)
    vs_resp = client.post(
        "/api/v1/voice/sessions",
        json={"agent_id": agent_id},
    )
    assert vs_resp.status_code == 201, vs_resp.text
    vs_id = vs_resp.json()["data"]["session_id"]

    with client.websocket_connect(f"/api/v1/voice/sessions/{vs_id}/stream") as ws:
        state_msg = ws.receive_json()
        assert state_msg["type"] == "session.state"
        live_list = client.get("/api/v1/live-calls?active_only=true").json()["data"]
        assert any(c["external_call_id"] == vs_id for c in live_list)
        ws.send_json({"type": "session.end"})

    # After disconnect, call session should be completed
    all_calls = client.get("/api/v1/live-calls?active_only=false").json()["data"]
    matching = [c for c in all_calls if c["external_call_id"] == vs_id]
    assert len(matching) == 1
    assert matching[0]["status"] == "COMPLETED"
