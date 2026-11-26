"""Tests for Phase 4 Speech (STT, TTS, VAD), Audio Settings, and Voice WebSocket."""

import array
import io
import json
from pathlib import Path
from typing import Any
import wave

from fastapi.testclient import TestClient

from app.api.v1.llm import get_llm_provider
from app.api.v1.speech import get_stt_service, get_tts_service
from app.core.config import Settings, get_settings
from app.main import create_app
from app.providers.stt import STTAudioError, STTProvider
from app.providers.tts import TTSProvider, TTSValidationError, TTSVoiceNotFoundError, PiperTTSProvider
from app.providers.vad import EnergyVADProvider
from app.schemas.speech import SpeechProviderHealth, STTResult, TTSVoiceInfo
from app.services.speech_service import STTService, TTSService
from tests.test_conversations import FakeChatProvider


def _make_pcm(amplitude: int, duration_ms: int, sample_rate: int = 16000) -> bytes:
    num_samples = int((sample_rate * duration_ms) / 1000)
    samples = array.array("h", [amplitude if i % 2 == 0 else -amplitude for i in range(num_samples)])
    return samples.tobytes()


def _make_silent_wav(duration_ms: int = 200, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(_make_pcm(0, duration_ms, sample_rate))
    return buf.getvalue()


class FakeSTTProvider(STTProvider):
    provider_id = "faster-whisper"

    async def health_check(self) -> SpeechProviderHealth:
        return SpeechProviderHealth(provider=self.provider_id, available=True, details="mock")

    async def transcribe(self, audio: bytes, config: dict[str, Any]) -> STTResult:
        if not audio or len(audio) < 320:
            raise STTAudioError("Audio input is empty.")
        return STTResult(
            text="Namaste, mujhe aapki service ke baare mein jaanna hai.",
            raw_text="Namaste, mujhe aapki service ke baare mein jaanna hai.",
            language="hi",
            duration_seconds=1.2,
            is_final=True,
        )

    async def supported_languages(self) -> list[str]:
        return ["hi", "en"]


class FakeTTSProvider(TTSProvider):
    provider_id = "piper"

    async def health_check(self) -> SpeechProviderHealth:
        return SpeechProviderHealth(provider=self.provider_id, available=True, details="mock")

    async def synthesize(self, text: str, config: dict[str, Any]) -> bytes:
        if not text.strip():
            raise TTSValidationError("Empty text.")
        return _make_silent_wav(100, 22050)

    async def supported_voices(self) -> list[TTSVoiceInfo]:
        return [
            TTSVoiceInfo(
                id="hi_IN-rohan-medium",
                name="hi_IN-rohan-medium",
                provider="piper",
                language="hi_IN",
            )
        ]


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app()
    test_settings = Settings(app_env="test", data_dir=str(tmp_path))
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_llm_provider] = lambda: FakeChatProvider()
    app.dependency_overrides[get_stt_service] = lambda: STTService(FakeSTTProvider())
    app.dependency_overrides[get_tts_service] = lambda: TTSService(FakeTTSProvider())
    return TestClient(app)


async def test_energy_vad_speech_boundaries() -> None:
    vad = EnergyVADProvider(threshold=0.02, min_speech_ms=200, min_silence_ms=400)
    silence = _make_pcm(0, 200)
    speech = _make_pcm(4000, 250)

    r1 = await vad.detect_speech(silence)
    assert r1.is_speech is False
    assert r1.event == "none"

    r2 = await vad.detect_speech(speech)
    assert r2.is_speech is True
    assert r2.event == "speech_start"

    r3 = await vad.detect_speech(speech)
    assert r3.event == "speech_continue"

    # Hangover silence before speech_end
    r4 = await vad.detect_speech(_make_pcm(0, 200))
    assert r4.event == "speech_continue"
    r5 = await vad.detect_speech(_make_pcm(0, 250))
    assert r5.event == "speech_end"


async def test_piper_tts_validation_and_voice_discovery(tmp_path: Path) -> None:
    tts_dir = tmp_path / "tts"
    tts_dir.mkdir()
    provider = PiperTTSProvider(tts_dir)

    # Empty text
    try:
        await provider.synthesize("   ", {"voice_id": "v1", "speed": 1.0})
        assert False, "Expected TTSValidationError"
    except TTSValidationError:
        pass

    # Invalid speed
    try:
        await provider.synthesize("Hello", {"voice_id": "v1", "speed": 3.0})
        assert False, "Expected TTSValidationError"
    except TTSValidationError:
        pass

    # Missing voice
    try:
        await provider.synthesize("Hello", {"voice_id": "missing", "speed": 1.0})
        assert False, "Expected TTSVoiceNotFoundError"
    except TTSVoiceNotFoundError:
        pass

    # Discovers .onnx + .onnx.json
    (tts_dir / "hi_IN-rohan-medium.onnx").write_bytes(b"fake-onnx")
    (tts_dir / "hi_IN-rohan-medium.onnx.json").write_text(
        json.dumps({"language": {"code": "hi_IN"}, "audio": {"sample_rate": 22050}}),
        encoding="utf-8",
    )
    voices = await provider.supported_voices()
    assert len(voices) == 1
    assert voices[0].id == "hi_IN-rohan-medium"
    assert voices[0].language == "hi_IN"


