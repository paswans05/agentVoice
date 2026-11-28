"""Telephony management, SIP routing, inbound/outbound gating, DTMF, and webhook security."""

from __future__ import annotations

from datetime import datetime, timezone
import fnmatch
import hashlib
import hmac
import logging
from typing import Any
import uuid
from zoneinfo import ZoneInfo

from app.providers.telephony.base import TelephonyProvider, TelephonyUnavailableError
from app.providers.telephony.factory import TelephonyProviderFactory
from app.repositories.telephony_repository import TelephonyRepository
from app.schemas.agent import AgentStatus
from app.schemas.leads import ConsentChannel
from app.schemas.live_calls import (
    CallDirection,
    CallEventType,
    CallSession,
    CallSessionStatus,
    CallSessionType,
)
from app.schemas.telephony import (
    DtmfActionRequest,
    GsmGatewayCreate,
    GsmGatewayPublic,
    InboundRoute,
    InboundRouteCreate,
    InboundRouteUpdate,
    OutboundRoute,
    OutboundRouteCreate,
    OutboundRouteUpdate,
    ProviderCapabilitiesSchema,
    ProviderConnectionStatus,
    SipTrunkCreate,
    SipTrunkPublic,
    SipTrunkUpdate,
    TelephonyOverview,
    TelephonyProviderCreate,
    TelephonyProviderPublic,
    TelephonyProviderType,
    TelephonyProviderUpdate,
    TelephonySettings,
)
from app.services.agent_service import AgentService
from app.services.live_calls_service import ACTIVE_STATUSES, CallSessionService
from app.services.suppression_service import LeadEligibilityService

logger = logging.getLogger(__name__)


class TelephonyNotFoundError(LookupError):
    """Raised when a telephony provider, trunk, route, or gateway is not found."""


class TelephonyPolicyError(ValueError):
    """Raised when a telephony security, compliance, or routing policy blocks an action."""


def _destination_matches(destination: str, patterns: list[str]) -> bool:
    if not patterns:
        return True
    cleaned = destination.strip()
    return any(fnmatch.fnmatch(cleaned, pat.strip()) for pat in patterns if pat.strip())


def _is_within_working_hours(route: InboundRoute, now_utc: datetime | None = None) -> bool:
    now = now_utc or datetime.now(timezone.utc)
    try:
        local_dt = now.astimezone(ZoneInfo(route.working_hours_timezone))
    except Exception:
        local_dt = now
    hhmm = local_dt.strftime("%H:%M")
    if route.working_hours_start <= route.working_hours_end:
        return route.working_hours_start <= hhmm <= route.working_hours_end
    return hhmm >= route.working_hours_start or hhmm <= route.working_hours_end


