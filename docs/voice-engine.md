# agentVoice — Speech Integration & Real-Time Voice (Phase 4)

## 1. Selected Local Engines & Licenses

| Component | Selected Engine | License | Rationale |
| :--- | :--- | :--- | :--- |
| **STT** | `faster-whisper` (CTranslate2) | MIT | Fast CPU (`int8`) and CUDA GPU (`float16`) inference, supports Hindi (`hi`), English (`en`), and Hinglish code-switching. |
| **TTS** | `Piper` (`piper-tts` / ONNX) | MIT | Lightweight local ONNX neural TTS outputting 16-bit WAV directly without mandatory FFmpeg; supports multiple languages/voices. |
| **VAD** | `EnergyVADProvider` (RMS + Hangover) | MIT | Zero-dependency offline voice activity detection with pre-roll ring buffer so utterance starts/ends are not clipped. |

## 2. Installing Speech Engines & Voice Models

### Install Python Speech Extras

```powershell
cd apps/api
uv sync --extra speech
```

Or with pip:

```bash
pip install faster-whisper piper-tts
```

### Download Piper Voice Models

Place `.onnx` and `.onnx.json` files inside `agentvoice-data/models/tts/` (e.g., `hi_IN-rohan-medium.onnx` + `hi_IN-rohan-medium.onnx.json` or `en_US-lessac-medium.onnx` + `en_US-lessac-medium.onnx.json`).

Check installed voices and runtime health at:
- `GET /api/v1/speech/health`
- `GET /api/v1/speech/tts/voices`

## 3. Real-Time Voice Pipeline & State Machine

1. Browser captures microphone audio only after clicking **Start Conversation** (`getUserMedia`, 16kHz `pcm_s16le` binary WebSocket frames).
2. Backend `EnergyVADProvider` detects `speech_start` -> `speech_continue` -> `speech_end` using a pre-roll ring buffer.
3. Backend transitions through explicit states: `LISTENING` -> `SPEECH_DETECTED` -> `TRANSCRIBING` -> `THINKING` -> `GENERATING_SPEECH` -> `SPEAKING` -> `LISTENING`.
4. `ConversationService` (Phase 3) generates the local Ollama response and persists transcripts.
5. `PiperTTSProvider` synthesizes WAV audio and streams it as binary WebSocket frames to the browser.
6. **Barge-in**: Speaking during `THINKING`/`GENERATING_SPEECH`/`SPEAKING` or clicking **Interrupt** cancels the active turn, emits `response.interrupted`, and stops browser playback immediately.

## 4. API Endpoints

- `GET /api/v1/speech/health`
- `GET /api/v1/speech/stt/providers`, `GET /api/v1/speech/stt/models`, `POST /api/v1/speech/stt/transcribe`
- `GET /api/v1/speech/tts/providers`, `GET /api/v1/speech/tts/voices`, `POST /api/v1/speech/tts/synthesize`
- `GET /api/v1/speech/settings`, `PUT /api/v1/speech/settings`
- `POST /api/v1/voice/sessions`, `GET /api/v1/voice/sessions/{session_id}`, `DELETE /api/v1/voice/sessions/{session_id}`
- `WS /api/v1/voice/sessions/{session_id}/stream`
