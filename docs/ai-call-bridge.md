# AI Call Audio Bridge (`AICallBridgeManager`)

[ai_call_bridge.py](file:///d:/open-source/agentVoice/apps/api/app/services/ai_call_bridge.py) bridges Asterisk 23 ARI `ExternalMedia` RTP streams with AgentVoice's local AI pipeline without blocking the ARI event loop.

## Audio Flow

1. **ARI Mixing Bridge**: `AsteriskARIProvider.create_external_media_bridge()` creates a `mixing` bridge (`POST /bridges`) and an `ExternalMedia` UDP RTP channel (`POST /channels/externalMedia`, format `ulaw`).
2. **Inbound Audio**: Caller RTP packets (G.711 PCMU 8kHz) are decoded to PCM16 via `TelephonyMediaAdapter.pcmu_to_pcm16()`.
3. **VAD & Barge-In**: RMS energy VAD detects caller speech and immediately calls `trigger_barge_in()` to flush any queued AI TTS packets.
4. **STT → LLM → TTS**: On end-of-utterance silence, audio is resampled to 16kHz for `STTService` (faster-whisper), passed to `ConversationService` (Ollama), synthesized with `TTSService` (Piper TTS), resampled to 8kHz PCMU, and queued as 20ms RTP packets.
5. **Cleanup**: `detach_call()` cancels active tasks, flushes audio buffers, and deletes the ARI bridge (`DELETE /bridges/{bridge_id}`).
