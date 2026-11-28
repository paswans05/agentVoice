<div align="center">
  <img src="apps/web/public/logo.png" alt="AgentVoice Logo" width="180" height="96" />

  <h1>AgentVoice</h1>

  <p><strong>Your AI. Your Voice. Your Infrastructure.</strong></p>

  <p>
    An open-source, self-hosted, local-first AI voice agent platform built for developers, businesses, and AI enthusiasts.
  </p>

  <p>
    Build, deploy, test, and monitor intelligent voice agents on your own hardware — connecting local LLMs, speech recognition, text-to-speech, knowledge bases, Asterisk/SIP telephony, WebRTC, and mobile gateways from one unified platform.
  </p>

  <p>
    <strong>Self-Hosted · Local-First · Modular · Provider-Neutral · Open Source</strong>
  </p>
</div>

---

## Table of Contents

- [Overview & Philosophy](#overview--philosophy)
- [Key Capabilities](#key-capabilities)
- [Architecture & Stack](#architecture--stack)
- [Quick Start (Docker & Local Dev)](#quick-start-docker--local-dev)
- [Testing & Verification](#testing--verification)
- [Contributing](#contributing)
- [Development Principles](#development-principles)
- [Security](#security)
- [Roadmap](#roadmap)
- [Documentation](#documentation)

---

## Overview & Philosophy

AgentVoice gives developers and organizations full ownership of their voice AI stack without mandatory proprietary cloud APIs or external databases.

- **Local-First AI**: Ollama (LLM), `faster-whisper` (STT), `piper-tts` (TTS), and local vector RAG.
- **Zero-Budget Telephony Dev Mode**: Built-in Asterisk 23 internal SIP/WebRTC calling (`1001-ws`, `1002-ws`, `600` Echo, `700` AI Assistant) and dry-run campaign simulation with zero paid trunks required.
- **Authorized Production Ready**: Provider-neutral SIP trunk architecture (`userpass_registration`, `ip_whitelist`, `digest_challenge`), encrypted secret vault, caller ID validation, and TRAI DLT / consent / DNC safeguards.
- **Claymorphism Design System**: Soft 3D clay surfaces, light & dark themes, and accessible components across `apps/web`.

---

## Key Capabilities

| Module | Route / Path | Highlights |
|---|---|---|
| **Overview & Analytics** | `/`, `/analytics` | Runtime health, CPU/RAM gauges, real vs dry-run metrics |
| **AI Agents** | `/agents` | Create, duplicate, activate/deactivate, personality, voice, & model config |
| **Model Manager** | `/models` | Ollama health, model pull/delete, streaming chat |
| **Voice Playground** | `/playground` | Browser mic + WebSocket voice sessions, VAD, barge-in |
| **Knowledge Base (RAG)** | `/knowledge-base` | PDF, DOCX, TXT, MD upload, chunking, local vector search, citations |
| **Leads & Compliance** | `/leads` | Lead CRUD, groups, formula-safe CSV import/export, consent & DNC suppression |
| **Campaigns** | `/campaigns` | Campaign wizard, timezone windows, retries, dry-run & authorized execution |
| **Live Calls & History** | `/live-calls`, `/call-history` | WebSocket live monitoring, masked numbers, transcripts, operator controls |
| **Telephony & Dialer** | `/telephony`, `/telephony/dialer` | Asterisk 23 ARI, PJSIP trunks, WebRTC browser dialer, GSM gateway adapter |
| **Testing Lab** | `/testing-lab` | 15+ customer personas, text/voice simulation, compliance & perf suites |
| **Mobile & Safari Gateways** | `/telephony/devices`, `agentvoice-mobile/`, `agentvoice-phone-web/` | Flutter Android/iOS CallKit companion & iPhone Safari WebRTC PWA |

> **Important**: Installing Asterisk alone does not connect to public cellular/PSTN networks. Real external calling requires an authorized SIP trunk or compatible GSM gateway.

---

## Architecture & Stack

```text
                    AGENTVOICE
                         |
          +--------------+--------------+
          |                             |
      Next.js 15                    FastAPI
      Dashboard                      API
    (Claymorphism)                     |
          |              +-------------+-------------+
          |              |             |             |
       Agents       AI Pipeline    Telephony      Storage
       Campaigns         |             |             |
       Leads         +---+---+     Asterisk 23   JSON/JSONL
       Live Calls    |       |         |         Local Data
       Dialer      Ollama  Whisper   PJSIP / ARI
                     |       |         |
                     +--- Piper --- WebRTC / SIP
                                       |
                                Mobile Gateways
```

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, TanStack Query |
| Backend | FastAPI, Pydantic v2, AsyncIO, HTTPX |
| AI / Speech | Ollama, faster-whisper, Piper TTS |
| Telephony | Asterisk 23, ARI, PJSIP, WebRTC |
| Storage | Local JSON / JSONL `StorageProvider` (`agentvoice-data/`) |
| Mobile | Flutter (Riverpod, Dio, Kotlin, Swift CallKit) & Next.js Safari PWA |
| Infrastructure | Docker Compose, Caddy |

---

## Quick Start (Docker & Local Dev)

### Prerequisites

- **Git** & **Docker Desktop** (with Docker Compose)
- **Ollama** ([ollama.com](https://ollama.com/)) running locally (`http://localhost:11434`)
- **For local dev without Docker**: **Node.js `>= 20`**, **Python `>= 3.12`**, **uv** (`https://docs.astral.sh/uv/`), and **Flutter SDK** (for `agentvoice-mobile/`)

### 1. Clone & Configure Environment

```powershell
# Windows PowerShell
git clone YOUR_GITHUB_REPOSITORY_URL
cd agentVoice
Copy-Item .env.example .env
```

```bash
# Linux / macOS
git clone YOUR_GITHUB_REPOSITORY_URL
cd agentVoice
cp .env.example .env
```

Pull a local model with Ollama:

```bash
ollama pull qwen2.5:3b
```

### 2. Run with Docker Compose (Recommended)

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

- **Dashboard**: `http://localhost:3000`
- **FastAPI Docs / Health**: `http://localhost:8000/api/v1/health`
- **Internal WebRTC Dialer**: `http://localhost:3000/telephony/dialer`

> **Docker Tip**: When configuring Asterisk in the Provider Setup Wizard while running inside Docker, use **`asterisk`** as the Host (not `127.0.0.1`) and leave **Use HTTPS / TLS** unchecked for port `8088`.

### 3. Run Locally for Development

```bash
# Backend (apps/api)
cd apps/api
uv sync --extra speech --extra dev
uv run uvicorn app.main:app --reload --port 8000

# Frontend (repo root)
npm install
npm --workspace=@agentvoice/web run dev
```

---

## Testing & Verification

Run the test suites before opening a Pull Request:

```bash
# Backend tests (apps/api)
cd apps/api
uv run --extra speech --extra dev pytest -v

# Frontend typecheck, unit tests & production build (repo root)
npm run typecheck:web
npm run test:web
npm --workspace=@agentvoice/web run build

# Docker Compose validation
docker compose config --quiet
```

Current baseline verified on this branch:
- **Backend (`pytest`)**: `64 passed`
- **Frontend (`node --test`)**: `31 passed`
- **Frontend (`tsc --noEmit` & `next build`)**: `Passed (32 routes)`

---

## Contributing

We welcome contributions from developers, AI engineers, VoIP specialists, UI/UX designers, testers, and technical writers!

### Where You Can Help

- **Backend & AI (`apps/api`)**: FastAPI endpoints, RAG optimizations, VAD/barge-in latency, new STT/TTS/LLM adapters, ARI WebSocket event listeners.
- **Telephony & VoIP (`docker/asterisk`, `apps/api/app/providers/telephony`)**: PJSIP trunk templates, carrier guides, WebRTC diagnostics, RTP handling.
- **Frontend & Claymorphism (`apps/web`, `packages/ui`)**: Claymorphism component polish, accessibility (WCAG AA), keyboard navigation, responsive mobile layouts, charts.
- **Mobile (`agentvoice-mobile`, `agentvoice-phone-web`)**: Flutter CallKit/Android VoIP improvements, Safari PWA WebRTC stability.
- **Docs & Testing (`docs/`, `tests/`)**: Setup guides, additional pytest/frontend tests, Testing Lab personas.

### Contribution Workflow

1. **Fork & Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/agentVoice.git
   cd agentVoice
   ```
2. **Create a Feature Branch**
   ```bash
   git checkout -b feat/your-feature-name
   ```
   Suggested branch prefixes: `feat/`, `fix/`, `docs/`, `test/`, `refactor/`, `style/`, `perf/`, `security/`.
3. **Make Focused Changes**
   - Preserve existing API contracts, consent/DNC safeguards, and JSON/JSONL storage compatibility.
   - Reuse shared components in `apps/web/components/clay/` and existing backend services.
   - Never commit `.env`, `certs/`, `*.pem`, SIP passwords, ARI secrets, or customer data.
4. **Verify Locally**
   - Run `pytest`, `npm run typecheck:web`, `npm run test:web`, and `npm --workspace=@agentvoice/web run build`.
5. **Commit Using Conventional Commits**
   ```bash
   git commit -m "feat: add ARI WebSocket event consumer"
   ```
6. **Open a Pull Request**
   - Describe **what** changed and **why**.
   - Link related issues.
   - Include screenshots or screen recordings for UI changes.
   - List the exact test commands you ran and their results.

### Good First Issues

- Expand frontend component tests in `apps/web/tests/`
- Add new customer personas & evaluation scenarios to Testing Lab
- Improve error messages, empty states, and loading skeletons across Claymorphism pages
- Add carrier-specific PJSIP documentation under `docs/`
- Improve keyboard navigation & ARIA labels

---

## Development Principles

1. **Local-First**: Prefer self-hosted, locally controlled models and storage.
2. **Modular & Provider-Neutral**: Keep AI, speech, storage, and SIP adapters decoupled.
3. **Secure by Default**: Encrypt credentials at rest (`TelephonySecretVault`) and mask PII.
4. **Honest & Transparent**: Clearly separate implemented, mocked/simulated, and hardware-verified capabilities.
5. **Testable**: Every new capability should include deterministic unit or integration tests.

---

## Security

Do **not** disclose security vulnerabilities in public issues before maintainers can investigate.

Never commit:
- `.env` files, API keys, or `AGENTVOICE_SECRET_KEY`
- SIP passwords or ARI credentials
- Private TLS certificates (`certs/`, `*.pem`)
- Customer phone numbers, leads, or call recordings

---

## Roadmap

- [x] Global Claymorphism design system & 22-component library (`apps/web/components/clay/`)
- [x] Internal Asterisk 23 SIP/WebRTC calling & browser dialer (`/telephony/dialer`)
- [x] Provider-neutral SIP auth modes (`userpass_registration`, `ip_whitelist`, `digest_challenge`)
- [ ] Persistent ARI WebSocket event listener in FastAPI lifespan
- [ ] Additional local LLM, STT, and TTS providers
- [ ] Verified external PSTN calling with authorized carrier trunks
- [ ] Human-agent live call handoff & multi-tenant isolation
- [ ] Plugin and extension ecosystem

---

## Documentation

- [Internal Calling Architecture](docs/internal-calling.md)
- [Asterisk 23 Internal Setup](docs/asterisk-23-setup.md)
- [Asterisk 23 External SIP Trunk Setup](docs/ASTERISK_23_SIP_SETUP.md)
- [AgentVoice Browser Dialer](docs/agentvoice-dialer.md)
- [AI Call Bridge](docs/ai-call-bridge.md)
- [SIP Integration Audit & Gap Analysis](docs/SIP_INTEGRATION_AUDIT.md)
- [Exotel SIP Integration Readiness](docs/EXOTEL_INTEGRATION.md)
- [Real Indian Mobile Calling Setup](docs/REAL_MOBILE_CALLING_SETUP.md)

---

## License

Please add an explicit open-source `LICENSE` file (e.g., MIT or Apache-2.0) before publishing the repository.

---

<p align="center">
  <strong>AgentVoice</strong> · <em>Your AI. Your Voice. Your Infrastructure.</em><br />
  Contributions are welcome!
</p>
