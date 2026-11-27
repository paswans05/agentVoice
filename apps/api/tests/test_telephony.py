"""Phase 10 Telephony Integration automated tests (mocked providers, no real calls)."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from pathlib import Path

from fastapi.testclient import TestClient
import httpx

from app.core.config import Settings, get_settings
from app.main import create_app
from app.providers.storage import JSONStorageProvider
from app.providers.telephony import (
    AsteriskARIProvider,
    AudioFrameBuffer,
    GsmGatewayProvider,
    TelephonyMediaAdapter,
    TelephonyMediaError,
)
from app.repositories.agent_repository import AgentRepository
from app.repositories.call_session_repository import (
    CallEventRepository,
    CallMetricsRepository,
    CallSessionRepository,
    TranscriptRepository,
)
from app.repositories.telephony_repository import TelephonyRepository
from app.schemas.live_calls import CallDirection, CallSessionType
from app.schemas.telephony import (
    GsmGatewayPublic,
    ProviderConnectionStatus,
    TelephonyProviderCreate,
    TelephonyProviderPublic,
    TelephonyProviderType,
)
from app.services.agent_service import AgentService
from app.services.live_calls_service import CallSessionService
from app.services.telephony_service import (
    TelephonyCallRouter,
    TelephonyManagementService,
    TelephonyPolicyError,
)


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app()
    test_settings = Settings(
        app_env="test",
        data_dir=str(tmp_path),
        agentvoice_secret_key="test-telephony-secret-key",
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app)


def test_provider_crud_secret_masking_and_trunks_routes(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    # Create Asterisk provider with secrets
    create_resp = client.post(
        "/api/v1/telephony/providers",
        json={
            "name": "Local Asterisk PBX",
            "provider_type": "asterisk",
            "host": "10.0.0.5",
            "port": 8089,
            "use_tls": True,
            "transport": "TLS",
            "ari_username": "ari_user",
            "ari_password": "super-secret-ari-password",
            "caller_id": "+911140001234",
            "allowed_destinations": ["+91*"],
            "webhook_secret": "whsec_12345",
        },
    )
    assert create_resp.status_code == 201
    prov = create_resp.json()["data"]
    assert prov["has_ari_password"] is True
    assert prov["has_webhook_secret"] is True
    assert "super-secret-ari-password" not in json.dumps(prov)
    assert "whsec_12345" not in json.dumps(prov)

    # GET never exposes raw secrets
    list_resp = client.get("/api/v1/telephony/providers")
    assert list_resp.status_code == 200
    assert "super-secret-ari-password" not in list_resp.text
    assert "whsec_12345" not in list_resp.text

    # Trunk + Inbound/Outbound routes CRUD
    trunk_resp = client.post(
        "/api/v1/telephony/trunks",
        json={
            "name": "Primary India SIP",
            "provider_id": prov["id"],
            "host": "sip.carrier.local",
            "caller_id": "+911140001234",
            "password": "sip-secret-password",
        },
    )
    assert trunk_resp.status_code == 201
    assert "sip-secret-password" not in trunk_resp.text

    in_resp = client.post(
        "/api/v1/telephony/inbound-routes",
        json={
            "name": "Support DID",
            "phone_number": "+911140001234",
            "agent_id": "agent_demo",
        },
    )
    assert in_resp.status_code == 201

    out_resp = client.post(
        "/api/v1/telephony/outbound-routes",
        json={
            "name": "India Outbound",
            "provider_id": prov["id"],
            "caller_id": "+911140001234",
            "destination_pattern": "+91*",
        },
    )
    assert out_resp.status_code == 201

    ov = client.get("/api/v1/telephony/overview").json()["data"]
    assert ov["real_telephony_ready"] is False
    assert ov["inbound_routes"] == 1
    assert ov["outbound_routes"] == 1


def test_asterisk_ari_adapter_mocked_connection_auth_and_calls() -> None:
    cfg = TelephonyProviderPublic(
        id="tprov_1",
        name="Asterisk Mock",
        provider_type=TelephonyProviderType.ASTERISK,
        host="127.0.0.1",
        port=8088,
        use_tls=False,
        ari_username="agentvoice",
        caller_id="+911140001234",
    )

    def _ok_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/asterisk/info"):
            return httpx.Response(200, json={"system": {"version": "20.7.0"}})
        if request.method == "POST" and request.url.path.endswith("/channels"):
            return httpx.Response(200, json={"id": "ast_chan_1"})
        if request.method in ("POST", "DELETE"):
            return httpx.Response(204)
        return httpx.Response(404)

    async def _run() -> None:
        ok_provider = AsteriskARIProvider(
            cfg,
            ari_password="secret",
            transport=httpx.MockTransport(_ok_handler),
        )
        conn = await ok_provider.check_connection()
        assert conn["connected"] is True
        assert conn["status"] == ProviderConnectionStatus.CONNECTED.value
        assert conn["asterisk_version"] == "20.7.0"

        res = await ok_provider.initiate_call(
            to_number="+919876543210",
            agent_id="agent_1",
            campaign_id="camp_1",
            idempotency_key="idem_1",
        )
        assert res.provider_call_id == "ast_chan_1"
        assert await ok_provider.hold_call("ast_chan_1") is True
        assert await ok_provider.resume_call("ast_chan_1") is True
        assert await ok_provider.transfer_call("ast_chan_1", destination="PJSIP/1002") is True
        assert await ok_provider.send_dtmf("ast_chan_1", digits="1") is True
        assert await ok_provider.terminate_call("ast_chan_1") is True

        # Auth failure check
        auth_fail_provider = AsteriskARIProvider(
            cfg,
            ari_password="wrong",
            transport=httpx.MockTransport(lambda req: httpx.Response(401)),
        )
        fail_res = await auth_fail_provider.check_connection()
        assert fail_res["connected"] is False
        assert fail_res["status"] == ProviderConnectionStatus.AUTH_FAILED.value

    asyncio.run(_run())


def test_gsm_gateway_mocked_and_unreachable_states() -> None:
    gw = GsmGatewayPublic(
        id="gsmgw_1",
        name="Office GSM",
        vendor="Yeastar-Compatible",
        mode="vendor_api",
        host="10.0.0.20",
        port=80,
        api_base_url="http://10.0.0.20/api",
        max_channels=4,
    )

    async def _run() -> None:
        ok_gw = GsmGatewayProvider(
            gw,
            api_token="tok",
            transport=httpx.MockTransport(
                lambda req: httpx.Response(200, json={"active_channels": 1, "signal_strength": 24})
            ),
        )
        res = await ok_gw.check_connection()
        assert res["connected"] is True
        assert res["hardware_verified"] is True
        assert res["active_channels"] == 1

        down_gw = GsmGatewayProvider(
            gw,
            api_token="tok",
            transport=httpx.MockTransport(lambda req: (_ for _ in ()).throw(httpx.ConnectError("down"))),
        )
        down_res = await down_gw.check_connection()
        assert down_res["connected"] is False
        assert down_res["hardware_verified"] is False
        assert down_res["status"] == ProviderConnectionStatus.NETWORK_ERROR.value

    asyncio.run(_run())


def test_media_codec_negotiation_g711_and_jitter_buffer() -> None:
    codec = TelephonyMediaAdapter.negotiate_codec(["PCMA", "PCMU"], ["OPUS", "PCMU"])
    assert codec == "PCMU"

    try:
        TelephonyMediaAdapter.negotiate_codec(["G729"], ["OPUS"])
        assert False, "Expected TelephonyMediaError"
    except TelephonyMediaError:
        pass

    # Roundtrip PCM16 16k -> PCMU 8k -> PCM16 16k
    pcm16 = b"\x00\x10\x00\x20\x00\xf0\x00\xe0" * 40
    enc = TelephonyMediaAdapter.encode_from_pcm16(pcm16, "PCMU", src_rate=16000, dst_rate=8000)
    assert enc.codec == "PCMU"
    assert len(enc.audio_bytes) == 80
    dec = TelephonyMediaAdapter.decode_to_pcm16_16k(enc.audio_bytes, "PCMU", src_rate=8000)
    assert dec.sample_rate == 16000
    assert len(dec.audio_bytes) == len(pcm16)

    # Jitter buffer concealment on empty pop
    buf = AudioFrameBuffer(max_frames=2, frame_bytes=320)
    silence = buf.pop_or_conceal()
    assert len(silence) == 320
    assert buf.concealed_packets == 1


def test_inbound_routing_outbound_gates_dtmf_and_webhook_signature(tmp_path: Path) -> None:
    storage = JSONStorageProvider(tmp_path)
    storage.ensure_initialized()
    repo = TelephonyRepository(storage, "master-key")
    call_svc = CallSessionService(
        session_repo=CallSessionRepository(storage),
        event_repo=CallEventRepository(storage),
        transcript_repo=TranscriptRepository(storage),
        metrics_repo=CallMetricsRepository(storage),
    )
    agent_svc = AgentService(AgentRepository(storage))
    mgmt = TelephonyManagementService(repo, call_svc=call_svc)
    router = TelephonyCallRouter(repo, mgmt, call_svc, agent_svc)

    # Create provider and mark it CONNECTED in test storage
    prov = mgmt.create_provider(
        TelephonyProviderCreate(
            name="Test Asterisk",
            provider_type=TelephonyProviderType.ASTERISK,
            host="127.0.0.1",
            port=8088,
            use_tls=False,
            ari_username="ari",
            ari_password="pw",
            caller_id="+911140001234",
            allowed_destinations=["+91*"],
            webhook_secret="wh_secret_abc",
        )
    )
    repo.providers.update(prov.model_copy(update={"status": ProviderConnectionStatus.CONNECTED}))

    # Webhook signature validation
    body = b'{"type":"StasisStart"}'
    sig = hmac.new(b"wh_secret_abc", body, hashlib.sha256).hexdigest()
    assert TelephonyCallRouter.verify_webhook_signature(body, f"sha256={sig}", "wh_secret_abc") is True
    assert TelephonyCallRouter.verify_webhook_signature(body, "bad", "wh_secret_abc") is False

    async def _run() -> None:
        # Inbound route fails closed when no route matches
        try:
            await router.resolve_inbound_route("+919999999999")
            assert False, "Expected TelephonyPolicyError"
        except TelephonyPolicyError:
            pass

        # Outbound blocked if destination violates allowed_destinations
        try:
            await router.initiate_authorized_outbound_call(
                provider_id=prov.id,
                to_number="+14155551234",
                agent_id="agent_1",
                campaign_id="camp_1",
                idempotency_key="k1",
            )
            assert False, "Expected TelephonyPolicyError for disallowed destination"
        except TelephonyPolicyError:
            pass

        # Outbound blocked if caller_id mismatches provider caller_id
        try:
            await router.initiate_authorized_outbound_call(
                provider_id=prov.id,
                to_number="+919876543210",
                agent_id="agent_1",
                campaign_id="camp_1",
                caller_id="+919999999999",
                idempotency_key="k2",
            )
            assert False, "Expected TelephonyPolicyError for unauthorized caller_id"
        except TelephonyPolicyError:
            pass

        # DTMF structured action
        session = await call_svc.create_session(
            agent_id="agent_1",
            session_type=CallSessionType.TELEPHONY,
            direction=CallDirection.INBOUND,
            provider="asterisk",
        )
        from app.schemas.telephony import DtmfActionRequest

        dtmf_res = await router.handle_dtmf(
            DtmfActionRequest(call_id=session.id, digit="9", action_type="OPT_OUT")
        )
        assert dtmf_res["accepted"] is True

    asyncio.run(_run())
