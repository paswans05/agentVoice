# Phase 10 — Telephony Integration

## Overview

Phase 10 provides a provider-independent, local-first telephony integration layer for **agentVoice**, connecting authorized SIP carriers, self-hosted **Asterisk PBX (ARI + PJSIP)**, and documented **GSM Gateways** to the existing `CallSessionService`, `VoiceConversationService`, `CampaignExecutionService`, and `Live Calls` monitoring pipeline.

> **Important**: Real telephone calls require an authorized carrier, valid caller identity, and applicable regulatory compliance (e.g., TRAI/DLT rules in India). Carrier charges may apply. Automated tests use mocked providers and never place real telephone calls.

## Architecture & Modules

- **Provider Interface (`apps/api/app/providers/telephony/base.py`)**: Extended `TelephonyProvider` with `ProviderCapabilities`, `connect()`, `disconnect()`, `health_check()`, `register_endpoint()`, `answer_inbound_call()`, `reject_call()`, `hold_call()`, `resume_call()`, `transfer_call()`, `send_dtmf()`, and `handle_provider_event()`.
- **Asterisk ARI Adapter (`apps/api/app/providers/telephony/asterisk_ari.py`)**: Connects to Asterisk ARI over HTTP/TLS (`httpx.AsyncClient` + Basic Auth), manages channels, PJSIP endpoints, hold/resume/transfer/DTMF, and normalizes Stasis events into Phase 9 `CallEventType`.
- **GSM Gateway Adapter (`apps/api/app/providers/telephony/gsm_gateway.py`)**: Supports authorized SIP-trunk or documented vendor HTTP API gateways; explicitly marks `hardware_verified=False` when hardware is unreachable.
- **Media & Codec Layer (`apps/api/app/providers/telephony/media.py`)**: Pure-Python G.711 μ-law (`PCMU`) / A-law (`PCMA`) <-> PCM16 16 kHz conversion, codec negotiation, and `AudioFrameBuffer` jitter/packet-loss concealment.
- **Routing, Compliance & Security (`apps/api/app/services/telephony_service.py`, `apps/api/app/repositories/telephony_repository.py`)**:
  - `TelephonySecretVault` encrypts and authenticates stored passwords, ARI credentials, and webhook secrets at rest (`telephony/secrets.json`) and never returns them in GET responses.
  - `TelephonyCallRouter` validates inbound routes/working hours/active agents before answering, enforces caller ID authorization, destination restrictions, open-relay blocking, Phase 7 consent/suppression gates, and HMAC-SHA256 webhook signatures.

## Local Asterisk Development Setup

An optional local Asterisk Compose template is provided at [docker-compose.asterisk.yml](file:///d:/open-source/agentVoice/docker-compose.asterisk.yml). Bind ARI (`8088`/`8089`) and SIP (`5060`) to private/local interfaces only — never expose Asterisk management ports to the public internet.
