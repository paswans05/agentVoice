# AgentVoice Browser Dialer (`/telephony/dialer`)

The built-in WebRTC browser dialer connects directly to Asterisk 23 over SIP-over-WebSocket (`ws://127.0.0.1:8088/ws` locally, or `wss://` behind Caddy HTTPS).

## Features

1. **Extension Login**: Select `1001-ws` or `1002-ws` and enter your `.env` extension password (`ASTERISK_EXT_1001_PASSWORD` / `1002`). Passwords are never stored in browser state or returned by API endpoints.
2. **Dial Pad & Presets**: Dial `1001`, `1002`, `600` (Echo test), or `700` (AI Assistant).
3. **In-Call Controls**: Mute/unmute, hold/resume (`re-INVITE`), DTMF keypad (`RTCDTMFSender` / SIP `INFO`), live call duration, and hangup.
4. **Incoming Calls**: Answer or reject incoming SIP `INVITE` notifications.
5. **Microphone & Audio Devices**: Grant browser mic permission, select input/output devices, and monitor live mic input level.
6. **Connection Diagnostics**: Displays live Asterisk ARI connectivity, Asterisk version, WebRTC WS URL, ICE state, and external PSTN gateway status.
