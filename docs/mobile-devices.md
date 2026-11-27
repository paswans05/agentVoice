# Android & iPhone Device Gateway

## Product Modes

1. **Mode A — Android Device Gateway**: Device registration, per-device revocable credentials, battery/network/SIM status where permitted, `TelecomManager`/`TelephonyManager` capability reporting, and explicit `CELLULAR_AUDIO_BRIDGE_UNAVAILABLE` reporting.
2. **Mode B — iPhone Companion**: Secure pairing, iOS Keychain credential storage, device health, and `CallKit` integration strictly for AgentVoice VoIP calls.
3. **Mode C — Authorized AI Telephony**: Actual AI-to-customer calls always use the backend `TelephonyProvider` (Asterisk/PJSIP/SIP trunk) connected to `CallSessionService` and `VoiceConversationService`.

## Security & Capability Honesty

- Pairing codes are single-use and short-lived (default 5 minutes).
- Device tokens are salted HMAC-SHA256 hashed at rest in `devices/device_credentials.json`, never returned in GET APIs, and can be rotated or revoked at any time.
- Neither Android nor iOS is ever marked `ai_call_ready=True` or `cellular_audio_capture=True` without a verified bidirectional audio bridge.