def test_speech_rest_endpoints_and_settings_persistence(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    health = client.get("/api/v1/speech/health")
    assert health.status_code == 200
    assert health.json()["data"]["vad"]["available"] is True

    voices = client.get("/api/v1/speech/tts/voices")
    assert voices.status_code == 200
    assert voices.json()["data"][0]["id"] == "hi_IN-rohan-medium"

    # Update & persist audio settings
    cfg = client.get("/api/v1/speech/settings").json()["data"]
    cfg["stt_model"] = "base"
    cfg["min_silence_ms"] = 600
    put_resp = client.put("/api/v1/speech/settings", json=cfg)
    assert put_resp.status_code == 200
    assert put_resp.json()["data"]["stt_model"] == "base"

    # Transcribe via multipart upload
    wav_bytes = _make_silent_wav(300)
    tr_resp = client.post(
        "/api/v1/speech/stt/transcribe",
        files={"file": ("test.wav", wav_bytes, "audio/wav")},
        data={"language": "hi-IN"},
    )
    assert tr_resp.status_code == 200
    assert "Namaste" in tr_resp.json()["data"]["text"]

    # Synthesize via REST
    syn_resp = client.post(
        "/api/v1/speech/tts/synthesize",
        json={"text": "Namaste!", "voice_id": "hi_IN-rohan-medium", "speed": 1.0, "pitch": 1.0},
    )
    assert syn_resp.status_code == 200
    assert syn_resp.content[:4] == b"RIFF"


def test_voice_websocket_full_turn_and_barge_in(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    # Create agent with installed model
    agent = client.post(
        "/api/v1/agents",
        json={
            "name": "Asha Voice",
            "type": "SALES",
            "instructions": {"system_prompt": "Be helpful."},
            "language": {"primary_language": "hi-IN", "hinglish_enabled": True},
            "voice": {"provider": "piper", "voice_id": "hi_IN-rohan-medium"},
            "model": {"provider": "ollama", "model_id": "qwen2.5:3b"},
        },
    ).json()["data"]

    # Create voice session
    sess_resp = client.post("/api/v1/voice/sessions", json={"agent_id": agent["id"]})
    assert sess_resp.status_code == 201
    session_info = sess_resp.json()["data"]
    session_id = session_info["session_id"]
    conv_id = session_info["conversation_id"]

    with client.websocket_connect(f"/api/v1/voice/sessions/{session_id}/stream") as ws:
        # Initial LISTENING state
        init_msg = ws.receive_json()
        assert init_msg["type"] == "session.state"
        assert init_msg["state"] == "LISTENING"

        # Send speech (300ms) followed by silence (800ms) to trigger speech_start -> speech_end
        ws.send_bytes(_make_pcm(4000, 300))
        ws.send_bytes(_make_pcm(0, 800))

        seen_types: list[str] = []
        got_wav = False
        for _ in range(15):
            msg = ws.receive()
            if "bytes" in msg and msg["bytes"] is not None:
                assert msg["bytes"][:4] == b"RIFF"
                got_wav = True
            elif "text" in msg and msg["text"] is not None:
                ev = json.loads(msg["text"])
                seen_types.append(ev["type"])
                if ev["type"] == "session.state" and ev["state"] == "LISTENING" and got_wav:
                    break

        assert "transcript.final" in seen_types
        assert "response.text" in seen_types
        assert "metrics" in seen_types
        assert got_wav is True

        # Test explicit barge-in interrupt
        ws.send_json({"type": "session.interrupt"})
        int_events = []
        for _ in range(4):
            ev = ws.receive_json()
            int_events.append(ev)
            if ev["type"] == "session.state" and ev["state"] == "LISTENING":
                break
        assert any(e.get("type") == "response.interrupted" for e in int_events)

        ws.send_json({"type": "session.end"})

    # Verify conversation persisted user transcript + assistant reply
    conv = client.get(f"/api/v1/conversations/{conv_id}").json()["data"]
    assert len(conv["messages"]) == 2
    assert "Namaste" in conv["messages"][0]["content"]
    assert conv["messages"][1]["role"] == "assistant"
