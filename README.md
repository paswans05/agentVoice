<p align="left">
  <img src="apps/web/public/logo.png" alt="agentVoice logo" width="48" height="48" />
</p>

# agentVoice

**Your AI. Your Voice. Your Infrastructure.**

agentVoice is an open-source, self-hosted, local-first AI voice agent platform. Build, configure, test, and run conversational AI voice agents on your own hardware without mandatory paid AI APIs, cloud accounts, or external databases.

## Core Principles

- **Open Source & Self-Hosted**: Run locally on your PC or on your own VPS.
- **Privacy-First**: Local AI inference and local JSON/JSONL storage by default (`agentvoice-data/`).
- **No Mandatory Paid APIs**: Uses local LLMs (Ollama), local STT (`faster-whisper`), local TTS (`piper-tts`), and local embeddings.
- **Hindi, Hinglish & English**: Built for natural multilingual conversations.
- **Modular Architecture**: Decoupled Next.js frontend, FastAPI backend, `voice-engine`, and optional `agentvoice-mobile` companion app.

## Implemented Capabilities

- **Agent Management** (`/agents`): Create, edit, duplicate, activate/deactivate, and configure personality, instructions, language, voice, and model settings.
- **Local LLM & Model Manager** (`/models`): Ollama health checks, model listing/pulling, and multi-turn streaming conversations.
- **Voice Playground & Speech Pipeline** (`/playground`): Real-time browser microphone + WebSocket voice sessions with VAD, barge-in, `faster-whisper` STT, and `piper-tts`.
- **Knowledge Base & RAG** (`/knowledge-base`): Upload PDF/DOCX/TXT/MD documents, chunk & index locally, and ground agent replies with source citations.
- **Leads & Consent Management** (`/leads`): Lead CRUD, groups, CSV import/export (formula-safe), consent tracking, and Do-Not-Contact suppression safeguards.
- **Campaign Management** (`/campaigns`, `/analytics`, `/call-history`): Outbound campaign wizard, timezone calling windows, retry policies, and local dry-run simulation mode.
- **Live Calls & Real-Time Monitoring** (`/live-calls`): Real-time WebSocket call monitoring, live transcripts, latency metrics, and capability-gated operator controls.
- **Telephony Integration** (`/telephony`, `/telephony/setup`): Asterisk ARI + PJSIP adapter, SIP trunks, inbound/outbound routes, authorized GSM gateway adapter, encrypted secret vault, and G.711 PCMU/PCMA media conversion.
- **Testing Lab & AI Client Simulator** (`/testing-lab`): 15+ customer personas, text and voice-to-voice simulation, deterministic compliance evaluation, KB/telephony/performance/recovery suites, and autonomous Testing Assistant.
- **Mobile Device Gateway** (`/telephony/devices`, `agentvoice-mobile/`): Android & iPhone device pairing, revocable per-device credentials, health/capability reporting, and CallKit VoIP companion.

> **Note**: Phase 6 (Sales Agent Intelligence) is currently deferred.

## Project Structure

- `apps/web` — Next.js 15 App Router dashboard (TypeScript, Tailwind CSS, TanStack Query)
- `apps/api` — FastAPI backend (Pydantic v2, AsyncIO, JSON/JSONL `StorageProvider`)
- `packages/shared-types` — Shared TypeScript API contracts
- `packages/config` — Shared app and navigation configuration
- `packages/ui` — Shared UI tokens
- `voice-engine` — Modular STT, LLM, TTS, VAD, and conversation interfaces
- `agentvoice-mobile` — Flutter + Kotlin + Swift companion app (requires Flutter/Android/Xcode SDKs)
- `agentvoice-data` — Local-first JSON/JSONL data directory
- `docker-compose.yml` & `docker-compose.asterisk.yml` — Containerized local setup & optional local Asterisk PBX
- `docs/` — Architecture, telephony, testing lab, and mobile device guides

---

## End-to-End Local Setup

### Prerequisites

