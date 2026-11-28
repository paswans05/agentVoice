# AgentVoice — SIP Integration Audit & Gap Analysis Report

## 1. Audit Summary (17 Core Feature Areas)

| # | Feature Area | Status | Verification | Notes |
|---|---|---|---|---|
| 1 | Existing SIP Provider Adapter (`AsteriskARIProvider`) | **IMPLEMENTED** | **VERIFIED (Local/Mocked)** | ARI `/asterisk/info`, `/channels`, `/endpoints/PJSIP`, `/bridges`, `ExternalMedia`, hold/resume/transfer/DTMF implemented. Trunk-aware `PJSIP/{number}@{trunk}` added. |
| 2 | Asterisk ARI Connection | **IMPLEMENTED** | **VERIFIED** | Verified against Docker Asterisk 23 at `127.0.0.1:8088` and internal Docker service `asterisk:8088`. |
| 3 | PJSIP Configuration | **IMPLEMENTED** | **VERIFIED (Internal)** | Internal extensions `1001`, `1002`, `1001-ws`, `1002-ws` loaded. External trunk template added at [pjsip_trunk.conf.template](file:///d:/open-source/agentVoice/docker/asterisk/pjsip_trunk.conf.template). |
| 4 | SIP Authentication Modes | **IMPLEMENTED** | **VERIFIED (Unit)** | Supports `userpass_registration`, `ip_whitelist`, and `digest_challenge` via `SipAuthMode`. |
| 5 | SIP Registration & OPTIONS Monitoring | **PARTIALLY IMPLEMENTED** | **VERIFIED (Unit)** | `check_trunk_endpoint()` queries ARI `/endpoints/PJSIP/{trunk}` and updates `options_status`. Live carrier trunk registration is **BLOCKED BY PROVIDER**. |
| 6 | Provider Health Checks | **IMPLEMENTED** | **VERIFIED** | `GET /api/v1/telephony/providers/{id}/health` & `POST .../test` & `POST /trunks/{id}/test`. |
| 7 | Outbound Call Routing | **IMPLEMENTED** | **VERIFIED (Unit)** | `TelephonyCallRouter.initiate_authorized_outbound_call()` enforces caller ID, open-relay block, `allowed_destinations`, concurrency, duplicate guard, consent/DNC, and resolves preferred `SipTrunk`. |
| 8 | Inbound Call Routing | **PARTIALLY IMPLEMENTED** | **VERIFIED (Unit)** | `resolve_inbound_route()` & webhook handler `POST /telephony/events/{id}/webhook` work; active ARI WebSocket Stasis event consumer loop is **NOT IMPLEMENTED**. |
| 9 | Caller ID Validation | **IMPLEMENTED** | **VERIFIED (Unit)** | Enforced against `provider.caller_id` when `require_caller_id_authorization` is enabled. |
| 10 | RTP Media Handling | **IMPLEMENTED** | **VERIFIED (Local)** | `docker/asterisk/rtp.conf` (`10000-20000`), `AudioFrameBuffer` jitter buffer, and `AICallBridgeManager` RTP packet framing. |
| 11 | G.711 Codec Conversion | **IMPLEMENTED** | **VERIFIED (Unit)** | `TelephonyMediaAdapter` handles `PCMU`/`PCMA`/`L16` <-> 16kHz PCM16 with linear resampling. |
| 12 | AI Audio Bridge | **IMPLEMENTED** | **VERIFIED (Unit)** | `AICallBridgeManager` handles ARI `ExternalMedia` UDP bridge, RMS VAD, barge-in, STT -> LLM -> TTS, and cleanup. |
| 13 | Call Event Processing | **PARTIALLY IMPLEMENTED** | **VERIFIED (Unit)** | Webhook normalization (`_ARI_EVENT_MAP`) and `WebSocketManager` live monitoring fan-out work; persistent ARI WS client not yet running. |
| 14 | Call History Storage | **IMPLEMENTED** | **VERIFIED** | JSON/JSONL `CallSessionRepository`, `CallEventRepository`, `TranscriptRepository`. |
| 15 | Secret Encryption | **IMPLEMENTED** | **VERIFIED (Unit)** | `TelephonySecretVault` (PBKDF2-HMAC-SHA256 + HMAC-SHA256 EtM) + `rotate_provider_credentials()`. |
| 16 | Docker Configuration | **IMPLEMENTED** | **VERIFIED** | `docker-compose.yml` + `docker-compose.asterisk.yml` running Asterisk 23, FastAPI, Next.js, Caddy. |
| 17 | Network & Firewall Requirements | **DOCUMENTED** | **BLOCKED BY PROVIDER** | Localhost-bound for dev; static public IP + TCP 5070/TLS 443 + UDP 10000-40000 required for carrier trunks. |

---

## 2. Gap Analysis of Existing Components

- **`AsteriskARIProvider`**: Ready for ARI origination, hold, transfer, DTMF, and `ExternalMedia` bridges. Updated to format `PJSIP/{to_number}@{trunk_name}` when a trunk is active and expose `check_trunk_endpoint()`.
- **`GsmGatewayProvider`**: Supports `vendor_api` HTTP `/status` checks and `sip_trunk` metadata; physical GSM hardware is **NOT VERIFIED** (no hardware present).
- **`TelephonyMediaAdapter`**: Production-ready for `PCMU`/`PCMA` <-> `PCM16` 16kHz conversion.
- **`TelephonyCallRouter`**: Enforces all compliance gates (caller ID, open relay, destination patterns, concurrency, duplicate active lead call guard, consent/DNC). Now resolves preferred `SipTrunk` automatically.
- **`TelephonyManagementService` & `TelephonySecretVault`**: Encrypts passwords/tokens at rest, masks all secrets in API responses, and supports credential rotation + enable/disable toggling.
- **`VoiceConversationService` / `AICallBridgeManager`**: Ready for bidirectional AI voice over ARI ExternalMedia.
- **Remaining Architectural Gap**: A background ARI WebSocket (`ws://<host>:8088/ari/events`) listener in FastAPI lifespan is needed for unsolicited inbound carrier calls when not using an external webhook bridge.

---

## 3. Campaign Activation 422 Bug — Root Cause & Resolution

- **Symptom**: `POST /api/v1/campaigns/{campaign_id}/activate?run_inline=true&bypass_window=true` returned `HTTP 422 Unprocessable Entity`.
- **Root Causes Identified & Fixed**:
  1. `CampaignPolicyService` previously had a hardcoded Phase 8 block rejecting real-telephony campaigns, and `telephony_repo` was not injected into `CampaignService` / `LeadEligibilityService`.
  2. `TelephonyCallRouter.initiate_authorized_outbound_call()` called `check_contact_eligibility` synchronously with an outdated signature instead of `await self._eligibility.check_contact_eligibility(...)`.
  3. Frontend `apps/web/app/campaigns/new/page.tsx` defaulted `callingPurpose` to `"SALES_CALLS"` while leads had `"PRODUCT_INFORMATION"` consent, and filtered providers on non-existent fields. `apiFetch` also masked FastAPI `detail` messages on 422.
- **Safeguards Preserved**: Customer consent, DNC suppression, calling-window checks, contact eligibility, retry policy, and agent assignment remain strictly enforced.
