"""Tests for health and system status endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app


def _make_test_client(tmp_path: Path) -> TestClient:
    app = create_app()
    test_settings = Settings(
        app_env="test",
        data_dir=str(tmp_path),
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app)


def test_health_endpoint(tmp_path: Path) -> None:
    client = _make_test_client(tmp_path)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert "meta" in body
    assert body["data"]["service"] == "agentVoice"
    assert body["data"]["status"] == "healthy"
    assert body["data"]["storage"]["backend"] == "json"
    assert body["data"]["storage"]["writable"] is True


def test_readiness_endpoint(tmp_path: Path) -> None:
    client = _make_test_client(tmp_path)
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["ready"] is True
    assert body["data"]["storage_writable"] is True


def test_system_status_endpoint(tmp_path: Path) -> None:
    client = _make_test_client(tmp_path)
    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["app_name"] == "agentVoice"
    assert data["external_ai_required"] is False
    assert data["offline_ready"] is True
    assert data["phases"]["current_phase"] == 8