- **Node.js** `>= 20` and **npm**
- **Python** `>= 3.12` and **uv** (`pip install uv` or https://docs.astral.sh/uv/)
- **Ollama** (https://ollama.com) for local LLM inference
- **Optional**: Docker (for containerized services or local Asterisk dev PBX)

### 1. Clone & Configure Environment

```powershell
# Windows PowerShell (from repo root)
Copy-Item .env.example .env
```

```bash
# Linux / macOS
cp .env.example .env
```

### 2. Start Ollama & Pull a Local Model

Make sure Ollama is running (`http://localhost:11434`), then pull a model (for example on 16 GB RAM / 4 GB VRAM hardware):

```bash
ollama pull qwen2.5:3b
```

*(You can also pull models directly from the **Model Manager** page at `/models` once the app is running.)*

### 3. Start the FastAPI Backend

```powershell
cd apps/api
uv sync --extra speech --extra dev
uv run uvicorn app.main:app --reload --port 8000
```

- Backend API: **http://localhost:8000**
- OpenAPI Docs: **http://localhost:8000/docs**

### 4. Start the Next.js Frontend

In a new terminal from the repository root:

```powershell
npm install
npm run dev:web
```

- Web Dashboard: **http://localhost:3000**

---

## End-to-End Usage Walkthrough

1. **Verify Runtime Health**: Open `/models` to confirm Ollama is connected and `/settings` to verify storage and speech providers.
2. **Create & Activate an AI Agent**: Go to `/agents/new`, configure personality, system prompt, language (`en`, `hi`, or Hinglish), voice, and local model, then **Activate** the agent.
3. **Add Company Knowledge (Optional)**: Go to `/knowledge-base`, create a Knowledge Base, upload brochures/FAQs (`.pdf`, `.docx`, `.txt`, `.md`), and assign it to your agent.
4. **Test Live Voice**: Open `/playground`, select your agent, and talk using your microphone. Open `/live-calls` in another tab to watch live transcripts, AI states, and latency metrics in real time.
5. **Run Automated Simulations**: Open `/testing-lab`, select your agent, and click **Run Full Test** (or use the **AI Testing Assistant**) to test pricing objections, Hindi/Hinglish, opt-out compliance, and KB grounding.
6. **Manage Leads & Dry-Run Campaigns**: Import contacts in `/leads/import`, verify consent, and run a local **Dry-Run** campaign in `/campaigns/new` without placing real calls.
7. **Optional Asterisk/SIP Telephony**: Start local Asterisk via [docker-compose.asterisk.yml](file:///d:/open-source/agentVoice/docker-compose.asterisk.yml) (`127.0.0.1:8088`), then configure and test your connection in `/telephony/setup`. See [docs/telephony.md](docs/telephony.md) for details and compliance requirements.

---

## Connecting the Mobile App (`agentvoice-mobile`)

The `agentvoice-mobile/` Flutter companion app connects Android and iPhone devices to your agentVoice backend for device health monitoring, single-use secure pairing, and AgentVoice VoIP endpoints.

### 1. Run the Mobile App

Requires **Flutter SDK `>= 3.3.0`** (plus Android Studio for Android, or macOS + Xcode for iPhone):

```powershell
cd agentvoice-mobile
flutter pub get
flutter run
```

### 2. Generate a Single-Use Pairing Code

1. In the web dashboard, open **Telephony → Mobile Devices** (`/telephony/devices`) and click **Add Mobile Device** (`/telephony/devices/wizard`).
2. Select **Android Device Gateway** or **iPhone Companion**.
3. Click **Generate Single-Use Pairing Code** (valid for 5 minutes).

### 3. Pair from Your Phone

1. If connecting from a **physical phone on the same Wi-Fi**, start the backend bound to all interfaces:
   ```powershell
   cd apps/api
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. In the **agentVoice** mobile app, enter your **Server URL**:
   - **Android Emulator**: `http://10.0.2.2:8000`
   - **iOS Simulator**: `http://127.0.0.1:8000`
   - **Physical Phone (same Wi-Fi)**: `http://<YOUR_PC_LOCAL_IP>:8000` *(use HTTPS/TLS in production)*
3. Enter your **Device Name** and the **Single-Use Pairing Code**, then tap **Confirm Pairing**.
4. Once paired, the app stores its per-device revocable token in Android Keystore / iOS Keychain and syncs heartbeats, battery, network, and capabilities to `/telephony/devices`.

> **Capability Note**: Android and iOS devices report `CELLULAR_AUDIO_BRIDGE_UNAVAILABLE` for standard cellular SIM calls. Actual AI-to-customer voice calls run through your configured **Asterisk/SIP** provider (`/telephony`) or an **AgentVoice VoIP** session (`/api/v1/mobile-voip/sessions`). See [docs/mobile-devices.md](docs/mobile-devices.md).

---

## Verification & Automated Tests

Run the full backend and frontend test suites from the repository root:

```powershell
# Backend tests (apps/api)
cd apps/api
uv run --extra speech --extra dev pytest -v

# Frontend typecheck, unit tests, and production build (repo root)
npm run typecheck:web
npm run test:web
npm run build:web
```

## Documentation

- [docs/installation.md](docs/installation.md) — Detailed installation guide
- [docs/architecture.md](docs/architecture.md) — System & phase architecture
- [docs/telephony.md](docs/telephony.md) — Asterisk ARI, SIP trunks, GSM gateways & compliance
- [docs/testing-lab.md](docs/testing-lab.md) — Testing Lab & AI Client Simulator
- [docs/live-calls.md](docs/live-calls.md) — Live Calls & real-time WebSocket monitoring
- [docs/mobile-devices.md](docs/mobile-devices.md) — Android & iPhone Device Gateway

## License

MIT License — see [LICENSE](LICENSE).
