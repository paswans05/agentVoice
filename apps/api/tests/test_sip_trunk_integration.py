"""Tests for provider-neutral SIP trunk integration, auth modes, rotation, and guards."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from app.providers.storage import JSONStorageProvider
from app.providers.telephony.asterisk_ari import AsteriskARIProvider
from app.providers.telephony.base import (
    TelephonyAuthError,
    TelephonyMediaError,
    TelephonyProviderError,
)
from app.providers.telephony.media import TelephonyMediaAdapter
from app.repositories.agent_repository import AgentRepository
from app.repositories.call_session_repository import (
    CallEventRepository,
    CallMetricsRepository,
    CallSessionRepository,
    TranscriptRepository,
)
from app.repositories.telephony_repository import TelephonyRepository
from app.schemas.agent import AgentCreate
from app.schemas.telephony import (
    CredentialRotateRequest,
    InboundRouteCreate,
    ProviderConnectionStatus,
    SipAuthMode,
    SipTrunkCreate,
    TelephonyProviderCreate,
    TelephonyProviderType,
    TransportProtocol,
)
from app.services.agent_service import AgentService
from app.services.ai_call_bridge import AICallBridgeManager
from app.services.live_calls_service import CallSessionService
from app.services.telephony_service import (
    TelephonyCallRouter,
    TelephonyManagementService,
    TelephonyPolicyError,
)


def _build_services(tmp_path: Path):
    storage = JSONStorageProvider(tmp_path)
    repo = TelephonyRepository(storage, master_key="test-secret-key-for-sip-audit")
    call_svc = CallSessionService(
        CallSessionRepository(storage),
        CallEventRepository(storage),
        TranscriptRepository(storage),
        CallMetricsRepository(storage),
    )
    mgmt = TelephonyManagementService(repo, call_svc=call_svc)
    agent_svc = AgentService(AgentRepository(storage))
    router = TelephonyCallRouter(repo, mgmt, call_svc, agent_svc)
    return storage, repo, mgmt, call_svc, agent_svc, router


@pytest.mark.asyncio
async def test_provider_auth_modes_encryption_and_credential_rotation(tmp_path: Path):
    _, repo, mgmt, _, _, _ = _build_services(tmp_path)
    prov = mgmt.create_provider(
        TelephonyProviderCreate(
            name="Exotel vSIP",
            provider_type=TelephonyProviderType.SIP_TRUNK,
            host="pstn.in2.exotel.com",
            port=5070,
            use_tls=False,
            transport=TransportProtocol.TCP,
            auth_mode=SipAuthMode.IP_WHITELIST,
            ari_username="agentvoice",
            ari_password="initial-ari-password",
            caller_id="+911140001234",
            allowed_destinations=["+91*"],
        )
    )
    assert prov.auth_mode == SipAuthMode.IP_WHITELIST
    assert prov.has_ari_password is True
    assert prov.credential_rotated_at is None
    assert repo.vault.get_secret(f"provider:{prov.id}:ari_password") == "initial-ari-password"

    rotated = mgmt.rotate_provider_credentials(
        prov.id,
        CredentialRotateRequest(ari_password="rotated-ari-password"),
    )
    assert rotated.credential_rotated_at is not None
    assert repo.vault.get_secret(f"provider:{prov.id}:ari_password") == "rotated-ari-password"
    assert "rotated-ari-password" not in rotated.model_dump_json()

    disabled = mgmt.set_provider_enabled(prov.id, False)
    assert disabled.enabled is False


@pytest.mark.asyncio
async def test_asterisk_ari_trunk_endpoint_check_and_error_handling(tmp_path: Path):
    _, _, mgmt, _, _, _ = _build_services(tmp_path)
    prov = mgmt.create_provider(
        TelephonyProviderCreate(
            name="Local Asterisk",
            provider_type=TelephonyProviderType.ASTERISK,
            host="asterisk",
            port=8088,
            use_tls=False,
            ari_username="agentvoice",
            ari_password="secret",
            caller_id="+911140001234",
        )
    )

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ari/endpoints/PJSIP/sip-trunk-external":
            return httpx.Response(200, json={"state": "online", "channel_ids": []})
        if request.url.path == "/ari/endpoints/PJSIP/missing-trunk":
            return httpx.Response(404, json={"message": "Not found"})
        if request.url.path == "/ari/channels" and request.method == "POST":
            body = request.read().decode("utf-8")
            assert "PJSIP/+919876543210@sip-trunk-external" in body
            return httpx.Response(503, json={"message": "Service Unavailable"})
        return httpx.Response(401, json={"message": "Unauthorized"})

    adapter = AsteriskARIProvider(
        prov,
        ari_password="secret",
        transport=httpx.MockTransport(_handler),
    )

    ok_res = await adapter.check_trunk_endpoint("sip-trunk-external")
    assert ok_res["reachable"] is True
    assert ok_res["options_status"] == "REACHABLE"

    missing_res = await adapter.check_trunk_endpoint("missing-trunk")
    assert missing_res["reachable"] is False
    assert missing_res["options_status"] == "NOT_CONFIGURED"

    with pytest.raises(TelephonyProviderError):
        await adapter.initiate_call(
            to_number="+919876543210",
            agent_id="agt_1",
            campaign_id="cmp_1",
            idempotency_key="idem_1",
            metadata={"trunk_name": "sip-trunk-external"},
        )

    bad_auth_adapter = AsteriskARIProvider(
        prov,
        ari_password="wrong",
        transport=httpx.MockTransport(lambda _: httpx.Response(401)),
    )
    auth_res = await bad_auth_adapter.check_trunk_endpoint("sip-trunk-external")
    assert auth_res["options_status"] == "AUTH_FAILED"

    with pytest.raises(TelephonyAuthError):
        await bad_auth_adapter.initiate_call(
            to_number="+919876543210",
            agent_id="agt_1",
            campaign_id="cmp_1",
            idempotency_key="idem_2",
        )


@pytest.mark.asyncio
async def test_outbound_guards_duplicate_protection_and_inbound_hours(tmp_path: Path):
    _, repo, mgmt, _, agent_svc, router = _build_services(tmp_path)
    prov = mgmt.create_provider(
        TelephonyProviderCreate(
            name="Mock Connected Asterisk",
            provider_type=TelephonyProviderType.ASTERISK,
            host="asterisk",
            port=8088,
            use_tls=False,
            ari_username="agentvoice",
            ari_password="secret",
            caller_id="+911140001234",
            allowed_destinations=["+91*"],
        )
    )
    repo.providers.update(prov.model_copy(update={"status": ProviderConnectionStatus.CONNECTED}))

    # Create preferred trunk
    mgmt.create_trunk(
        SipTrunkCreate(
            name="sip-trunk-external",
            provider_id=prov.id,
            host="pstn.in2.exotel.com",
            port=5070,
            transport=TransportProtocol.TCP,
            auth_mode=SipAuthMode.IP_WHITELIST,
            caller_id="+911140001234",
            preferred=True,
        )
    )

    # Caller ID mismatch blocked
    with pytest.raises(TelephonyPolicyError, match="not authorized"):
        await router.initiate_authorized_outbound_call(
            provider_id=prov.id,
            to_number="+919876543210",
            agent_id="agt_1",
            campaign_id="cmp_1",
            caller_id="+919999999999",
            idempotency_key="k1",
        )

    # Open SIP relay blocked
    with pytest.raises(TelephonyPolicyError, match="open relay"):
        await router.initiate_authorized_outbound_call(
            provider_id=prov.id,
            to_number="sip:attacker@evil.example",
            agent_id="agt_1",
            campaign_id="cmp_1",
            idempotency_key="k2",
        )

    # Destination pattern blocked
    with pytest.raises(TelephonyPolicyError, match="allowed_destinations"):
        await router.initiate_authorized_outbound_call(
            provider_id=prov.id,
            to_number="+14155550199",
            agent_id="agt_1",
            campaign_id="cmp_1",
            idempotency_key="k3",
        )

    # Mock AsteriskARIProvider.initiate_call via monkeypatch on _build_provider_adapter
    class _FakeAdapter:
        async def initiate_call(self, **kwargs: Any):
            assert kwargs.get("metadata", {}).get("trunk_name") == "sip-trunk-external"
            from app.providers.telephony.base import CallInitiationResult

            return CallInitiationResult(
                provider_call_id="ast_mock_1",
                status="INITIATING",
                is_dry_run=False,
            )

    mgmt._build_provider_adapter = lambda _rec: _FakeAdapter()  # type: ignore[method-assign]

    sess = await router.initiate_authorized_outbound_call(
        provider_id=prov.id,
        to_number="+919876543210",
        agent_id="agt_1",
        campaign_id="cmp_1",
        lead_id="lead_1",
        idempotency_key="k4",
    )
    assert sess.external_call_id == "ast_mock_1"

    # Duplicate active call for same lead & campaign blocked
    with pytest.raises(TelephonyPolicyError, match="Duplicate active call"):
        await router.initiate_authorized_outbound_call(
            provider_id=prov.id,
            to_number="+919876543210",
            agent_id="agt_1",
            campaign_id="cmp_1",
            lead_id="lead_1",
            idempotency_key="k5",
        )

    # Inbound route matching requires ACTIVE agent
    agent = await agent_svc.create_agent(AgentCreate(name="InboundBot"))
    mgmt.create_inbound_route(
        InboundRouteCreate(
            name="Exophone Inbound",
            phone_number="+911140001234",
            agent_id=agent.id,
        )
    )
    with pytest.raises(TelephonyPolicyError, match="not ACTIVE"):
        await router.resolve_inbound_route("+911140001234")


@pytest.mark.asyncio
async def test_media_codec_error_and_ai_bridge_cleanup():
    with pytest.raises(TelephonyMediaError):
        TelephonyMediaAdapter.negotiate_codec(["G729"], ["PCMU", "PCMA"])

    bridge = AICallBridgeManager()
    session = await bridge.attach_call(call_id="c_sip_1", channel_id="ch_sip_1", agent_id="agt_1")
    assert session.active is True
    assert await bridge.detach_call("c_sip_1") is True
    assert session.active is False
