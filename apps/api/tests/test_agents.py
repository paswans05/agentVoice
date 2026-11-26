"""Backend tests for Agent schemas, repository, service, and API endpoints."""

from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.providers.storage import StorageProvider
from app.repositories.agent_repository import AgentRepository
from app.schemas.agent import AgentStatus, AgentType


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app()
    test_settings = Settings(app_env="test", data_dir=str(tmp_path))
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app)


def _sample_payload(name: str = "Asha Sales") -> dict:
    return {
        "name": name,
        "description": "Hindi/Hinglish sales voice agent",
        "avatar": "briefcase",
        "type": "SALES",
        "personality": {
            "tone": "FRIENDLY",
            "traits": ["polite", "helpful"],
            "custom_instructions": "Be respectful.",
        },
        "instructions": {
            "system_prompt": "You are a helpful sales assistant for ABC Company.",
            "greeting": "Namaste! Main Asha bol rahi hoon.",
            "additional_rules": ["Never invent prices."],
        },
        "language": {
            "primary_language": "hi-IN",
            "supported_languages": ["hi-IN", "en-IN"],
            "hinglish_enabled": True,
            "response_mode": "AUTO",
        },
        "voice": {
            "provider": "piper",
            "voice_id": "hi_IN-rohan-medium",
            "speed": 1.0,
            "pitch": 1.0,
        },
    }


def test_list_templates(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    resp = client.get("/api/v1/agents/templates")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) == 5


def test_full_agent_lifecycle_and_restart_persistence(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    # 1. Create agent (starts as DRAFT)
    create_resp = client.post("/api/v1/agents", json=_sample_payload())
    assert create_resp.status_code == 201
    created = create_resp.json()["data"]
    agent_id = created["id"]
    assert created["status"] == "DRAFT"
    assert created["version"] == 1

    # 2. Retrieve agent
    get_resp = client.get(f"/api/v1/agents/{agent_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["name"] == "Asha Sales"

    # 3. Update agent (edit personality, language, voice)
    update_payload = _sample_payload("Asha Pro")
    update_payload["personality"]["tone"] = "CONFIDENT"
    update_payload["language"]["primary_language"] = "hi-IN"
    update_payload["voice"]["speed"] = 1.15
    update_resp = client.put(f"/api/v1/agents/{agent_id}", json=update_payload)
    assert update_resp.status_code == 200
    updated = update_resp.json()["data"]
    assert updated["name"] == "Asha Pro"
    assert updated["personality"]["tone"] == "CONFIDENT"
    assert updated["voice"]["speed"] == 1.15
    assert updated["version"] == 2

    # 4. Duplicate agent
    dup_resp = client.post(f"/api/v1/agents/{agent_id}/duplicate")
    assert dup_resp.status_code == 201
    dup = dup_resp.json()["data"]
    assert dup["id"] != agent_id
    assert dup["status"] == "DRAFT"
    assert dup["name"] == "Asha Pro (Copy)"

    # 5. Activate original, then deactivate
    act_resp = client.post(f"/api/v1/agents/{agent_id}/activate")
    assert act_resp.status_code == 200
    assert act_resp.json()["data"]["status"] == "ACTIVE"

    deact_resp = client.post(f"/api/v1/agents/{agent_id}/deactivate")
    assert deact_resp.status_code == 200
    assert deact_resp.json()["data"]["status"] == "INACTIVE"

    # 6. Delete duplicate
    del_resp = client.delete(f"/api/v1/agents/{dup['id']}")
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True

    # 7. Simulate backend restart with a fresh FastAPI app instance pointing to same data_dir
    restarted_client = _make_client(tmp_path)
    list_resp = restarted_client.get("/api/v1/agents")
    assert list_resp.status_code == 200
    agents = list_resp.json()["data"]
    assert len(agents) == 1
    assert agents[0]["id"] == agent_id
    assert agents[0]["status"] == "INACTIVE"


def test_filtering_and_search(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    a1 = client.post("/api/v1/agents", json=_sample_payload("Alpha Sales")).json()["data"]
    p2 = _sample_payload("Beta Support")
    p2["type"] = "CUSTOMER_SUPPORT"
    a2 = client.post("/api/v1/agents", json=p2).json()["data"]
    client.post(f"/api/v1/agents/{a1['id']}/activate")

    # Filter by status
    active_list = client.get("/api/v1/agents?status=ACTIVE").json()["data"]
    assert [a["id"] for a in active_list] == [a1["id"]]

    # Filter by type + search
    support_list = client.get("/api/v1/agents?type=CUSTOMER_SUPPORT&search=beta").json()["data"]
    assert [a["id"] for a in support_list] == [a2["id"]]


def test_validation_and_missing_id_errors(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    # Missing agent -> 404
    assert client.get("/api/v1/agents/agent_missing").status_code == 404
    assert client.delete("/api/v1/agents/agent_missing").status_code == 404

    # Invalid name -> 422
    bad_payload = _sample_payload("A")
    assert client.post("/api/v1/agents", json=bad_payload).status_code == 422

    # Activation without system_prompt -> 422
    no_prompt = _sample_payload("No Prompt")
    no_prompt["instructions"]["system_prompt"] = ""
    created = client.post("/api/v1/agents", json=no_prompt).json()["data"]
    act_resp = client.post(f"/api/v1/agents/{created['id']}/activate")
    assert act_resp.status_code == 422
    assert act_resp.json()["success"] is False


async def test_repository_handles_storage_failure() -> None:
    mock_storage = MagicMock(spec=StorageProvider)
    mock_storage.read_json.side_effect = OSError("Disk unavailable")
    repo = AgentRepository(mock_storage)

    try:
        await repo.get_by_id("agent_123")
        assert False, "Expected AgentRepositoryError"
    except Exception as exc:
        assert "Failed to read agent" in str(exc)
