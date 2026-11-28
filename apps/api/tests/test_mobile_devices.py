"""Automated tests for Android & iPhone Device Gateway, Pairing, Auth, Commands, and Mobile VoIP."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings, get_settings
from app.main import create_app
from app.providers.storage import JSONStorageProvider
from app.repositories.device_repository import DeviceRepository


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app()
    test_settings = Settings(
        app_env="test",
        data_dir=str(tmp_path),
        agentvoice_secret_key="test-device-gateway-secret",
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app)


def test_pairing_single_use_expiry_and_credential_protection(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    # 1. Generate Android pairing code
    code_resp = client.post(
        "/api/v1/devices/pairing-codes",
        json={"platform": "android", "account_id": "op_1", "ttl_seconds": 300},
    )
    assert code_resp.status_code == 201
    code = code_resp.json()["data"]["code"]

    # 2. Pair Android device (even if client attempts to claim cellular audio, backend forces false)
    pair_resp = client.post(
        "/api/v1/devices/pair",
        json={
            "pairing_code": code,
            "device_name": "Pixel 8 Gateway",
            "platform": "android",
            "platform_version": "14",
            "app_version": "0.1.0",
            "capability_profile": {
                "platform": "android",
                "cellular_call_initiation": True,
                "cellular_call_state": True,
                "cellular_audio_capture": True,
                "cellular_audio_injection": True,
                "voip_supported": True,
                "ai_call_ready": True,
            },
        },
    )
    assert pair_resp.status_code == 201
    data = pair_resp.json()["data"]
    device = data["device"]
    token = data["device_token"]
    assert token.startswith("avd_")
    assert device["capability_profile"]["cellular_audio_capture"] is False
    assert device["capability_profile"]["cellular_audio_injection"] is False
    assert device["capability_profile"]["cellular_audio_bridge_status"] == "CELLULAR_AUDIO_BRIDGE_UNAVAILABLE"
    assert device["capability_profile"]["ai_call_ready"] is False

    # 3. Single-use enforcement: reusing same code must fail (422)
    reuse_resp = client.post(
        "/api/v1/devices/pair",
        json={
            "pairing_code": code,
            "device_name": "Duplicate",
            "platform": "android",
            "platform_version": "14",
            "app_version": "0.1.0",
        },
    )
    assert reuse_resp.status_code == 422

    # 4. GET /devices never exposes token
    list_resp = client.get("/api/v1/devices")
    assert list_resp.status_code == 200
    assert token not in list_resp.text

    # 5. Expired pairing code rejected
    storage = JSONStorageProvider(tmp_path)
    repo = DeviceRepository(storage, "test-device-gateway-secret")
    codes = repo.list_pairing_codes()
    codes[0] = codes[0].model_copy(
        update={"used": False, "expires_at": datetime.now(timezone.utc) - timedelta(seconds=10)}
    )
    repo.save_pairing_codes(codes)
    exp_resp = client.post(
        "/api/v1/devices/pair",
        json={
            "pairing_code": codes[0].code,
            "device_name": "Expired",
            "platform": "android",
            "platform_version": "14",
            "app_version": "0.1.0",
        },
    )
    assert exp_resp.status_code == 422


def test_heartbeat_commands_revocation_ws_and_mobile_voip(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    # Pair iPhone Companion
    code = client.post(
        "/api/v1/devices/pairing-codes",
        json={"platform": "ios", "account_id": "op_1"},
    ).json()["data"]["code"]
    paired = client.post(
        "/api/v1/devices/pair",
        json={
            "pairing_code": code,
            "device_name": "iPhone 15 Companion",
            "platform": "ios",
            "platform_version": "17.5",
            "app_version": "0.1.0",
        },
    ).json()["data"]
    dev_id = paired["device"]["id"]
    token = paired["device_token"]
    assert paired["device"]["capability_profile"]["callkit_supported"] is True

    # Heartbeat with valid device token succeeds
    hb_resp = client.post(
        f"/api/v1/devices/{dev_id}/heartbeat",
        headers={"X-Device-Token": token},
        json={
            "health": {
                "battery_percent": 85,
                "battery_charging": False,
                "network_type": "wifi",
                "connected": True,
                "permissions": {"microphone": True},
            }
        },
    )
    assert hb_resp.status_code == 200
    assert hb_resp.json()["data"]["health"]["battery_percent"] == 85

    # Heartbeat with wrong token fails (403)
    bad_hb = client.post(
        f"/api/v1/devices/{dev_id}/heartbeat",
        headers={"X-Device-Token": "wrong-token"},
        json={"health": {"network_type": "wifi", "connected": True}},
    )
    assert bad_hb.status_code == 403

    # Device command enqueue & retrieve
    cmd_resp = client.post(
        f"/api/v1/devices/{dev_id}/commands",
        json={"command_type": "PING", "payload": {}},
    )
    assert cmd_resp.status_code == 201
    cmd_id = cmd_resp.json()["data"]["id"]
    assert client.get(f"/api/v1/devices/{dev_id}/commands/{cmd_id}").status_code == 200

    # Mobile VoIP session linked to CallSessionService
    voip_resp = client.post(
        "/api/v1/mobile-voip/sessions",
        json={"device_id": dev_id, "agent_id": "agent_demo", "direction": "OUTBOUND"},
    )
    assert voip_resp.status_code == 201
    voip_data = voip_resp.json()["data"]
    assert voip_data["call_source"] == "AGENTVOICE_VOIP"
    assert voip_data["call_session_id"] is not None

    term_resp = client.post(f"/api/v1/mobile-voip/sessions/{voip_data['id']}/terminate")
    assert term_resp.status_code == 200
    assert term_resp.json()["data"]["status"] == "TERMINATED"

    # WebSocket authenticated with device token
    with client.websocket_connect(f"/api/v1/devices/ws?device_id={dev_id}&token={token}") as ws:
        assert ws.receive_json()["type"] == "CONNECTED"
        ws.send_json({"type": "PING"})
        assert ws.receive_json()["type"] == "PONG"

    # Revoke device: subsequent heartbeats & WS connections are rejected
    rev_resp = client.post(f"/api/v1/devices/{dev_id}/revoke")
    assert rev_resp.status_code == 200
    assert rev_resp.json()["data"]["device_status"] == "REVOKED"

    rev_hb = client.post(
        f"/api/v1/devices/{dev_id}/heartbeat",
        headers={"X-Device-Token": token},
        json={"health": {"network_type": "wifi", "connected": True}},
    )
    assert rev_hb.status_code == 403

    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/v1/devices/ws?device_id={dev_id}&token={token}") as ws:
            ws.receive_json()


def test_safari_pairing_confirm_and_webrtc_signaling(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    # 1. Generate 60s pairing code via /devices/pairing
    code_resp = client.post(
        "/api/v1/devices/pairing",
        json={"platform": "ios", "account_id": "op_safari", "ttl_seconds": 60},
    )
    assert code_resp.status_code == 201
    code = code_resp.json()["data"]["code"]

    # 2. Pair iPhone Safari browser
    paired = client.post(
        "/api/v1/devices/pair",
        json={
            "pairing_code": code,
            "device_name": "iPhone 13 Safari",
            "platform": "ios",
            "platform_version": "iOS 26 (Safari)",
            "app_version": "0.1.0-safari",
            "capability_profile": {
                "platform": "ios",
                "webrtc_supported": True,
                "browser": "Safari",
                "voip_supported": True,
                "cellular_audio_capture": False,
                "cellular_audio_injection": False,
            },
        },
    ).json()["data"]
    dev_id = paired["device"]["id"]
    token = paired["device_token"]

    # 3. Desktop confirm pairing
    confirm = client.post("/api/v1/devices/pairing/confirm", json={"device_id": dev_id})
    assert confirm.status_code == 200
    assert confirm.json()["data"]["id"] == dev_id

    # 4. Create WebRTC session & verify CallSession integration
    wrtc = client.post(
        "/api/v1/webrtc/sessions",
        headers={"X-Device-Token": token},
        json={"device_id": dev_id, "agent_id": "agent_demo"},
    )
    assert wrtc.status_code == 201
    wrtc_data = wrtc.json()["data"]
    assert wrtc_data["call_source"] == "AGENTVOICE_INTERNET_VOICE_CALL"
    assert wrtc_data["call_session_id"] is not None

    # 5. Authenticated WebRTC WebSocket signaling
    with client.websocket_connect(f"/api/v1/webrtc/ws?device_id={dev_id}&token={token}") as ws:
        assert ws.receive_json()["type"] == "SIGNALING_CONNECTED"
        ws.send_json({"type": "OFFER", "session_id": wrtc_data["id"], "sdp": "v=0..."})
        assert ws.receive_json()["type"] == "OFFER_ACK"
        ws.send_json({"type": "ICE_STATE", "session_id": wrtc_data["id"], "state": "connected"})
        assert ws.receive_json()["state"] == "connected"
        ws.send_json({"type": "PING"})
        assert ws.receive_json()["type"] == "PONG"

    # 6. Terminate WebRTC session
    term = client.post(f"/api/v1/webrtc/sessions/{wrtc_data['id']}/terminate")
    assert term.status_code == 200
    assert term.json()["data"]["status"] == "TERMINATED"
