# iPhone 13 Safari Web Gateway (iOS 26) Setup Guide

## Overview

Connect an **iPhone 13 (iOS 26 Safari)** to **agentVoice** over local Wi-Fi HTTPS/WSS without installing a native iOS app.

> **Important**: This is a browser-based **AgentVoice Internet Voice Call** (WebRTC + WebSocket audio). Safari cannot access or bridge standard iPhone cellular SIM call audio (`Cellular Dialer Handoff — AI audio bridge unavailable`).

---

## 1. Generate Local HTTPS Certificates & Caddyfile (Windows)

Install `mkcert` and `caddy` on Windows (for example via `winget install FiloSottile.mkcert` and `winget install CaddyServer.Caddy`), then run:

```powershell
.\scripts\setup-iphone-https.ps1
```

This detects your active Windows LAN IPv4 address, generates `certs/agentvoice-lan.pem` + `certs/agentvoice-lan-key.pem` via `mkcert`, and writes `docker/caddy/Caddyfile.iphone`.

Open Windows Firewall for private LAN HTTPS only (do **not** expose ports 3000 or 8000 publicly):

```powershell
New-NetFirewallRule -DisplayName "agentVoice HTTPS LAN" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow -Profile Private
```

---

## 2. Trust the `mkcert` Root CA on iPhone 13 (iOS 26)

1. Locate `rootCA.pem` from `mkcert -CAROOT`. **Never** copy `rootCA-key.pem` to the iPhone.
2. AirDrop or transfer `rootCA.pem` to your iPhone.
3. On iPhone: **Settings → General → VPN & Device Management** → tap the `mkcert` profile → **Install**.
4. Then go to **Settings → General → About → Certificate Trust Settings** and enable **Full Trust** for the `mkcert` root certificate.

---

## 3. Start Services & Connect from Safari

1. Start Backend (`apps/api`): `uv run uvicorn app.main:app --port 8000`
2. Start Desktop Dashboard (repo root): `npm run dev:web`
3. Start Phone Web PWA (`agentvoice-phone-web/`): `npm install && npm run dev` (port `3001`)
4. Start Caddy reverse proxy: `caddy run --config docker\caddy\Caddyfile.iphone`
5. In Desktop Dashboard, open **Telephony → Mobile Devices → Add Mobile Device** and generate a 60-second pairing code.
6. On iPhone Safari, open `https://<YOUR_WINDOWS_LAN_IP>/phone` (or `https://<YOUR_WINDOWS_LAN_IP>:443` routed to `agentvoice-phone-web`), enter the pairing code, tap **Connect**, grant Microphone permission when prompted, and start an **AgentVoice Internet Voice Call**.
