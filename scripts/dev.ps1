# Start agentVoice backend and frontend in local development mode (Windows PowerShell)
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd apps/api; uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
npm run dev:web
