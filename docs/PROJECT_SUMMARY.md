# agentVoice — Implementation Summary

**Tagline:** *Your AI. Your Voice. Your Infrastructure.*  
**Architecture:** Open-source, self-hosted, local-first AI voice agent platform (FastAPI + Next.js + local Ollama/STT/TTS/RAG + JSON/JSONL `StorageProvider`).

---

## 1. Core Platform Modules Implemented

### Phases 1–5, 7–8 (Verified Baseline)
- **Foundation & Storage**: FastAPI backend (`apps/api`), Next.js 15 dashboard (`apps/web`), shared TypeScript contracts (`packages/shared-types`, `packages/config`), and atomic local JSON/JSONL `StorageProvider` (`agentvoice-data/`).
- **Agent Management (`/agents`)**: Agent CRUD, templates, activation/deactivation, duplication, personality, instructions, language, voice, and model configuration.
- **Local LLM & Model Manager (`/models`)**: Ollama health checks, model listing/pulling, and streaming `ConversationService`.
- **Voice Playground & Speech Pipeline (`/playground`)**: Real-time WebSocket voice sessions (`VoiceConversationService`), VAD, barge-in, `faster-whisper` STT, and `piper-tts`.
- **Knowledge Base & RAG (`/knowledge-base`)**: Document upload (PDF, DOCX, TXT, MD), chunking, local vector store, retrieval with source citations, and cross-agent KB isolation.
- **Leads & Consent Management (`/leads`)**: Lead CRUD, groups, formula-safe CSV import/export, consent tracking, and Do-Not-Contact suppression safeguards.
- **Campaign Management (`/campaigns`, `/analytics`, `/call-history`)**: Campaign creation wizard, timezone-aware calling windows, retry policies, eligibility/consent gates, and local dry-run execution.

*(Phase 6 — Sales Agent Intelligence — remains deferred.)*

---

### Phase 9 — Live Calls & Real-Time Monitoring
- **Backend**:
  - `apps/api/app/schemas/live_calls.py`: `CallSession`, `NormalizedCallEvent`, `TranscriptSegment`, `CallMetricsSnapshot`, `LiveCallsStats`, `CallMonitoringSettings`, and control requests (`recording_enabled=False` by default, customer numbers masked).
  - `apps/api/app/repositories/call_session_repository.py`: `CallSessionRepository`, `CallEventRepository`, `TranscriptRepository` (partial-to-final replacement & `search_by_call()`), `CallMetricsRepository`, `CallMonitoringSettingsService`.
  - `apps/api/app/services/ws_manager.py` & `apps/api/app/services/live_calls_service.py`: Bounded-queue `WebSocketManager` (`monitoring_ws_hub`), `CallSessionService`, capability-gated `CallControlService`, and `CallAuthorizationService`.
  - `apps/api/app/api/v1/live_calls.py` & `apps/api/app/api/v1/voice.py`: REST endpoints, `WS /api/v1/live-calls/ws` (`CONNECTED`, `SUBSCRIBE`, `UNSUBSCRIBE`, `PING`/`PONG`), and non-blocking browser voice session bridging.
- **Frontend**:
  - `apps/web/hooks/use-live-calls.ts`, `apps/web/app/live-calls/page.tsx`, `apps/web/app/live-calls/[id]/page.tsx`.
- **Docs**: `docs/live-calls.md`, `docs/architecture.md`.

---

### Phase 10 — Telephony Integration (Asterisk ARI, SIP, GSM Gateway & Media)
- **Provider Interface & Adapters**:
  - `apps/api/app/providers/telephony/base.py`, `factory.py`, `asterisk_ari.py` (`AsteriskARIProvider` over ARI HTTP/TLS + PJSIP), `gsm_gateway.py` (`GsmGatewayProvider` for SIP-trunk or documented HTTP vendor APIs), and `media.py` (`TelephonyMediaAdapter` with codec negotiation, pure-Python G.711 `PCMU`/`PCMA` <-> PCM16 16 kHz conversion, and `AudioFrameBuffer`).
- **Encrypted Vault, Routing & Security**:
  - `apps/api/app/schemas/telephony.py`, `apps/api/app/repositories/telephony_repository.py` (`TelephonySecretVault` encrypting SIP/ARI/webhook secrets at rest), `apps/api/app/services/telephony_service.py` (`TelephonyManagementService`, `TelephonyCallRouter` enforcing inbound route/working-hours/active-agent validation, outbound caller ID/destination/concurrency/consent checks, structured DTMF, and HMAC-SHA256 webhook verification), and `apps/api/app/api/v1/telephony.py`.
- **Frontend**: `apps/web/app/telephony/page.tsx` and `apps/web/app/telephony/setup/page.tsx` (6-step wizard).
- **Local Asterisk Docker Setup**: `docker-compose.asterisk.yml` and `docker/asterisk/http.conf` (verified `Asterisk 23.5.0` ARI responding on `127.0.0.1:8088` and `Local Asterisk PBX` `CONNECTED` in `providers_store.json`).

---

