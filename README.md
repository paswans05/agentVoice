# agentVoice

**Your AI. Your Voice. Your Infrastructure.**

agentVoice is an open-source, self-hosted, local-first AI voice agent platform. Build, configure, test, and run conversational AI voice agents on your own hardware without mandatory paid AI APIs, cloud accounts, or external databases.

## Core Principles

- **Open Source & Self-Hosted**: Run locally on your PC or on your own VPS.
- **Privacy-First**: Local AI inference and local JSON/JSONL storage by default.
- **No Mandatory Paid APIs**: Designed for local LLMs (Ollama), local STT, and local TTS.
- **Hindi, Hinglish & English**: Built for natural multilingual conversations.
- **Modular Architecture**: Decoupled Next.js frontend, FastAPI backend, and provider-independent `voice-engine`.

## Project Structure

- `apps/web` — Next.js App Router dashboard (TypeScript, Tailwind CSS, TanStack Query)
- `apps/api` — FastAPI backend (Pydantic v2, AsyncIO, JSON storage foundation)
- `packages/shared-types` — Shared TypeScript API contracts
- `packages/config` — Shared app and navigation configuration
- `packages/ui` — Shared UI tokens
- `voice-engine` — Modular STT, LLM, TTS, VAD, and conversation interfaces
- `agentvoice-data` — Local-first JSON/JSONL data directory
- `docker` & `docker-compose.yml` — Containerized local development setup
- `docs/` — Architecture and installation documentation

## Quick Start

See [docs/installation.md](docs/installation.md) for full Windows, Linux/macOS, and Docker setup instructions.

```powershell
# 1. Copy environment config
Copy-Item .env.example .env

# 2. Start Backend (in apps/api)
cd apps/api
uv sync
uv run uvicorn app.main:app --reload --port 8000

# 3. Start Frontend (from repo root)
npm install
npm run dev:web
```

Open **http://localhost:3000** in your browser.

## License

MIT License — see [LICENSE](LICENSE).
