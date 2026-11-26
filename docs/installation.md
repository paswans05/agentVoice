# agentVoice — Installation & Local Development Guide

## Prerequisites

- **Node.js**: 20+ (tested on Node 24) and `npm`
- **Python**: 3.11+ (tested on Python 3.14)
- **uv** (recommended) or `pip` + `venv`
- **Docker & Docker Compose** (optional, for containerized local development)

No paid AI API keys, cloud accounts, or external databases are required.

---

## Option A: Native Local Development (Windows-first)

### 1. Clone and configure environment

```powershell
git clone <your-repo-url> agentVoice
cd agentVoice
Copy-Item .env.example .env
```

### 2. Start the FastAPI Backend

Using `uv` (recommended):

```powershell
cd apps/api
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or using standard `venv` + `pip`:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify backend health:
- API Docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

### 3. Start the Next.js Frontend

In a new terminal from the repository root:

```powershell
npm install
npm run dev:web
```

Open the dashboard at: **http://localhost:3000**

---

## Option B: Linux / macOS Native Development

```bash
cp .env.example .env

# Terminal 1 — Backend
cd apps/api
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend (from repo root)
npm install
npm run dev:web
```

---

## Option C: Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Local data persists in `./agentvoice-data`

---

## Running Tests

### Backend tests

```powershell
cd apps/api
uv run pytest
```

### Frontend checks & tests

```powershell
npm run typecheck:web
npm run lint:web
npm run build:web
```
