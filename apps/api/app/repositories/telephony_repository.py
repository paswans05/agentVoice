"""Encrypted secret vault and StorageProvider repositories for Phase 10 Telephony."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import logging
import os

from pydantic import ValidationError

from app.providers.storage import StorageProvider
from app.schemas.telephony import (
    GsmGatewayPublic,
    InboundRoute,
    OutboundRoute,
    SipTrunkPublic,
    TelephonyProviderPublic,
    TelephonySettings,
)

logger = logging.getLogger(__name__)

PROVIDERS_STORE = "telephony/providers_store.json"
TRUNKS_STORE = "telephony/trunks_store.json"
INBOUND_ROUTES_STORE = "telephony/inbound_routes_store.json"
OUTBOUND_ROUTES_STORE = "telephony/outbound_routes_store.json"
GATEWAYS_STORE = "telephony/gateways_store.json"
TELEPHONY_SETTINGS_PATH = "telephony/settings.json"
TELEPHONY_SECRETS_PATH = "telephony/secrets.json"


class TelephonySecretVault:
    """Encrypts and authenticates telephony secrets at rest using app secret key."""

    def __init__(self, storage: StorageProvider, master_key: str) -> None:
        self._storage = storage
        self._enc_key = hashlib.sha256(f"enc:{master_key}".encode("utf-8")).digest()
        self._mac_key = hashlib.sha256(f"mac:{master_key}".encode("utf-8")).digest()

    def _seal(self, plaintext: str) -> str:
        nonce = os.urandom(16)
        stream_key = hashlib.pbkdf2_hmac("sha256", self._enc_key, nonce, 10_000, dklen=len(plaintext.encode("utf-8")) or 1)
        plain_bytes = plaintext.encode("utf-8")
        cipher = bytes(b ^ k for b, k in zip(plain_bytes, stream_key))
        tag = hmac.new(self._mac_key, nonce + cipher, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(nonce + tag + cipher).decode("ascii")

    def _open(self, token: str) -> str | None:
        try:
            raw = base64.urlsafe_b64decode(token.encode("ascii"))
            if len(raw) < 48:
                return None
            nonce, tag, cipher = raw[:16], raw[16:48], raw[48:]
            expected = hmac.new(self._mac_key, nonce + cipher, hashlib.sha256).digest()
            if not hmac.compare_digest(tag, expected):
                return None
            stream_key = hashlib.pbkdf2_hmac("sha256", self._enc_key, nonce, 10_000, dklen=len(cipher) or 1)
            plain_bytes = bytes(b ^ k for b, k in zip(cipher, stream_key))
            return plain_bytes.decode("utf-8")
        except Exception:
            return None

    def set_secret(self, key: str, value: str | None) -> None:
        if value is None or value == "":
            return
        secrets = self._storage.read_json(TELEPHONY_SECRETS_PATH, default={}) or {}
        secrets[key] = self._seal(value)
        self._storage.write_json(TELEPHONY_SECRETS_PATH, secrets)

    def get_secret(self, key: str) -> str | None:
        secrets = self._storage.read_json(TELEPHONY_SECRETS_PATH, default={}) or {}
        token = secrets.get(key)
        if not isinstance(token, str):
            return None
        return self._open(token)

    def delete_prefix(self, prefix: str) -> None:
        secrets = self._storage.read_json(TELEPHONY_SECRETS_PATH, default={}) or {}
        filtered = {k: v for k, v in secrets.items() if not k.startswith(prefix)}
        if len(filtered) != len(secrets):
            self._storage.write_json(TELEPHONY_SECRETS_PATH, filtered)


class _JsonModelRepo:
    """Shared StorageProvider-backed CRUD helper for telephony entities."""

    def __init__(self, storage: StorageProvider, path: str, model_cls: type) -> None:
        self._storage = storage
        self._path = path
        self._model_cls = model_cls

    def list_all(self) -> list:
        raw = self._storage.read_json(self._path, default=[]) or []
        items = []
        for row in raw:
            try:
                items.append(self._model_cls.model_validate(row))
            except ValidationError as exc:
                logger.warning("Skipping invalid %s record: %s", self._model_cls.__name__, exc)
        return items

    def save_all(self, items: list) -> None:
        self._storage.write_json(self._path, [item.model_dump(mode="json") for item in items])

    def get(self, item_id: str):
        for item in self.list_all():
            if item.id == item_id:
                return item
        return None

    def create(self, item):
        items = self.list_all()
        items.append(item)
        self.save_all(items)
        return item

    def update(self, item):
        items = self.list_all()
        for idx, existing in enumerate(items):
            if existing.id == item.id:
                updated = item.model_copy(update={"updated_at": datetime.now(timezone.utc)})
                items[idx] = updated
                self.save_all(items)
                return updated
        return None

    def delete(self, item_id: str) -> bool:
        items = self.list_all()
        filtered = [item for item in items if item.id != item_id]
        if len(filtered) == len(items):
            return False
        self.save_all(filtered)
        return True


class TelephonyRepository:
    """Unified repository for providers, trunks, routes, gateways, settings, and secrets."""

    def __init__(self, storage: StorageProvider, master_key: str) -> None:
        self._storage = storage
        self.vault = TelephonySecretVault(storage, master_key)
        self.providers = _JsonModelRepo(storage, PROVIDERS_STORE, TelephonyProviderPublic)
        self.trunks = _JsonModelRepo(storage, TRUNKS_STORE, SipTrunkPublic)
        self.inbound_routes = _JsonModelRepo(storage, INBOUND_ROUTES_STORE, InboundRoute)
        self.outbound_routes = _JsonModelRepo(storage, OUTBOUND_ROUTES_STORE, OutboundRoute)
        self.gateways = _JsonModelRepo(storage, GATEWAYS_STORE, GsmGatewayPublic)

    def get_settings(self) -> TelephonySettings:
        raw = self._storage.read_json(TELEPHONY_SETTINGS_PATH, default=None)
        if not raw:
            return TelephonySettings()
        return TelephonySettings.model_validate(raw)

    def update_settings(self, settings: TelephonySettings) -> TelephonySettings:
        self._storage.write_json(TELEPHONY_SETTINGS_PATH, settings.model_dump(mode="json"))
        return settings