class TelephonyManagementService:
    """Manages providers, SIP trunks, routes, GSM gateways, and connection verification."""

    def __init__(self, repo: TelephonyRepository, call_svc: CallSessionService | None = None) -> None:
        self._repo = repo
        self._calls = call_svc

    def _build_provider_adapter(self, rec: TelephonyProviderPublic) -> TelephonyProvider:
        secret = self._repo.vault.get_secret(f"provider:{rec.id}:ari_password") or self._repo.vault.get_secret(
            f"provider:{rec.id}:password"
        )
        return TelephonyProviderFactory.create(
            rec.provider_type.value,
            provider_config=rec,
            secret=secret,
        )

    def list_providers(self) -> list[TelephonyProviderPublic]:
        return self._repo.providers.list_all()

    def get_provider(self, provider_id: str) -> TelephonyProviderPublic:
        rec = self._repo.providers.get(provider_id)
        if rec is None:
            raise TelephonyNotFoundError(f"Telephony provider '{provider_id}' not found.")
        return rec

    def create_provider(self, payload: TelephonyProviderCreate) -> TelephonyProviderPublic:
        pid = f"tprov_{uuid.uuid4().hex[:10]}"
        if payload.password:
            self._repo.vault.set_secret(f"provider:{pid}:password", payload.password)
        if payload.ari_password:
            self._repo.vault.set_secret(f"provider:{pid}:ari_password", payload.ari_password)
        if payload.webhook_secret:
            self._repo.vault.set_secret(f"provider:{pid}:webhook_secret", payload.webhook_secret)

        has_pw = bool(payload.password)
        has_ari = bool(payload.ari_password)
        configured = bool(payload.host or payload.ari_base_url) and (has_ari or has_pw)
        caps = ProviderCapabilitiesSchema(
            inbound=True,
            outbound=True,
            hold=payload.provider_type == TelephonyProviderType.ASTERISK,
            transfer=payload.provider_type == TelephonyProviderType.ASTERISK,
            recording=False,
            dtmf=True,
            supported_codecs=payload.supported_codecs,
            max_concurrent_calls=payload.max_concurrent_calls,
        )
        rec = TelephonyProviderPublic(
            id=pid,
            name=payload.name,
            provider_type=payload.provider_type,
            supports_real_calls=payload.provider_type != TelephonyProviderType.DRY_RUN,
            configured=configured,
            status=(
                ProviderConnectionStatus.DISCONNECTED
                if configured
                else ProviderConnectionStatus.INCOMPLETE
            ),
            message="Saved. Run connection test to verify connectivity." if configured else "Configuration incomplete.",
            host=payload.host,
            port=payload.port,
            use_tls=payload.use_tls,
            transport=payload.transport,
            username=payload.username,
            auth_username=payload.auth_username,
            sip_domain=payload.sip_domain,
            outbound_proxy=payload.outbound_proxy,
            ari_base_url=payload.ari_base_url,
            ari_app=payload.ari_app,
            ari_username=payload.ari_username,
            caller_id=payload.caller_id,
            allowed_destinations=payload.allowed_destinations,
            connection_timeout_seconds=payload.connection_timeout_seconds,
            max_concurrent_calls=payload.max_concurrent_calls,
            supported_codecs=payload.supported_codecs,
            enabled=payload.enabled,
            has_password=has_pw,
            has_ari_password=has_ari,
            has_webhook_secret=bool(payload.webhook_secret),
            capabilities=caps,
        )
        return self._repo.providers.create(rec)

    def update_provider(self, provider_id: str, payload: TelephonyProviderUpdate) -> TelephonyProviderPublic:
        existing = self.get_provider(provider_id)
        if payload.password:
            self._repo.vault.set_secret(f"provider:{provider_id}:password", payload.password)
        if payload.ari_password:
            self._repo.vault.set_secret(f"provider:{provider_id}:ari_password", payload.ari_password)
        if payload.webhook_secret:
            self._repo.vault.set_secret(f"provider:{provider_id}:webhook_secret", payload.webhook_secret)

        updates = payload.model_dump(
            exclude_unset=True,
            exclude={"password", "ari_password", "webhook_secret"},
        )
        updates["has_password"] = existing.has_password or bool(payload.password)
        updates["has_ari_password"] = existing.has_ari_password or bool(payload.ari_password)
        updates["has_webhook_secret"] = existing.has_webhook_secret or bool(payload.webhook_secret)
        updated = existing.model_copy(update=updates)
        return self._repo.providers.update(updated) or updated

    def delete_provider(self, provider_id: str) -> bool:
        self._repo.vault.delete_prefix(f"provider:{provider_id}:")
        return self._repo.providers.delete(provider_id)

    async def test_provider(self, provider_id: str) -> dict[str, Any]:
        rec = self.get_provider(provider_id)
        adapter = self._build_provider_adapter(rec)
        result = await adapter.check_connection()
        new_status = ProviderConnectionStatus(
            str(result.get("status") or ProviderConnectionStatus.UNAVAILABLE.value)
        )
        updated = rec.model_copy(
            update={
                "status": new_status,
                "configured": new_status != ProviderConnectionStatus.INCOMPLETE,
                "message": str(result.get("message") or ""),
                "last_checked_at": datetime.now(timezone.utc),
                "last_error": None if result.get("connected") else str(result.get("message") or ""),
            }
        )
        self._repo.providers.update(updated)
        return result

    async def connect_provider(self, provider_id: str) -> TelephonyProviderPublic:
        await self.test_provider(provider_id)
        return self.get_provider(provider_id)

    async def disconnect_provider(self, provider_id: str) -> TelephonyProviderPublic:
        rec = self.get_provider(provider_id)
        adapter = self._build_provider_adapter(rec)
        await adapter.disconnect()
        updated = rec.model_copy(
            update={
                "status": ProviderConnectionStatus.DISCONNECTED,
                "message": "Disconnected by operator.",
                "last_checked_at": datetime.now(timezone.utc),
            }
        )
        return self._repo.providers.update(updated) or updated

    # --- SIP Trunks ---

    def list_trunks(self) -> list[SipTrunkPublic]:
        return self._repo.trunks.list_all()

    def create_trunk(self, payload: SipTrunkCreate) -> SipTrunkPublic:
        self.get_provider(payload.provider_id)
        tid = f"trunk_{uuid.uuid4().hex[:10]}"
        if payload.password:
            self._repo.vault.set_secret(f"trunk:{tid}:password", payload.password)
        trunk = SipTrunkPublic(
            id=tid,
            name=payload.name,
            provider_id=payload.provider_id,
            host=payload.host,
            port=payload.port,
            transport=payload.transport,
            username=payload.username,
            auth_username=payload.auth_username,
            sip_domain=payload.sip_domain,
            outbound_proxy=payload.outbound_proxy,
            caller_id=payload.caller_id,
            register_required=payload.register_required,
            allowed_destinations=payload.allowed_destinations,
            codecs=payload.codecs,
            max_concurrent_calls=payload.max_concurrent_calls,
            preferred=payload.preferred,
            enabled=payload.enabled,
            has_password=bool(payload.password),
        )
        return self._repo.trunks.create(trunk)

    def update_trunk(self, trunk_id: str, payload: SipTrunkUpdate) -> SipTrunkPublic:
        existing = self._repo.trunks.get(trunk_id)
        if existing is None:
            raise TelephonyNotFoundError(f"SIP trunk '{trunk_id}' not found.")
        if payload.password:
            self._repo.vault.set_secret(f"trunk:{trunk_id}:password", payload.password)
        updates = payload.model_dump(exclude_unset=True, exclude={"password"})
        updates["has_password"] = existing.has_password or bool(payload.password)
        updated = existing.model_copy(update=updates)
        return self._repo.trunks.update(updated) or updated

    def delete_trunk(self, trunk_id: str) -> bool:
        self._repo.vault.delete_prefix(f"trunk:{trunk_id}:")
        return self._repo.trunks.delete(trunk_id)

    async def test_trunk(self, trunk_id: str) -> dict[str, Any]:
        trunk = self._repo.trunks.get(trunk_id)
        if trunk is None:
            raise TelephonyNotFoundError(f"SIP trunk '{trunk_id}' not found.")
        prov_res = await self.test_provider(trunk.provider_id)
        new_status = (
            ProviderConnectionStatus.CONNECTED
            if prov_res.get("connected")
            else ProviderConnectionStatus(
                str(prov_res.get("status") or ProviderConnectionStatus.UNAVAILABLE.value)
            )
        )
        self._repo.trunks.update(
            trunk.model_copy(
                update={
                    "status": new_status,
                    "last_error": None if prov_res.get("connected") else prov_res.get("message"),
                }
            )
        )
        return {
            "trunk_id": trunk_id,
            "connected": bool(prov_res.get("connected")),
            "status": new_status.value,
            "message": prov_res.get("message"),
        }

    # --- Inbound / Outbound Routes ---

    def list_inbound_routes(self) -> list[InboundRoute]:
        return self._repo.inbound_routes.list_all()

    def create_inbound_route(self, payload: InboundRouteCreate) -> InboundRoute:
        route = InboundRoute(id=f"inrt_{uuid.uuid4().hex[:10]}", **payload.model_dump())
        return self._repo.inbound_routes.create(route)

    def update_inbound_route(self, route_id: str, payload: InboundRouteUpdate) -> InboundRoute:
        existing = self._repo.inbound_routes.get(route_id)
        if existing is None:
            raise TelephonyNotFoundError(f"Inbound route '{route_id}' not found.")
        updated = existing.model_copy(update=payload.model_dump(exclude_unset=True))
        return self._repo.inbound_routes.update(updated) or updated

    def delete_inbound_route(self, route_id: str) -> bool:
        return self._repo.inbound_routes.delete(route_id)

    def list_outbound_routes(self) -> list[OutboundRoute]:
        routes = self._repo.outbound_routes.list_all()
        routes.sort(key=lambda r: r.priority)
        return routes

    def create_outbound_route(self, payload: OutboundRouteCreate) -> OutboundRoute:
        self.get_provider(payload.provider_id)
        route = OutboundRoute(id=f"outrt_{uuid.uuid4().hex[:10]}", **payload.model_dump())
        return self._repo.outbound_routes.create(route)

    def update_outbound_route(self, route_id: str, payload: OutboundRouteUpdate) -> OutboundRoute:
        existing = self._repo.outbound_routes.get(route_id)
        if existing is None:
            raise TelephonyNotFoundError(f"Outbound route '{route_id}' not found.")
        updated = existing.model_copy(update=payload.model_dump(exclude_unset=True))
        return self._repo.outbound_routes.update(updated) or updated

    def delete_outbound_route(self, route_id: str) -> bool:
        return self._repo.outbound_routes.delete(route_id)

    # --- GSM Gateways ---

    def list_gateways(self) -> list[GsmGatewayPublic]:
        return self._repo.gateways.list_all()

    def get_gateway(self, gateway_id: str) -> GsmGatewayPublic:
        gw = self._repo.gateways.get(gateway_id)
        if gw is None:
            raise TelephonyNotFoundError(f"GSM gateway '{gateway_id}' not found.")
        return gw

    def create_gateway(self, payload: GsmGatewayCreate) -> GsmGatewayPublic:
        gid = f"gsmgw_{uuid.uuid4().hex[:10]}"
        if payload.api_token:
            self._repo.vault.set_secret(f"gateway:{gid}:api_token", payload.api_token)
        gw = GsmGatewayPublic(
            id=gid,
            name=payload.name,
            vendor=payload.vendor,
            mode=payload.mode,
            host=payload.host,
            port=payload.port,
            api_base_url=payload.api_base_url,
            username=payload.username,
            max_channels=payload.max_channels,
            has_api_token=bool(payload.api_token),
            enabled=payload.enabled,
            hardware_verified=False,
        )
        return self._repo.gateways.create(gw)

    def delete_gateway(self, gateway_id: str) -> bool:
        self._repo.vault.delete_prefix(f"gateway:{gateway_id}:")
        return self._repo.gateways.delete(gateway_id)

    async def test_gateway(self, gateway_id: str) -> dict[str, Any]:
        gw = self.get_gateway(gateway_id)
        token = self._repo.vault.get_secret(f"gateway:{gateway_id}:api_token")
        adapter = TelephonyProviderFactory.create(
            "gsm_gateway",
            gateway_config=gw,
            secret=token,
        )
        res = await adapter.check_connection()
        new_status = ProviderConnectionStatus(
            str(res.get("status") or ProviderConnectionStatus.UNAVAILABLE.value)
        )
        self._repo.gateways.update(
            gw.model_copy(
                update={
                    "status": new_status,
                    "hardware_verified": bool(res.get("hardware_verified", False)),
                    "active_channels": int(res.get("active_channels", 0)),
                    "signal_strength": res.get("signal_strength"),
                    "last_error": None if res.get("connected") else res.get("message"),
                }
            )
        )
        return res

    # --- Settings & Overview ---

    def get_settings(self) -> TelephonySettings:
        return self._repo.get_settings()

    def update_settings(self, settings: TelephonySettings) -> TelephonySettings:
        return self._repo.update_settings(settings)

    async def get_overview(self) -> TelephonyOverview:
        providers = self.list_providers()
        trunks = self.list_trunks()
        in_routes = self.list_inbound_routes()
        out_routes = self.list_outbound_routes()
        gateways = self.list_gateways()

        connected = [p for p in providers if p.status == ProviderConnectionStatus.CONNECTED]
        reg_trunks = [t for t in trunks if t.status == ProviderConnectionStatus.CONNECTED]
        active_gws = [g for g in gateways if g.status == ProviderConnectionStatus.CONNECTED]
        errors = [p.last_error for p in providers if p.last_error] + [
            g.last_error for g in gateways if g.last_error
        ]

        active_calls = 0
        failed_calls = 0
        if self._calls is not None:
            all_calls = await self._calls.list_sessions(active_only=False)
            tel_calls = [c for c in all_calls if c.session_type == CallSessionType.TELEPHONY]
            active_calls = sum(1 for c in tel_calls if c.status in ACTIVE_STATUSES)
            failed_calls = sum(1 for c in tel_calls if c.status == CallSessionStatus.FAILED)

        total_channels = sum(p.max_concurrent_calls for p in connected) + sum(
            g.max_channels for g in active_gws
        )
        return TelephonyOverview(
            connected_providers=len(connected),
            total_providers=len(providers),
            registered_trunks=len(reg_trunks),
            total_trunks=len(trunks),
            inbound_routes=len([r for r in in_routes if r.enabled]),
            outbound_routes=len([r for r in out_routes if r.enabled]),
            active_gateways=len(active_gws),
            total_gateways=len(gateways),
            active_telephony_calls=active_calls,
            failed_telephony_calls=failed_calls,
            available_channels=max(0, total_channels - active_calls),
            real_telephony_ready=len(connected) > 0,
            recent_errors=errors[:10],
        )


