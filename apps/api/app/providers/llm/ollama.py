"""Ollama local HTTP API provider implementation."""

from __future__ import annotations

from collections.abc import AsyncIterator
import json
import logging
from typing import Any

import httpx

from app.providers.llm.base import (
    LLMGenerationConfig,
    LLMModelNotFoundError,
    LLMProvider,
    LLMProviderError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.schemas.llm import LLMModelInfo, LLMRuntimeHealth, ModelStatus

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Async HTTP client for a local Ollama server (default http://localhost:11434)."""

    provider_id = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self.base_url = base_url.rstrip("/")

    def _client(self, timeout: float = 15.0) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def health_check(self) -> LLMRuntimeHealth:
        try:
            async with self._client(timeout=5.0) as client:
                resp = await client.get("/api/version")
                if resp.status_code == 200:
                    data = resp.json()
                    return LLMRuntimeHealth(
                        provider=self.provider_id,
                        available=True,
                        endpoint=self.base_url,
                        version=data.get("version"),
                    )
                # Fallback to /api/tags if /api/version is unavailable on older Ollama
                tags_resp = await client.get("/api/tags")
                if tags_resp.status_code == 200:
                    return LLMRuntimeHealth(
                        provider=self.provider_id,
                        available=True,
                        endpoint=self.base_url,
                        version=None,
                    )
                return LLMRuntimeHealth(
                    provider=self.provider_id,
                    available=False,
                    endpoint=self.base_url,
                    error=f"Ollama returned HTTP {resp.status_code}",
                )
        except httpx.HTTPError as exc:
            logger.info("Ollama health check failed at %s: %s", self.base_url, exc)
            return LLMRuntimeHealth(
                provider=self.provider_id,
                available=False,
                endpoint=self.base_url,
                error=(
                    f"Cannot connect to Ollama at {self.base_url}. "
                    "Ensure Ollama is installed and running (`ollama serve`)."
                ),
            )

    async def list_models(self) -> list[LLMModelInfo]:
        try:
            async with self._client(timeout=10.0) as client:
                resp = await client.get("/api/tags")
                resp.raise_for_status()
                payload = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Timed out querying Ollama models.") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(
                f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama is running."
            ) from exc

        models: list[LLMModelInfo] = []
        for item in payload.get("models", []):
            name = item.get("name") or item.get("model")
            if not name:
                continue
            details = item.get("details") or {}
            models.append(
                LLMModelInfo(
                    id=name,
                    name=name,
                    provider=self.provider_id,
                    status=ModelStatus.INSTALLED,
                    size_bytes=item.get("size"),
                    family=details.get("family"),
                    parameter_size=details.get("parameter_size"),
                    quantization=details.get("quantization_level"),
                    modified_at=item.get("modified_at"),
                )
            )
        return models

    async def has_model(self, model_id: str) -> bool:
        models = await self.list_models()
        target = model_id.strip()
        for m in models:
            if m.id == target or m.id == f"{target}:latest":
                return True
        return False

    async def generate(
        self,
        messages: list[dict[str, str]],
        config: LLMGenerationConfig,
    ) -> str:
        body = {
            "model": config.model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
        }
        try:
            async with self._client(timeout=config.timeout_seconds) as client:
                resp = await client.post("/api/chat", json=body)
                if resp.status_code == 404:
                    raise LLMModelNotFoundError(
                        f"Model '{config.model_id}' is not installed in Ollama."
                    )
                resp.raise_for_status()
                data = resp.json()
        except LLMModelNotFoundError:
            raise
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Local LLM generation timed out.") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(
                f"Ollama request failed at {self.base_url}: {exc}"
            ) from exc

        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise LLMProviderError("Invalid response payload from Ollama /api/chat.")
        return content

    async def stream(
        self,
        messages: list[dict[str, str]],
        config: LLMGenerationConfig,
    ) -> AsyncIterator[str]:
        body = {
            "model": config.model_id,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
        }
        timeout = httpx.Timeout(connect=10.0, read=config.timeout_seconds, write=15.0, pool=10.0)
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout) as client:
                async with client.stream("POST", "/api/chat", json=body) as resp:
                    if resp.status_code == 404:
                        raise LLMModelNotFoundError(
                            f"Model '{config.model_id}' is not installed in Ollama."
                        )
                    resp.raise_for_status()
                    async for raw_line in resp.aiter_lines():
                        if not raw_line.strip():
                            continue
                        try:
                            chunk = json.loads(raw_line)
                        except json.JSONDecodeError:
                            continue
                        if chunk.get("error"):
                            raise LLMProviderError(str(chunk["error"]))
                        msg = chunk.get("message") or {}
                        delta = msg.get("content")
                        if delta:
                            yield delta
                        if chunk.get("done"):
                            break
        except (LLMModelNotFoundError, LLMProviderError):
            raise
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Local LLM streaming timed out.") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(
                f"Ollama streaming failed at {self.base_url}: {exc}"
            ) from exc

    async def pull_model(self, model_id: str) -> AsyncIterator[dict[str, Any]]:
        body = {"model": model_id, "stream": True}
        timeout = httpx.Timeout(connect=10.0, read=600.0, write=15.0, pool=10.0)
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout) as client:
                async with client.stream("POST", "/api/pull", json=body) as resp:
                    resp.raise_for_status()
                    async for raw_line in resp.aiter_lines():
                        if not raw_line.strip():
                            continue
                        try:
                            event = json.loads(raw_line)
                        except json.JSONDecodeError:
                            continue
                        if event.get("error"):
                            raise LLMProviderError(str(event["error"]))
                        yield event
        except LLMProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Model pull timed out for '{model_id}'.") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(
                f"Failed to pull model '{model_id}' from Ollama: {exc}"
            ) from exc

    async def delete_model(self, model_id: str) -> None:
        try:
            async with self._client(timeout=15.0) as client:
                resp = await client.request("DELETE", "/api/delete", json={"model": model_id})
                if resp.status_code == 404:
                    raise LLMModelNotFoundError(f"Model '{model_id}' is not installed.")
                resp.raise_for_status()
        except LLMModelNotFoundError:
            raise
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Timed out deleting model '{model_id}'.") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(
                f"Failed to delete model '{model_id}' from Ollama: {exc}"
            ) from exc
