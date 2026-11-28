"""Tests for Phase 8 Campaign Management, Scheduling, Eligibility, Dry-Run Execution, and Analytics."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.schemas.campaigns import CallOutcome, Campaign, CampaignStatus
from app.services.campaign_policy import CampaignRetryService, CampaignScheduler
from app.providers.telephony import AsteriskARIProvider


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app()
    test_settings = Settings(app_env="test", data_dir=str(tmp_path))
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app)


def _setup_agent_and_leads(client: TestClient) -> tuple[str, str, str, str]:
    # Create and activate an agent
    agent = client.post(
        "/api/v1/agents",
        json={
            "name": "Asha Campaign Agent",
            "type": "SALES",
            "instructions": {"system_prompt": "Be polite and disclose AI identity."},
        },
    ).json()["data"]
    client.post(f"/api/v1/agents/{agent['id']}/activate")

    # Lead 1: Valid phone + GRANTED PHONE consent
    l1 = client.post(
        "/api/v1/leads",
        json={"full_name": "Eligible Lead", "phone": "+919811111111"},
    ).json()["data"]
    client.post(
        f"/api/v1/leads/{l1['id']}/consent",
        json={
            "channel": "PHONE",
            "purpose": "SALES_CALLS",
            "consent_status": "GRANTED",
            "source": "optin_form",
        },
    )

    # Lead 2: Valid phone + UNKNOWN consent (must be skipped)
    l2 = client.post(
        "/api/v1/leads",
        json={"full_name": "Unknown Consent Lead", "phone": "+919822222222"},
    ).json()["data"]

    # Lead 3: Suppressed (must be DO_NOT_CONTACT)
    l3 = client.post(
        "/api/v1/leads",
        json={"full_name": "Suppressed Lead", "phone": "+919833333333"},
    ).json()["data"]
    client.post(
        "/api/v1/suppression-list",
        json={"lead_id": l3["id"], "reason": "Opted out"},
    )

    return agent["id"], l1["id"], l2["id"], l3["id"]


def test_scheduler_and_retry_logic() -> None:
    c = Campaign(
        id="cmp_1",
        name="Test",
        agent_id="agent_1",
        timezone="Asia/Kolkata",
        calling_days=[0, 1, 2, 3, 4],
        start_time="09:00",
        end_time="18:00",
        maximum_attempts_per_lead=3,
        retry_interval_minutes=10,
    )
    assert CampaignScheduler.validate_schedule(c) == []

    # 2026-11-27 is Friday (weekday=4); 06:00 UTC = 11:30 IST -> inside window
    ok, _ = CampaignScheduler.is_within_calling_window(
        c, now_utc=datetime(2026, 11, 27, 6, 0, tzinfo=timezone.utc)
    )
    assert ok is True

    # 15:00 UTC = 20:30 IST -> outside window
    outside, _ = CampaignScheduler.is_within_calling_window(
        c, now_utc=datetime(2026, 11, 27, 15, 0, tzinfo=timezone.utc)
    )
    assert outside is False

    # Retry rules
    assert CampaignRetryService.should_retry(c, CallOutcome.NO_ANSWER, 1) is True
    assert CampaignRetryService.should_retry(c, CallOutcome.NO_ANSWER, 3) is False
    assert CampaignRetryService.should_retry(c, CallOutcome.DO_NOT_CALL, 1) is False
    assert CampaignRetryService.should_retry(c, CallOutcome.INTERESTED, 1) is False


def test_campaign_dry_run_execution_eligibility_and_analytics(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    agent_id, l1_id, l2_id, l3_id = _setup_agent_and_leads(client)

    # Create dry-run campaign
    camp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Q4 Hindi Sales",
            "campaign_type": "SALES",
            "agent_id": agent_id,
            "calling_purpose": "SALES_CALLS",
            "selected_lead_ids": [l1_id, l2_id, l3_id],
            "dry_run": True,
            "telephony_provider": "dry_run",
        },
    ).json()["data"]
    cid = camp["id"]
    assert camp["status"] == "DRAFT"

    # Validate campaign -> 1 eligible, 2 ineligible
    val = client.post(f"/api/v1/campaigns/{cid}/validate").json()["data"]
    assert val["valid"] is True
    assert val["eligibility"]["total_selected"] == 3
    assert val["eligibility"]["eligible_count"] == 1
    assert val["eligibility"]["suppressed_count"] == 1
    assert val["eligibility"]["unknown_consent_count"] == 2

    # Execute inline dry-run
    act = client.post(f"/api/v1/campaigns/{cid}/activate?run_inline=true&bypass_window=true")
    assert act.status_code == 200
    assert act.json()["data"]["status"] == "COMPLETED"

    # Check jobs: 1 COMPLETED, 1 SKIPPED, 1 DO_NOT_CONTACT
    jobs = client.get(f"/api/v1/campaigns/{cid}/jobs").json()["data"]
    statuses = {j["lead_id"]: j["status"] for j in jobs}
    assert statuses[l1_id] == "COMPLETED"
    assert statuses[l2_id] == "SKIPPED"
    assert statuses[l3_id] == "DO_NOT_CONTACT"

    # Check calls & analytics: 1 simulated call, 0 real calls
    calls = client.get(f"/api/v1/campaigns/{cid}/calls").json()["data"]
    assert len(calls) == 1
    assert calls[0]["is_dry_run"] is True

    analytics = client.get(f"/api/v1/campaigns/{cid}/analytics").json()["data"]
    assert analytics["dry_run_calls_simulated"] == 1
    assert analytics["real_calls_initiated"] == 0

    overview = client.get("/api/v1/campaigns/analytics/overview").json()["data"]
    assert overview["completed_campaigns"] == 1
    assert overview["total_real_calls"] == 0
    assert overview["total_dry_run_calls"] == 1


def test_real_telephony_blocked_without_authorized_provider(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    agent_id, l1_id, _, _ = _setup_agent_and_leads(client)

    camp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Real SIP Attempt",
            "agent_id": agent_id,
            "selected_lead_ids": [l1_id],
            "dry_run": False,
            "telephony_provider": "sip",
        },
    ).json()["data"]

    val = client.post(f"/api/v1/campaigns/{camp['id']}/validate").json()["data"]
    assert val["valid"] is False

    act = client.post(f"/api/v1/campaigns/{camp['id']}/activate")
    assert act.status_code == 422

    # Telephony status reports dry-run available and real unavailable
    tel = client.get("/api/v1/telephony/status").json()["data"]
    assert tel["real_telephony_configured"] is False
    assert tel["dry_run_available"] is True
    assert client.post("/api/v1/telephony/test-connection?provider_id=sip").status_code == 422


def test_campaign_pause_stop_cancel_lifecycle(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    agent_id, l1_id, _, _ = _setup_agent_and_leads(client)

    c1 = client.post(
        "/api/v1/campaigns",
        json={"name": "Cancel Me", "agent_id": agent_id, "selected_lead_ids": [l1_id]},
    ).json()["data"]
    assert client.post(f"/api/v1/campaigns/{c1['id']}/cancel").json()["data"]["status"] == "CANCELLED"

    c2 = client.post(
        "/api/v1/campaigns",
        json={"name": "Stop Me", "agent_id": agent_id, "selected_lead_ids": [l1_id]},
    ).json()["data"]
    assert client.post(f"/api/v1/campaigns/{c2['id']}/stop").json()["data"]["status"] == "STOPPED"


def _create_connected_asterisk_provider(
    client: TestClient,
    monkeypatch,
    handler,
) -> str:
    orig_init = AsteriskARIProvider.__init__

    def _patched_init(self, config, *, ari_password="", transport=None):
        orig_init(self, config, ari_password=ari_password, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(AsteriskARIProvider, "__init__", _patched_init)

    prov = client.post(
        "/api/v1/telephony/providers",
        json={
            "name": "Test Asterisk",
            "provider_type": "asterisk",
            "host": "127.0.0.1",
            "port": 8088,
            "use_tls": False,
            "ari_username": "agentvoice",
            "ari_password": "secret",
            "caller_id": "+911140001234",
            "enabled": True,
        },
    ).json()["data"]
    test_res = client.post(f"/api/v1/telephony/providers/{prov['id']}/test").json()["data"]
    assert test_res["connected"] is True
    return prov["id"]


def test_campaign_activation_validation_and_safety_guards(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    agent_id, l1_id, l2_id, l3_id = _setup_agent_and_leads(client)

    # 1. Missing required fields on create -> 422
    bad_create = client.post("/api/v1/campaigns", json={"name": "X"})
    assert bad_create.status_code == 422

    # 2. Empty eligible-contact list (only unknown-consent & suppressed leads) -> 422 on activate
    no_elig = client.post(
        "/api/v1/campaigns",
        json={
            "name": "No Eligible",
            "agent_id": agent_id,
            "selected_lead_ids": [l2_id, l3_id],
            "dry_run": True,
        },
    ).json()["data"]
    act_no_elig = client.post(f"/api/v1/campaigns/{no_elig['id']}/activate?run_inline=true")
    assert act_no_elig.status_code == 422
    assert "eligible" in act_no_elig.json()["detail"].lower()

    # 3. Missing / inactive agent configuration -> 422 on activate
    draft_agent = client.post(
        "/api/v1/agents",
        json={"name": "Draft Agent", "type": "SALES"},
    ).json()["data"]
    bad_agent_camp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Draft Agent Camp",
            "agent_id": draft_agent["id"],
            "selected_lead_ids": [l1_id],
            "dry_run": True,
        },
    ).json()["data"]
    act_bad_agent = client.post(f"/api/v1/campaigns/{bad_agent_camp['id']}/activate?run_inline=true")
    assert act_bad_agent.status_code == 422
    assert "active" in act_bad_agent.json()["detail"].lower()


def test_real_telephony_asterisk_unavailable_blocks_activation(
    tmp_path: Path, monkeypatch
) -> None:
    client = _make_client(tmp_path)
    agent_id, l1_id, _, _ = _setup_agent_and_leads(client)

    state = {"available": True}

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/asterisk/info"):
            if state["available"]:
                return httpx.Response(200, json={"system": {"version": "23.5.0"}})
            raise httpx.ConnectError("Connection refused", request=request)
        return httpx.Response(404)

    prov_id = _create_connected_asterisk_provider(client, monkeypatch, _handler)
    camp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Real Asterisk Unreachable",
            "agent_id": agent_id,
            "selected_lead_ids": [l1_id],
            "dry_run": False,
            "telephony_provider": prov_id,
            "timezone": "UTC",
            "calling_days": [0, 1, 2, 3, 4, 5, 6],
            "start_time": "00:00",
            "end_time": "23:59",
        },
    ).json()["data"]

    # Now Asterisk becomes unreachable before activation
    state["available"] = False
    act = client.post(f"/api/v1/campaigns/{camp['id']}/activate?run_inline=true&bypass_window=true")
    assert act.status_code == 422
    detail = act.json()["detail"].lower()
    assert "unable to reach" in detail or "not reachable" in detail


def test_real_telephony_calling_window_not_bypassed(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    agent_id, l1_id, _, _ = _setup_agent_and_leads(client)

    called_channels = []

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/asterisk/info"):
            return httpx.Response(200, json={"system": {"version": "23.5.0"}})
        if request.method == "POST" and request.url.path.endswith("/channels"):
            called_channels.append(request)
            return httpx.Response(200, json={"id": "ast_chan_never"})
        return httpx.Response(404)

    prov_id = _create_connected_asterisk_provider(client, monkeypatch, _handler)

    # Pick a 1-minute window 2 hours ago in UTC so it is guaranteed outside window
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    win_start = past.strftime("%H:%M")
    win_end = (past + timedelta(minutes=1)).strftime("%H:%M")
    if win_end <= win_start:
        win_start, win_end = "00:00", "00:01"

    camp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Outside Window Real",
            "agent_id": agent_id,
            "selected_lead_ids": [l1_id],
            "dry_run": False,
            "telephony_provider": prov_id,
            "timezone": "UTC",
            "calling_days": [0, 1, 2, 3, 4, 5, 6],
            "start_time": win_start,
            "end_time": win_end,
        },
    ).json()["data"]

    # Even with bypass_window=true, real telephony must NOT bypass calling window
    act = client.post(f"/api/v1/campaigns/{camp['id']}/activate?run_inline=true&bypass_window=true")
    assert act.status_code == 200
    assert len(called_channels) == 0
    jobs = client.get(f"/api/v1/campaigns/{camp['id']}/jobs").json()["data"]
    assert len(jobs) == 1
    assert jobs[0]["status"] == "SKIPPED"
    assert "window" in (jobs[0]["error_message"] or "").lower()


def test_real_telephony_ari_origination_failure_marks_failed(
    tmp_path: Path, monkeypatch
) -> None:
    client = _make_client(tmp_path)
    agent_id, l1_id, _, _ = _setup_agent_and_leads(client)

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/asterisk/info"):
            return httpx.Response(200, json={"system": {"version": "23.5.0"}})
        if request.method == "POST" and request.url.path.endswith("/channels"):
            return httpx.Response(500, json={"message": "SIP trunk down"})
        return httpx.Response(404)

    prov_id = _create_connected_asterisk_provider(client, monkeypatch, _handler)
    camp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "ARI Failure Test",
            "agent_id": agent_id,
            "selected_lead_ids": [l1_id],
            "dry_run": False,
            "telephony_provider": prov_id,
            "timezone": "UTC",
            "calling_days": [0, 1, 2, 3, 4, 5, 6],
            "start_time": "00:00",
            "end_time": "23:59",
            "maximum_attempts_per_lead": 1,
        },
    ).json()["data"]

    act = client.post(f"/api/v1/campaigns/{camp['id']}/activate?run_inline=true")
    assert act.status_code == 200

    calls = client.get(f"/api/v1/campaigns/{camp['id']}/calls").json()["data"]
    assert len(calls) == 1
    assert calls[0]["is_dry_run"] is False
    assert calls[0]["outcome"] == "FAILED"
    assert calls[0]["error_message"] or "failed" in calls[0]["summary"].lower()


def test_real_telephony_successful_mocked_outbound_origination_and_progress(
    tmp_path: Path, monkeypatch
) -> None:
    client = _make_client(tmp_path)
    agent_id, l1_id, l2_id, l3_id = _setup_agent_and_leads(client)

    channel_requests: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/asterisk/info"):
            return httpx.Response(200, json={"system": {"version": "23.5.0"}})
        if request.method == "POST" and request.url.path.endswith("/channels"):
            channel_requests.append(request)
            return httpx.Response(200, json={"id": "ast_chan_99"})
        return httpx.Response(404)

    prov_id = _create_connected_asterisk_provider(client, monkeypatch, _handler)

    # Verify /telephony/status now reports real telephony configured
    tel_status = client.get("/api/v1/telephony/status").json()["data"]
    assert tel_status["real_telephony_configured"] is True

    camp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Real Outbound Success",
            "agent_id": agent_id,
            "selected_lead_ids": [l1_id, l2_id, l3_id],
            "dry_run": False,
            "telephony_provider": prov_id,
            "timezone": "UTC",
            "calling_days": [0, 1, 2, 3, 4, 5, 6],
            "start_time": "00:00",
            "end_time": "23:59",
        },
    ).json()["data"]

    act = client.post(f"/api/v1/campaigns/{camp['id']}/activate?run_inline=true&bypass_window=true")
    assert act.status_code == 200
    assert act.json()["data"]["status"] == "COMPLETED"

    # Exactly 1 ARI channel origination (Lead 1 only; Lead 2 unknown consent & Lead 3 suppressed skipped)
    assert len(channel_requests) == 1
    ari_body = channel_requests[0].content.decode("utf-8")
    assert "919811111111" in ari_body
    assert "+911140001234" in ari_body

    progress = client.get(f"/api/v1/campaigns/{camp['id']}/progress").json()["data"]
    assert progress["total_jobs"] == 3
    assert progress["completed_jobs"] == 1

    calls = client.get(f"/api/v1/campaigns/{camp['id']}/calls").json()["data"]
    assert len(calls) == 1
    assert calls[0]["is_dry_run"] is False
    assert calls[0]["provider_call_id"] == "ast_chan_99"

    # Verify CallSession created with external_call_id & masked caller number
    sessions_data = client.get("/api/v1/live-calls?active_only=false").json()["data"]
    sessions = sessions_data["items"] if isinstance(sessions_data, dict) else sessions_data
    assert any(
        s.get("external_call_id") == "ast_chan_99" and bool(s.get("caller_number_masked"))
        for s in sessions
    )

    analytics = client.get(f"/api/v1/campaigns/{camp['id']}/analytics").json()["data"]
    assert analytics["real_calls_initiated"] == 1
    assert analytics["dry_run_calls_simulated"] == 0
