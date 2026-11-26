"""Unit and API tests for OllamaProvider and ModelManager (with mocked Ollama HTTP)."""

import asyncio
from collections.abc import AsyncIterator
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import httpx

from app.api.v1.llm import get_llm_provider
from app.core.config import Settings, get_settings
from app.main import create_app
from app.providers.llm import (
    LLMGenerationConfig,
    LLMModelNotFoundError,
    LLMProvider,
    LLMProviderError,
    LLMTimeoutError,
    OllamaProvider,
)
from app.schemas.llm import LLMModelInfo, LLMRuntimeHealth, ModelStatus


class MockTransportProvider(LLMProvider):
    """In-memory mock LLMProvider for ModelManager and API tests."""

    provider_id = "ollama"

    def __init__(self, available: bool = True, models: list[str] | None = None) -> None:
        self.available = available
        self.models = models if models is not None else ["qwen2.5:3b"]

    async def health_check(self) -> LLMRuntimeHealth:
        return LLMRuntimeHealth(
            provider="ollama",
            available=self.available,
            endpoint="http://localhost:11434",
            version="0.5.1" if self.available else None,
            error=None if self.available else "Ollama offline",
        )

    async def list_models(self) -> list[LLMModelInfo]:
        return [
            LLMModelInfo(
                id=m,
                name=m,
                provider="ollama",
                status=ModelStatus.INSTALLED,
                size_bytes=2_000_000_000,
                family="qwen2",
            )
            for m in self.models
        ]

    async def has_model(self, model_id: str) -> bool:
        return model_id in self.models

    async def generate(self, messages: list[dict[str, str]], config: LLMGenerationConfig) -> str:
        return "Namaste! Main aapki madad kar sakti hoon."

    async def stream(
        self, messages: list[dict[str, str]], config: LLMGenerationConfig
    ) -> AsyncIterator[str]:
        for chunk in ["Namaste! ", "Kaise ", "madad karun?"]:
            yield chunk

    async def pull_model(self, model_id: str) -> AsyncIterator[dict[str, Any]]:
        yield {"status": "pulling manifest", "total": 100, "completed": 50}
        await asyncio.sleep(0.01)
        self.models.append(model_id)
        yield {"status": "success", "total": 100, "completed": 100}

    async def delete_model(self, model_id: str) -> None:
        if model_id not in self.models:
            raise LLMModelNotFoundError(f"Model '{model_id}' not found.")
        self.models.remove(model_id)


def _make_client(tmp_path: Path, provider: LLMProvider) -> TestClient:
    app = create_app()
    test_settings = Settings(app_env="test", data_dir=str(tmp_path))
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_llm_provider] = lambda: provider
    return TestClient(app)


async def test_ollama_provider_health_and_models_mocked(monkeypatch: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.5.4"})
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "qwen2.5:3b",
                            "size": 1900000000,
                            "details": {"family": "qwen2", "quantization_level": "Q4_K_M"},
                        }
                    ]
                },
            )
        if request.url.path == "/api/chat":
            body = json.loads(request.content)
            if body.get("stream"):
                lines = (
                    json.dumps({"message": {"content": "Hello "}, "done": False})
                    + "\n"
                    + json.dumps({"message": {"content": "world!"}, "done": True})
                    + "\n"
                )
                return httpx.Response(200, text=lines)
            return httpx.Response(200, json={"message": {"content": "Full reply"}})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    orig_async_client = httpx.AsyncClient

    def patched_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return orig_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    provider = OllamaProvider("http://localhost:11434")
    health = await provider.health_check()
    assert health.available is True
    assert health.version == "0.5.4"

    models = await provider.list_models()
    assert len(models) == 1
    assert models[0].id == "qwen2.5:3b"
    assert await provider.has_model("qwen2.5:3b") is True

    cfg = LLMGenerationConfig(model_id="qwen2.5:3b")
    assert await provider.generate([{"role": "user", "content": "hi"}], cfg) == "Full reply"

    chunks = [c async for c in provider.stream([{"role": "user", "content": "hi"}], cfg)]
    assert "".join(chunks) == "Hello world!"


async def test_ollama_provider_errors_mocked(monkeypatch: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/chat":
            return httpx.Response(404, json={"error": "model not found"})
        raise httpx.ReadTimeout("timeout", request=request)

    transport = httpx.MockTransport(handler)
    orig_async_client = httpx.AsyncClient

    def patched_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return orig_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)
    provider = OllamaProvider("http://localhost:11434")

    try:
        await provider.generate([{"role": "user", "content": "hi"}], LLMGenerationConfig("missing"))
        assert False, "Expected LLMModelNotFoundError"
    except LLMModelNotFoundError:
        pass

    try:
        await provider.list_models()
        assert False, "Expected LLMTimeoutError"
    except (LLMTimeoutError, LLMProviderError):
        pass


def test_models_api_overview_default_pull_and_delete(tmp_path: Path) -> None:
    provider = MockTransportProvider(available=True, models=["qwen2.5:3b"])
    client = _make_client(tmp_path, provider)

    # Overview
    resp = client.get("/api/v1/models")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["runtime"]["available"] is True
    assert len(data["installed"]) == 1

    # Set default model
    def_resp = client.post("/api/v1/models/default", json={"model_id": "qwen2.5:3b"})
    assert def_resp.status_code == 200
    assert def_resp.json()["data"]["default_model_id"] == "qwen2.5:3b"

    # Pull new model
    pull_resp = client.post("/api/v1/models/pull", json={"model_id": "llama3.2:3b"})
    assert pull_resp.status_code == 202
    task_id = pull_resp.json()["data"]["task_id"]

    # Poll pull status
    status_resp = client.get(f"/api/v1/models/pull/{task_id}")
    assert status_resp.status_code == 200

    # Delete model
    del_resp = client.delete("/api/v1/models/qwen2.5:3b")
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True
