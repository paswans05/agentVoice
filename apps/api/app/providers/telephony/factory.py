"""Factory for resolving TelephonyProvider instances."""

from __future__ import annotations

from app.providers.telephony.base import TelephonyProvider, TelephonyUnavailableError
from app.providers.telephony.dry_run import DryRunTelephonyProvider


class TelephonyProviderFactory:
    """Resolves telephony providers; real SIP/Asterisk requires Phase 9 configuration."""

    @staticmethod
    def create(provider_id: str = "dry_run") -> TelephonyProvider:
        normalized = provider_id.strip().lower()
        if normalized == "dry_run":
            return DryRunTelephonyProvider()
        if normalized in ("sip", "asterisk", "livekit_sip", "gsm_gateway"):
            raise TelephonyUnavailableError(
                f"Telephony provider '{provider_id}' is not configured yet. "
                "Real outbound calling requires an authorized Phase 9 telephony setup; "
                "use 'dry_run' mode for local workflow testing."
            )
        raise TelephonyUnavailableError(f"Unsupported telephony provider: '{provider_id}'.")
