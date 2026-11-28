# Asterisk 23 Docker Setup (Windows)

## Ports & Transports

- **ARI / HTTP / WebSocket**: `127.0.0.1:8088` (`http.conf`)
- **SIP (UDP & TCP)**: `127.0.0.1:5060` (`[transport-udp]`)
- **RTP Media**: `127.0.0.1:10000-10050/udp` mapped in Docker (`rtp.conf` configured for `10000-20000` with `icesupport=yes`)

## Environment Variables (`.env`)

Never hardcode production secrets. Configure these in `.env`:

```env
ASTERISK_ARI_USER=agentvoice
ASTERISK_ARI_PASSWORD=change-me-local-dev
ASTERISK_EXT_1001_PASSWORD=agentvoice-ext-1001
ASTERISK_EXT_1002_PASSWORD=agentvoice-ext-1002
```

## Starting & Verifying

```powershell
docker compose config --quiet
docker compose up -d --build
curl.exe -u "agentvoice:change-me-local-dev" http://127.0.0.1:8088/ari/asterisk/info
```

In **Telephony**, set the provider host to `asterisk` when `api` runs inside Docker, or `127.0.0.1` when `api` runs directly on the Windows host.
