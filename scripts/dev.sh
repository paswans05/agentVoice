#!/usr/bin/env bash
set -euo pipefail

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

(cd apps/api && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) &
API_PID=$!

trap 'kill $API_PID 2>/dev/null || true' EXIT

npm run dev:web