### End-to-End Testing Lab & AI Client Simulator
- **Backend**:
  - `apps/api/app/schemas/testing.py` & `apps/api/app/repositories/testing_repository.py`: 15 built-in customer personas, custom personas, scenarios, test runs, and explicit `TestExecutionMode` separation (`mocked`, `local_simulation`, `real_microphone`, `real_telephony`).
  - `apps/api/app/services/testing_simulator.py`: `TestScenarioService`, `ClientSimulatorService` (text and voice-to-voice simulation via `ConversationService`, `STTService`, `TTSService`), and deterministic `ConversationEvaluator` (14 criteria + critical compliance assertions).
  - `apps/api/app/services/testing_suites.py` & `testing_orchestrator.py`: `KnowledgeBaseTestService`, `TelephonyTestService`, `PerformanceTestService`, `FailureRecoveryTestService`, `TestReportService` (JSON/CSV/Markdown exports + run comparison), `TestOrchestrator`, and `TestingAssistantService`.
  - `apps/api/app/api/v1/testing.py`: REST endpoints and `WS /api/v1/testing/ws`.
- **Frontend & Docs**: `apps/web/app/testing-lab/page.tsx`, `docs/testing-lab.md`.

---

### Android & iPhone Device Gateway (`agentvoice-mobile/`)
- **Backend**:
  - `apps/api/app/schemas/devices.py`, `apps/api/app/repositories/device_repository.py`, `apps/api/app/services/device_service.py`, `apps/api/app/api/v1/devices.py`: Single-use pairing codes, salted HMAC-SHA256 hashed per-device tokens, revocation/rotation, heartbeats, commands, `MobileVoIPService`, and `WS /api/v1/devices/ws`.
  - Enforces `CELLULAR_AUDIO_BRIDGE_UNAVAILABLE` (`cellular_audio_capture=False`, `cellular_audio_injection=False`, `ai_call_ready=False`).
- **Mobile App (`agentvoice-mobile/`)**:
  - Flutter + Riverpod + Dio + `flutter_secure_storage` (`lib/`), Android Kotlin bridge (`DeviceGatewayPlugin.kt`, `MainActivity.kt`, `AndroidManifest.xml` v2 embedding, `gradle.properties` IPv4 flag), and iOS Swift `CallKit` bridge (`AppDelegate.swift`, `CallKitVoipBridge.swift`).
  - Built Android debug APK (`app-debug.apk`) and passed `flutter test` (1/1).
- **Web Dashboard & Docs**: `apps/web/app/telephony/devices/page.tsx`, `[id]/page.tsx`, `wizard/page.tsx`, `docs/mobile-devices.md`.

---

### iPhone 13 Safari Web Gateway (`agentvoice-phone-web/`) & Unified Docker
- **Browser PWA (`agentvoice-phone-web/`)**:
  - Next.js mobile-first PWA (`app/page.tsx`, `/pair`, `/gateway`, `/voice-test`, `/settings`) with `PairingScreen`, `MicrophoneTest`, `VoiceSession` (`RTCPeerConnection` + `/api/v1/webrtc/ws` signaling + `/api/v1/voice/sessions/{id}/stream`), `sessionStorage`/in-memory token handling (never `localStorage`), and separate **Cellular Dialer Handoff** (`tel:`).
- **Backend WebRTC & Pairing Extensions**:
  - `POST /api/v1/devices/pairing` (60s TTL), `POST /api/v1/devices/pairing/confirm`, `POST /api/v1/webrtc/sessions`, `GET /api/v1/webrtc/sessions/{id}`, `POST /api/v1/webrtc/sessions/{id}/terminate`, and `WS /api/v1/webrtc/ws`.
- **Local HTTPS & Unified Docker Stack**:
  - `scripts/setup-iphone-https.ps1`, `docker/caddy/Caddyfile.iphone`, `docker/caddy/Caddyfile.docker`, `docker/phone-web.Dockerfile`, and unified `docker-compose.yml` (`api`, `web`, `phone-web`, `asterisk`, `caddy`).
  - `.gitignore` updated to ignore `certs/`, `*.pem`, `*.key`, `agentvoice-data/**`, and `agentvoice-phone-web/.next/`.
  - `README.md` and `docs/iphone-safari-gateway.md` updated with end-to-end setup and mobile/Safari connection guides.

---

## 2. Verification Snapshot
- **Backend (`apps/api`)**: `uv run --extra speech --extra dev pytest -v` — **50 passed** (including `test_live_calls.py`, `test_telephony.py`, `test_testing_lab.py`, `test_mobile_devices.py`).
- **Frontend (`apps/web`)**: `npm run typecheck:web` passed; `npm run test:web` — **31/31 passed**.
- **Phone PWA (`agentvoice-phone-web`)**: `npm run typecheck` & `npm run build` passed (8/8 static pages).
- **Mobile (`agentvoice-mobile`)**: `flutter test` (1/1 passed) and `flutter build apk --debug` (`app-debug.apk` built).
- **Docker**: `docker compose config --quiet` validated `docker-compose.yml`; Asterisk `23.5.0` ARI verified on `127.0.0.1:8088`.
- **Unverified Live Hardware**: Physical iPhone 13 Safari audio/WebRTC, live external SIP carrier trunks, and physical GSM gateway hardware have not been end-to-end tested in CI.
