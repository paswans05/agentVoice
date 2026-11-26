"""Speech runtime health, STT, TTS, and audio settings endpoints."""

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from app.api.v1.health import get_storage
from app.core.config import Settings, get_settings
from app.providers.storage import StorageProvider
from app.providers.stt import STTProviderFactory
from app.providers.tts import TTSProviderFactory
from app.providers.vad import VADProviderFactory
from app.schemas.response import ApiResponse, ok
from app.schemas.speech import (
    AudioSettings,
    SpeechRuntimeHealth,
    STTModelInfo,
    STTResult,
    TTSSynthesizeRequest,
    TTSVoiceInfo,
)
from app.services.speech_service import (
    AudioSettingsService,
    STTService,
    TTSService,
    VADService,
    get_speech_runtime_health,
)

router = APIRouter(prefix="/speech", tags=["speech"])


def get_audio_settings_service(
    storage: StorageProvider = Depends(get_storage),
) -> AudioSettingsService:
    return AudioSettingsService(storage)


def get_stt_service(
    settings: Settings = Depends(get_settings),
    audio_svc: AudioSettingsService = Depends(get_audio_settings_service),
) -> STTService:
    audio_cfg = audio_svc.get_settings()
    stt_dir = settings.resolved_data_dir / "models" / "stt"
    stt_dir.mkdir(parents=True, exist_ok=True)
    provider = STTProviderFactory.create(
        audio_cfg.stt_provider,
        model_size=audio_cfg.stt_model,
        download_root=stt_dir,
    )
    return STTService(provider)


def get_tts_service(
    settings: Settings = Depends(get_settings),
    audio_svc: AudioSettingsService = Depends(get_audio_settings_service),
) -> TTSService:
    audio_cfg = audio_svc.get_settings()
    tts_dir = settings.resolved_data_dir / "models" / "tts"
    tts_dir.mkdir(parents=True, exist_ok=True)
    provider = TTSProviderFactory.create(
        audio_cfg.tts_provider,
        models_dir=tts_dir,
    )
    return TTSService(provider)


def get_vad_service(
    audio_svc: AudioSettingsService = Depends(get_audio_settings_service),
) -> VADService:
    audio_cfg = audio_svc.get_settings()
    provider = VADProviderFactory.create(
        "energy",
        threshold=audio_cfg.vad_threshold,
        min_speech_ms=audio_cfg.min_speech_ms,
        min_silence_ms=audio_cfg.min_silence_ms,
        max_utterance_ms=audio_cfg.max_utterance_ms,
    )
    return VADService(provider)


@router.get("/health", response_model=ApiResponse[SpeechRuntimeHealth])
async def speech_health(
    settings: Settings = Depends(get_settings),
    stt: STTService = Depends(get_stt_service),
    tts: TTSService = Depends(get_tts_service),
    vad: VADService = Depends(get_vad_service),
) -> ApiResponse[SpeechRuntimeHealth]:
    """Check health of local STT, TTS, and VAD providers."""
    health = await get_speech_runtime_health(stt, tts, vad)
    return ok(health, version=settings.app_version)


@router.get("/stt/providers", response_model=ApiResponse[list[dict[str, object]]])
async def list_stt_providers(
    settings: Settings = Depends(get_settings),
) -> ApiResponse[list[dict[str, object]]]:
    providers = [
        {
            "id": "faster-whisper",
            "name": "faster-whisper (Local CTranslate2)",
            "is_local": True,
            "license": "MIT",
        }
    ]
    return ok(providers, version=settings.app_version)


@router.get("/stt/models", response_model=ApiResponse[list[STTModelInfo]])
async def list_stt_models(
    settings: Settings = Depends(get_settings),
    stt: STTService = Depends(get_stt_service),
) -> ApiResponse[list[STTModelInfo]]:
    return ok(stt.list_models(), version=settings.app_version)


@router.post("/stt/transcribe", response_model=ApiResponse[STTResult])
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    model: str | None = Form(default=None),
    settings: Settings = Depends(get_settings),
    stt: STTService = Depends(get_stt_service),
    audio_svc: AudioSettingsService = Depends(get_audio_settings_service),
) -> ApiResponse[STTResult]:
    audio_bytes = await file.read()
    audio_cfg = audio_svc.get_settings()
    result = await stt.transcribe(
        audio_bytes,
        {
            "format": "audio/wav" if (file.filename or "").endswith(".wav") else "pcm_s16le",
            "sample_rate": audio_cfg.input_sample_rate,
            "language": language,
            "model": model or audio_cfg.stt_model,
            "hinglish_script_mode": audio_cfg.hinglish_script_mode,
        },
    )
    return ok(result, version=settings.app_version)


@router.get("/tts/providers", response_model=ApiResponse[list[dict[str, object]]])
async def list_tts_providers(
    settings: Settings = Depends(get_settings),
) -> ApiResponse[list[dict[str, object]]]:
    providers = [
        {
            "id": "piper",
            "name": "Piper TTS (Local ONNX)",
            "is_local": True,
            "license": "MIT",
        }
    ]
    return ok(providers, version=settings.app_version)


@router.get("/tts/voices", response_model=ApiResponse[list[TTSVoiceInfo]])
async def list_tts_voices(
    settings: Settings = Depends(get_settings),
    tts: TTSService = Depends(get_tts_service),
) -> ApiResponse[list[TTSVoiceInfo]]:
    voices = await tts.supported_voices()
    return ok(voices, version=settings.app_version)


@router.post("/tts/synthesize")
async def synthesize_speech(
    payload: TTSSynthesizeRequest,
    tts: TTSService = Depends(get_tts_service),
) -> Response:
    wav_bytes = await tts.synthesize(
        payload.text,
        {
            "provider": payload.provider,
            "voice_id": payload.voice_id,
            "speed": payload.speed,
            "pitch": payload.pitch,
        },
    )
    return Response(content=wav_bytes, media_type="audio/wav")


@router.get("/settings", response_model=ApiResponse[AudioSettings])
async def get_audio_settings(
    settings: Settings = Depends(get_settings),
    audio_svc: AudioSettingsService = Depends(get_audio_settings_service),
) -> ApiResponse[AudioSettings]:
    return ok(audio_svc.get_settings(), version=settings.app_version)


@router.put("/settings", response_model=ApiResponse[AudioSettings])
async def update_audio_settings(
    payload: AudioSettings,
    settings: Settings = Depends(get_settings),
    audio_svc: AudioSettingsService = Depends(get_audio_settings_service),
) -> ApiResponse[AudioSettings]:
    saved = audio_svc.update_settings(payload)
    return ok(saved, version=settings.app_version)
