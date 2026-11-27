# agentVoice Mobile (Android & iPhone Device Gateway)

Flutter companion application for **agentVoice** supporting:
- **Mode A — Android Device Gateway**: Secure pairing, `TelecomManager`/`TelephonyManager` permitted status, battery/network/SIM presence, and explicit `CELLULAR_AUDIO_BRIDGE_UNAVAILABLE` reporting.
- **Mode B — iPhone Companion**: Secure pairing, Keychain credential storage, device health, and `CallKit` integration strictly for AgentVoice VoIP calls.
- **Mode C — Authorized AI Telephony**: Actual AI-to-customer calls always route through the backend `TelephonyProvider` (Asterisk/PJSIP/SIP trunk) + `CallSessionService` + `VoiceConversationService`.

## Build Prerequisites (Not Installed on CI Host)
- Flutter SDK `>=3.3.0` & Dart SDK
- Android Studio / Android SDK (for Android builds)
- macOS + Xcode (for iOS CallKit builds)
