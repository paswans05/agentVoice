"""Automated tests for Asterisk 23 internal SIP/WebRTC calling and AI call bridge."""

from __future__ import annotations

import asyncio
from pathlib import Path
import struct

from fastapi.testclient import TestClient
import httpx

from app.core.config import Settings, get_settings
from app.main import create_app
from app.providers.telephony.asterisk_ari import AsteriskARIProvider
from app.providers.telephony.media import TelephonyMediaAdapter
from app.services.ai_call_bridge import AICallBridgeManager, _build_rtp_packet


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app()
    test_settings = Settings(app_env="test", data_dir=str(tmp_path))
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app)


def _setup_mocked_asterisk(client: TestClient, monkeypatch, handler) -> str:
    orig_init = AsteriskARIProvider.__init__

    def _patched_init(self, config, *, ari_password="", transport=None):
        orig_init(self, config, ari_password=ari_password, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(AsteriskARIProvider, "__init__", _patched_init)

    prov = client.post(
        "/api/v1/telephony/providers",
        json={
            "name": "Local Asterisk Mock",
            "provider_type": "asterisk",
            "host": "127.0.0.1",
            "port": 8088,
            "use_tls": False,
            "ari_username": "agentvoice",
            "ari_password": "secret",
            "caller_id": "1001",
            "enabled": True,
        },
    ).json()["data"]
    assert client.post(f"/api/v1/telephony/providers/{prov['id']}/test").json()["data"]["connected"] is True
    return prov["id"]


def test_asterisk_config_files_and_pjsip_validation() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    rtp_conf = (repo_root / "docker" / "asterisk" / "rtp.conf").read_text(encoding="utf-8")
    ext_conf = (repo_root / "docker" / "asterisk" / "extensions.conf").read_text(encoding="utf-8")
    http_conf = (repo_root / "docker" / "asterisk" / "http.conf").read_text(encoding="utf-8")
    compose = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "rtpstart=10000" in rtp_conf
    assert "rtpend=20000" in rtp_conf
    assert "icesupport=yes" in rtp_conf

    for ext in ("1001", "1002", "600", "700"):
        assert f"exten => {ext}," in ext_conf
    assert "Echo()" in ext_conf
    assert "Stasis(agentvoice" in ext_conf

    assert "enabled=yes" in http_conf
    assert "bindport=8088" in http_conf

    assert "[transport-udp]" in compose
    assert "[transport-ws]" in compose
    assert "5060:5060/udp" in compose
    assert "ASTERISK_EXT_1001_PASSWORD" in compose
    assert "ASTERISK_EXT_1002_PASSWORD" in compose


def test_internal_extensions_registration_and_secret_masking(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/asterisk/info"):
            return httpx.Response(200, json={"system": {"version": "23.5.0"}})
        if request.url.path.endswith("/endpoints/PJSIP"):
            return httpx.Response(
                200,
                json=[
                    {"resource": "1001", "state": "online", "channel_ids": []},
                    {"resource": "1002", "state": "offline", "channel_ids": []},
                    {"resource": "1001-ws", "state": "online", "channel_ids": []},
                ],
            )
        return httpx.Response(404)

    _setup_mocked_asterisk(client, monkeypatch, _handler)

    exts = client.get("/api/v1/internal-calls/extensions").json()["data"]
    by_ext = {e["extension"]: e for e in exts}
    assert by_ext["1001"]["registered"] is True
    assert by_ext["1002"]["registered"] is False
    assert by_ext["1001-ws"]["webrtc_enabled"] is True
    assert "password" not in str(exts).lower()

    health = client.get("/api/v1/internal-calls/health").json()["data"]
    assert health["ari_connected"] is True
    assert health["asterisk_version"] == "23.5.0"
    assert health["external_telephony_configured"] is False

    webrtc_cfg = client.get("/api/v1/internal-calls/webrtc-config").json()["data"]
    assert webrtc_cfg["ws_url"].startswith("ws://")
    assert "1001-ws" in webrtc_cfg["extensions"]
    assert "password" not in str(webrtc_cfg).lower()


def test_internal_call_origination_duplicate_guard_hangup_and_history(
    tmp_path: Path, monkeypatch
) -> None:
    client = _make_client(tmp_path)

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/asterisk/info"):
            return httpx.Response(200, json={"system": {"version": "23.5.0"}})
        if request.url.path.endswith("/endpoints/PJSIP"):
            return httpx.Response(200, json=[])
        if request.method == "POST" and request.url.path.endswith("/channels"):
            return httpx.Response(200, json={"id": "ast_int_1"})
        if request.method == "DELETE" and "/channels/" in request.url.path:
            return httpx.Response(204)
        return httpx.Response(404)

    _setup_mocked_asterisk(client, monkeypatch, _handler)

    # Dial 1001 -> 1002
    dial = client.post(
        "/api/v1/internal-calls/dial",
        json={"from_extension": "1001", "to_extension": "1002", "mode": "human"},
    )
    assert dial.status_code == 200
    rec = dial.json()["data"]
    assert rec["channel_id"] == "ast_int_1"
    assert rec["is_external"] is False

    # Duplicate active call blocked with 409
    dup = client.post(
        "/api/v1/internal-calls/dial",
        json={"from_extension": "1001", "to_extension": "1002", "mode": "human"},
    )
    assert dup.status_code == 409

    # Active calls list includes rec
    active = client.get("/api/v1/internal-calls/active").json()["data"]
    assert len(active) == 1
    assert active[0]["call_id"] == rec["call_id"]

    # Hangup updates status and history
    hangup = client.post(f"/api/v1/internal-calls/{rec['call_id']}/hangup")
    assert hangup.status_code == 200
    assert hangup.json()["data"]["status"] == "ENDED"
    assert client.get("/api/v1/internal-calls/active").json()["data"] == []

    history = client.get("/api/v1/internal-calls/history").json()["data"]
    assert len(history) >= 1
    fetched = client.get(f"/api/v1/internal-calls/{rec['call_id']}").json()["data"]
    assert fetched["status"] == "ENDED"


def test_external_telephony_not_configured_error_and_ari_disconnection(
    tmp_path: Path, monkeypatch
) -> None:
    client = _make_client(tmp_path)
    state = {"up": True}

    def _handler(request: httpx.Request) -> httpx.Response:
        if not state["up"]:
            raise httpx.ConnectError("ARI down", request=request)
        if request.url.path.endswith("/asterisk/info"):
            return httpx.Response(200, json={"system": {"version": "23.5.0"}})
        return httpx.Response(200, json=[])

    _setup_mocked_asterisk(client, monkeypatch, _handler)

    # External PSTN number must be rejected with EXTERNAL_TELEPHONY_NOT_CONFIGURED
    ext_resp = client.post(
        "/api/v1/internal-calls/dial",
        json={"from_extension": "1001", "to_extension": "+917982691218", "mode": "human"},
    )
    assert ext_resp.status_code == 422
    assert "EXTERNAL_TELEPHONY_NOT_CONFIGURED" in str(ext_resp.json())

    # Simulate ARI disconnection
    state["up"] = False
    health = client.get("/api/v1/internal-calls/health").json()["data"]
    assert health["ari_connected"] is False

    disc_dial = client.post(
        "/api/v1/internal-calls/dial",
        json={"from_extension": "1001", "to_extension": "600", "mode": "echo"},
    )
    assert disc_dial.status_code in (502, 503)


def test_ai_call_bridge_lifecycle_and_barge_in() -> None:
    class _FakeSTT:
        async def transcribe_pcm16(self, pcm16: bytes, sample_rate: int = 16000):
            return type("Res", (), {"text": "Hello AgentVoice"})()

    class _FakeConv:
        async def create_conversation(self, *, agent_id: str, title: str):
            return type("Conv", (), {"id": "conv_test_1"})()

        async def send_message(self, conversation_id: str, *, content: str):
            return type(
                "Turn",
                (),
                {"assistant_message": type("Msg", (), {"content": f"Reply to: {content}"})()},
            )()

    class _FakeTTS:
        async def synthesize_pcm16(self, text: str) -> bytes:
            return b"\x00\x01" * 320

    async def _run() -> None:
        mgr = AICallBridgeManager(
            stt_service=_FakeSTT(),
            conversation_service=_FakeConv(),
            tts_service=_FakeTTS(),
            vad_rms_threshold=200.0,
            silence_frames_to_commit=2,
        )
        sess = await mgr.attach_call(call_id="icall_1", channel_id="ast_1", agent_id="agent_1")
        assert sess.active is True

        # Send voiced PCM16 -> PCMU RTP packet
        voiced_pcm = struct.pack("<160h", *([2000] * 160))
        voiced_ulaw = TelephonyMediaAdapter.encode_from_pcm16(
            voiced_pcm, "PCMU", src_rate=8000, dst_rate=8000
        ).audio_bytes
        await mgr.process_inbound_rtp("icall_1", _build_rtp_packet(voiced_ulaw, seq=1, timestamp=0))

        # Send 2 silence frames to commit utterance
        silence_ulaw = TelephonyMediaAdapter.encode_from_pcm16(
            b"\x00\x00" * 160, "PCMU", src_rate=8000, dst_rate=8000
        ).audio_bytes
        await mgr.process_inbound_rtp("icall_1", _build_rtp_packet(silence_ulaw, seq=2, timestamp=160))
        reply = await mgr.process_inbound_rtp("icall_1", _build_rtp_packet(silence_ulaw, seq=3, timestamp=320))
        assert reply == "Reply to: Hello AgentVoice"

        outbound = await mgr.pop_outbound_rtp("icall_1")
        assert outbound is not None and len(outbound) > 12

        # Barge-in clears outbound queue
        sess.trigger_barge_in()
        assert await mgr.pop_outbound_rtp("icall_1") is None

        assert await mgr.detach_call("icall_1") is True
        assert sess.active is False

    asyncio.run(_run())
