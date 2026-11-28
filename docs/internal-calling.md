# Internal Calling Architecture (Asterisk 23)

AgentVoice supports full internal SIP and WebRTC calling via Asterisk 23 without requiring a paid SIP trunk or external cellular gateway.

## Extensions & Dialplan

| Extension | Type | Purpose |
| --- | --- | --- |
| `1001` | UDP SIP | Softphone extension 1 |
| `1002` | UDP SIP | Softphone extension 2 |
| `1001-ws` | WebRTC (WS/DTLS-SRTP) | Browser dialer extension 1 |
| `1002-ws` | WebRTC (WS/DTLS-SRTP) | Browser dialer extension 2 |
| `600` | Internal Echo | Asterisk `Echo()` audio verification |
| `700` | AI Assistant | Enters `Stasis(agentvoice,ai-agent)` for AI voice calls |

## External Calling Safeguard

External PSTN numbers (such as `+91...` or 7+ digit phone numbers) are intentionally blocked with `EXTERNAL_TELEPHONY_NOT_CONFIGURED` (`HTTP 422`) until an authorized SIP trunk or GSM gateway is configured and connected.

## API Endpoints

- `GET /api/v1/internal-calls/extensions`
- `GET /api/v1/internal-calls/active`
- `GET /api/v1/internal-calls/history`
- `GET /api/v1/internal-calls/health`
- `GET /api/v1/internal-calls/webrtc-config`
- `POST /api/v1/internal-calls/dial`
- `POST /api/v1/internal-calls/{call_id}/hangup`
- `GET /api/v1/internal-calls/{call_id}`
