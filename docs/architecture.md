# agentVoice — Technical Implementation Plan & Architecture

## 1. Overview

**agentVoice** is an open-source, self-hosted, local-first AI voice agent platform.
It is structured as a modular monorepo with strict separation between:

- **Frontend (`apps/web`)**: Next.js App Router, TypeScript, Tailwind CSS, TanStack Query.
- **Backend (`apps/api`)**: FastAPI, Pydantic v2, AsyncIO, structured logging.
- **Voice Engine (`voice-engine`)**: Provider-agnostic interfaces for STT, LLM, TTS, and VAD.
- **Shared Packages (`packages/*`)**: `@agentvoice/shared-types`, `@agentvoice/config`, `@agentvoice/ui`.
- **Local Storage (`agentvoice-data/`)**: JSON/JSONL default storage with atomic writes and file locking, abstracted behind `StorageProvider` so SQLite/PostgreSQL adapters can be added without coupling business logic.

## 2. Phase 1 — Foundation (Current)

1. **Monorepo & Workspace**: npm workspaces for frontend and shared TypeScript packages; `uv`/Python project for FastAPI backend.
2. **Shared API Contract**: Every backend endpoint returns a consistent `ApiResponse[T]` envelope (`success`, `data`, `error`, `meta`).
3. **Configuration & Health**:
   - Pydantic `Settings` loaded from environment / `.env`.
   - `GET /api/v1/health` — liveness + storage writability check.
   - `GET /api/v1/health/ready` — readiness check.
   - `GET /api/v1/system/status` — host resource usage, storage backend, offline readiness.
4. **JSON Storage Foundation**:
   - `StorageProvider` abstract base class in `apps/api/app/providers/storage/base.py`.
   - `JSONStorageProvider` in `apps/api/app/providers/storage/json_storage.py` with:
     - Atomic temp-file write + `os.replace`.
     - Cross-platform file locking (`msvcrt` on Windows, `fcntl` on POSIX).
     - Path traversal protection (`_resolve_safe_path`).
     - JSONL append and read support.
     - Backup/export snapshot helper.
5. **Dashboard Shell**:
   - Responsive sidebar with all 11 platform sections.
   - Top navigation bar with live backend connection status and light/dark theme toggle.
   - Overview page displaying real backend health, storage status, and host resource metrics.
   - Settings page displaying current configuration and storage details.
   - Upcoming phase routes clearly marked as planned (no fake data or non-functional controls).

## 3. Phase 2 — Agent Management (Implemented)

- **Schemas (`apps/api/app/schemas/agent.py`)**: Strict Pydantic v2 models for `Agent`, `PersonalityConfig`, `InstructionConfig`, `LanguageConfig` (Hindi `hi-IN`, English `en-IN`, and `hinglish_enabled` response behavior), and `VoiceConfig`.
- **Repository (`apps/api/app/repositories/agent_repository.py`)**: `AgentRepository` using `StorageProvider` (`JSONStorageProvider` by default) with no direct filesystem coupling.
- **Service (`apps/api/app/services/agent_service.py`)**: `AgentService` enforcing lifecycle transitions (`DRAFT` → `ACTIVE` ↔ `INACTIVE`), activation validation, and duplication.
- **API (`apps/api/app/api/v1/agents.py`)**: Versioned CRUD, template listing, and lifecycle endpoints.
- **Frontend (`apps/web/app/agents/*`)**: Listing with search/filters, guided multi-step creation/editing form with starter templates, details view, and delete confirmation.

See [docs/agents.md](agents.md) for full schema and API details.

## 4. Upcoming Phases

- **Phase 3 — Local AI Integration**: Ollama adapter implementing `LLMProvider`, model health/listing, streaming conversation API.
- **Phase 4 — Speech Integration**: Local STT (`faster-whisper`), TTS (`Piper`), VAD (`Silero VAD`), WebSocket audio streaming.
- **Phase 5 — Voice Playground**: Real-time microphone testing, barge-in, silence detection, latency metrics.
- **Phase 6 — Knowledge Base**: Company/product/FAQ ingestion and verified-only retrieval.
- **Phase 7 — Leads & Sales Intelligence**: Lead CRUD, CSV import/export, consent tracking, 13-state sales machine.
- **Phase 8 — Campaigns**: Outbound scheduling, concurrency, retry policies, simulation mode.
- **Phase 9 — Telephony**: Authorized SIP / Asterisk / GSM gateway integration with compliance checks.
- **Phase 10 — Production Readiness**: Auth, encryption at rest, VPS hardening, full test suite.
- **Phase 11 — Desktop**: Tauri 2 wrapper for Windows, macOS, and Linux.