class TelephonyCallRouter:
    """Enforces inbound route validation, outbound compliance gates, DTMF, and webhook auth."""

    def __init__(
        self,
        repo: TelephonyRepository,
        mgmt: TelephonyManagementService,
        call_svc: CallSessionService,
        agent_svc: AgentService,
        eligibility_svc: LeadEligibilityService | None = None,
    ) -> None:
        self._repo = repo
        self._mgmt = mgmt
        self._calls = call_svc
        self._agents = agent_svc
        self._eligibility = eligibility_svc

    @staticmethod
    def verify_webhook_signature(
        payload_bytes: bytes,
        signature_header: str | None,
        secret: str | None,
    ) -> bool:
        if not secret or not signature_header:
            return False
        provided = signature_header.replace("sha256=", "").strip()
        expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(provided, expected)

    async def resolve_inbound_route(self, destination_number: str) -> tuple[InboundRoute, str]:
        routes = [r for r in self._repo.inbound_routes.list_all() if r.enabled]
        matched = next(
            (
                r
                for r in routes
                if r.phone_number == destination_number
                or r.sip_destination == destination_number
                or fnmatch.fnmatch(destination_number, r.phone_number)
            ),
            None,
        )
        if matched is None:
            raise TelephonyPolicyError(
                f"No enabled inbound route matched destination '{destination_number}'."
            )
        if not _is_within_working_hours(matched):
            raise TelephonyPolicyError(
                f"Inbound route '{matched.name}' is outside configured working hours."
            )
        agent = await self._agents.get_agent(matched.agent_id)
        if agent.status != AgentStatus.ACTIVE:
            raise TelephonyPolicyError(
                f"Assigned agent '{matched.agent_id}' is not ACTIVE for inbound calls."
            )
        return matched, agent.id

    async def handle_inbound_event(
        self,
        provider_id: str,
        raw_event: dict[str, Any],
    ) -> dict[str, Any]:
        prov = self._mgmt.get_provider(provider_id)
        adapter = self._mgmt._build_provider_adapter(prov)
        norm = await adapter.handle_provider_event(raw_event)
        ext_call_id = str(norm.get("provider_call_id") or raw_event.get("call_id") or "")
        dest = str(norm.get("destination_number") or raw_event.get("destination_number") or "")
        caller = str(norm.get("caller_number") or raw_event.get("caller_number") or "")

        # Check idempotency: reuse existing CallSession if already tracked
        existing = None
        for s in await self._calls.list_sessions(active_only=False):
            if s.external_call_id == ext_call_id and ext_call_id:
                existing = s
                break

        ev_type = norm.get("normalized_event_type") or CallEventType.CALL_STARTED
        if existing is None:
            try:
                route, agent_id = await self.resolve_inbound_route(dest)
            except TelephonyPolicyError as exc:
                if ext_call_id:
                    try:
                        await adapter.reject_call(ext_call_id, reason="route_or_agent_invalid")
                    except Exception:
                        pass
                raise exc

            session = await self._calls.create_session(
                agent_id=agent_id,
                session_type=CallSessionType.TELEPHONY,
                direction=CallDirection.INBOUND,
                provider=prov.provider_type.value,
                caller_number=caller,
                destination_number=dest,
                external_call_id=ext_call_id,
            )
            await adapter.answer_inbound_call(ext_call_id, agent_id=agent_id)
            return {
                "call_id": session.id,
                "route_id": route.id,
                "agent_id": agent_id,
                "status": "ANSWERED",
            }

        await self._calls.publish_event(
            call_id=existing.id,
            event_type=ev_type if isinstance(ev_type, CallEventType) else CallEventType.CALL_WARNING,
            source=prov.provider_type.value,
            payload=norm,
            event_id=raw_event.get("event_id"),
        )
        if ev_type in (CallEventType.CALL_ENDED, CallEventType.CALL_DISCONNECTED):
            await self._calls.end_session(existing.id, status=CallSessionStatus.COMPLETED)
        return {"call_id": existing.id, "status": existing.status.value}

    async def initiate_authorized_outbound_call(
        self,
        *,
        provider_id: str,
        to_number: str,
        agent_id: str,
        campaign_id: str,
        lead_id: str | None = None,
        caller_id: str | None = None,
        calling_purpose: str = "SALES_CALLS",
        idempotency_key: str,
    ) -> CallSession:
        settings = self._repo.get_settings()
        prov = self._mgmt.get_provider(provider_id)
        if not prov.enabled or prov.status != ProviderConnectionStatus.CONNECTED:
            raise TelephonyPolicyError(
                f"Provider '{prov.name}' is not connected/authorized for outbound calls."
            )

        # 1. Caller ID authorization
        effective_caller_id = caller_id or prov.caller_id
        if settings.require_caller_id_authorization and not effective_caller_id:
            raise TelephonyPolicyError("Authorized caller_id is required for outbound calls.")
        if prov.caller_id and effective_caller_id != prov.caller_id:
            raise TelephonyPolicyError(
                f"Caller ID '{effective_caller_id}' is not authorized for provider '{prov.name}'."
            )

        # 2. Destination restriction & anti-open-relay check
        if settings.block_open_sip_relay and ("@" in to_number and not prov.sip_domain):
            raise TelephonyPolicyError("Arbitrary external SIP URI dialing is blocked (open relay protection).")
        if not _destination_matches(to_number, prov.allowed_destinations):
            raise TelephonyPolicyError(
                f"Destination '{to_number}' is outside provider allowed_destinations policy."
            )

        # 3. Concurrency check
        active = await self._calls.list_sessions(active_only=True)
        tel_active = [c for c in active if c.session_type == CallSessionType.TELEPHONY]
        if len(tel_active) >= min(settings.max_concurrent_calls, prov.max_concurrent_calls):
            raise TelephonyPolicyError("Maximum concurrent telephony call limit reached.")

        # 4. Lead consent & suppression check (when lead_id is supplied)
        if lead_id and self._eligibility is not None:
            elig = await self._eligibility.check_contact_eligibility(
                lead_id,
                channel=ConsentChannel.PHONE,
                purpose=calling_purpose,
            )
            if not elig.eligible:
                raise TelephonyPolicyError(f"Lead '{lead_id}' blocked by eligibility gate: {elig.reason}")

        adapter = self._mgmt._build_provider_adapter(prov)
        res = await adapter.initiate_call(
            to_number=to_number,
            agent_id=agent_id,
            campaign_id=campaign_id,
            idempotency_key=idempotency_key,
        )
        session = await self._calls.create_session(
            agent_id=agent_id,
            session_type=CallSessionType.TELEPHONY,
            direction=CallDirection.OUTBOUND,
            provider=prov.provider_type.value,
            campaign_id=campaign_id,
            lead_id=lead_id,
            caller_number=effective_caller_id,
            destination_number=to_number,
            external_call_id=res.provider_call_id,
        )
        return session

    async def handle_dtmf(self, req: DtmfActionRequest) -> dict[str, Any]:
        session = await self._calls.get_session(req.call_id)
        await self._calls.publish_event(
            call_id=session.id,
            event_type=CallEventType.SPEECH_DETECTED,
            source="dtmf",
            payload={
                "digit": req.digit,
                "action_type": req.action_type,
                "target": req.target,
            },
        )
        if req.action_type == "OPT_OUT":
            await self._calls.publish_event(
                call_id=session.id,
                event_type=CallEventType.DO_NOT_CALL_REQUESTED,
                source="dtmf",
                payload={"digit": req.digit},
            )
        return {"call_id": session.id, "digit": req.digit, "action_type": req.action_type, "accepted": True}
