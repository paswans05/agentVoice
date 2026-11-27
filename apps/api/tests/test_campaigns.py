"""Tests for Phase 8 Campaign Management, Scheduling, Eligibility, Dry-Run Execution, and Analytics."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.schemas.campaigns import CallOutcome, Campaign, CampaignStatus
from app.services.campaign_policy import CampaignRetryService, CampaignScheduler


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
