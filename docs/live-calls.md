# Phase 9 — Live Calls & Real-Time Monitoring

## Overview

Phase 9 adds real-time call monitoring, normalized call events, live partial/final transcripts, technical latency metrics, and capability-gated operator controls to **agentVoice**.

## Architecture

- **CallSession & Storage (`apps/api/app/repositories/call_session_repository.py`)**
  - Persists `CallSession`, `NormalizedCallEvent`, `TranscriptSegment`, `CallMetricsSnapshot`, and `CallMonitoringSettings` through `StorageProvider`.
  - Recording is **disabled by default** (`recording_enabled=False`) and customer phone numbers are masked via `mask_phone()`.
- **WebSocket Fan-Out (`apps/api/app/services/ws_manager.py`)**
  - `WebSocketManager` (`monitoring_ws_hub`) maintains per-subscriber bounded `asyncio.Queue(maxsize=100)` queues with non-blocking `publish_nonblocking()` so slow monitoring clients never block live voice audio.
  - Supports `SUBSCRIBE` (`call_ids`, `campaign_id`, `agent_id`), `UNSUBSCRIBE`, and `PING` / `PONG` heartbeats on `WS /api/v1/live-calls/ws`.
- **Voice Engine Integration (`apps/api/app/api/v1/voice.py`)**
  - Browser voice sessions automatically register a `CallSession` (`session_type=BROWSER`) and forward state transitions, final transcripts, latency metrics, and errors non-blockingly to `CallSessionService`.
- **Operator Controls (`CallControlService`)**
  - `terminate` and `flag` work across all active sessions.
  - `hold`, `resume`, and `transfer` are capability-gated and fail closed (`422 CALL_CONTROL_UNSUPPORTED`) when the underlying provider (such as `browser` or `dry_run`) does not support them.
  - When `require_auth=True`, `CallAuthorizationService` enforces `AGENTVOICE_SECRET_KEY` on operator controls and `WS /api/v1/live-calls/ws`.

## Frontend

- `apps/web/hooks/use-live-calls.ts`: Shared WebSocket client with exponential backoff + jitter reconnection and `PING` heartbeat.
- `apps/web/app/live-calls/page.tsx`: Real-time Live Calls dashboard, KPI summary, search/status filtering, active calls table, and recent completed calls.
- `apps/web/app/live-calls/[id]/page.tsx`: Call detail inspector with live transcript updates, keyword search, latency metrics, event timeline, and capability-gated operator controls.
