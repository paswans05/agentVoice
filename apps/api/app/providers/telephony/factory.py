"""Factory for resolving TelephonyProvider instances."""

from __future__ import annotations

from app.providers.telephony.asterisk_ari import AsteriskARIProvider
from app.providers.telephony.base import TelephonyProvider, TelephonyUnavailableError
from app.providers.telephony.dry_run import DryRunTelephonyProvider
from app.providers.telephony.gsm_gateway import GsmGatewayProvider
from app.schemas.telephony import GsmGatewayPublic, TelephonyProviderPublic, TelephonyProviderType


class TelephonyProviderFactory:
    """Resolves dry-run or configured authorized telephony providers."""

    @staticmethod
    def create(
        provider_id: str = "dry_run",
        *,
        provider_config: TelephonyProviderPublic | None = None,
        gateway_config: GsmGatewayPublic | None = None,
        secret: str | None = None,
    ) -> TelephonyProvider:
        normalized = provider_id.strip().lower()
        if normalized == "dry_run":
            return DryRunTelephonyProvider()
        if provider_config is not None:
            if provider_config.provider_type in (
                TelephonyProviderType.ASTERISK,
                TelephonyProviderType.SIP_TRUNK,
            ):
                return AsteriskARIProvider(provider_config, ari_password=secret)
        if gateway_config is not None:
            return GsmGatewayProvider(gateway_config, api_token=secret)
        if normalized in ("sip", "sip_trunk", "asterisk", "livekit_sip", "gsm_gateway"):
            raise TelephonyUnavailableError(
                f"Telephony provider '{provider_id}' is not configured yet. "
                "Real outbound calling requires an authorized Phase 10 telephony configuration; "
                "use 'dry_run' mode for local workflow testing."
            )
        raise TelephonyUnavailableError(f"Unsupported telephony provider: '{provider_id}'.")
