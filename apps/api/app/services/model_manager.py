"""Local model discovery, recommendations, default selection, and download tasks."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import uuid

from app.providers.llm import LLMProvider, LLMProviderError
from app.providers.storage import StorageProvider
from app.schemas.llm import (
    LLMModelInfo,
    LLMRuntimeHealth,
    ModelPullTask,
    ModelRecommendation,
    ModelsOverview,
)

logger = logging.getLogger(__name__)

REGISTRY_PATH = "models/registry.json"

MODEL_RECOMMENDATIONS: list[ModelRecommendation] = [
    ModelRecommendation(
        id="qwen2.5:3b",
        name="Qwen 2.5 3B Instruct",
        approximate_size="~1.9 GB",
        min_ram_gb=6,
        quantization="Q4_K_M (default Ollama tag)",
        language_notes="Multilingual; test Hindi/Hinglish output quality on your prompts.",
        performance_notes="Fast on CPU or entry-level GPUs; good for lower-RAM machines.",
    ),
    ModelRecommendation(
        id="qwen2.5:7b-instruct",
        name="Qwen 2.5 7B Instruct",
        approximate_size="~4.7 GB",
        min_ram_gb=12,
        quantization="Q4_K_M (default Ollama tag)",
        language_notes="Strong multilingual instruction following; verify Hindi/Hinglish locally.",
        performance_notes="Recommended balance of quality and speed with 8GB+ VRAM or 16GB RAM.",
    ),
    ModelRecommendation(
        id="llama3.2:3b",
        name="Llama 3.2 3B Instruct",
        approximate_size="~2.0 GB",
        min_ram_gb=6,
        quantization="Q4_K_M (default Ollama tag)",
        language_notes="Primarily English-focused; limited Hindi fluency.",
        performance_notes="Lightweight and responsive on CPU-only development systems.",
    ),
    ModelRecommendation(
        id="gemma2:9b",
        name="Gemma 2 9B Instruct",
        approximate_size="~5.4 GB",
        min_ram_gb=16,
        quantization="Q4_0 (default Ollama tag)",
        language_notes="Good general reasoning; test Hindi/Hinglish phrasing before production use.",
        performance_notes="Slower on CPU; best with 8GB+ VRAM.",
    ),
]


class ModelManager:
    """Manages local LLM models via LLMProvider and persists user preferences."""

    # In-memory registry of active/recent pull tasks per process
    _pull_tasks: dict[str, ModelPullTask] = {}
    _asyncio_tasks: dict[str, asyncio.Task[None]] = {}

    def __init__(self, provider: LLMProvider, storage: StorageProvider) -> None:
        self._provider = provider
        self._storage = storage

    def get_default_model_id(self) -> str | None:
        """Read saved default model preference from local storage."""
        registry = self._storage.read_json(REGISTRY_PATH, default={}) or {}
        value = registry.get("default_model_id")
        return str(value) if value else None

    def set_default_model_id(self, model_id: str) -> str:
        """Persist default model preference to local storage."""
        cleaned = model_id.strip()
        registry = self._storage.read_json(REGISTRY_PATH, default={}) or {}
        registry["default_model_id"] = cleaned
        registry["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._storage.write_json(REGISTRY_PATH, registry)
        logger.info("Default local LLM model set to %s", cleaned)
        return cleaned

    async def runtime_health(self) -> LLMRuntimeHealth:
        """Check local LLM runtime health."""
        return await self._provider.health_check()

    async def get_overview(self) -> ModelsOverview:
        """Return runtime status, installed models, default model, and recommendations."""
        runtime = await self._provider.health_check()
        default_id = self.get_default_model_id()
        installed: list[LLMModelInfo] = []

        if runtime.available:
            try:
                installed = await self._provider.list_models()
                for m in installed:
                    if default_id and m.id == default_id:
                        m.is_default = True
            except LLMProviderError as exc:
                runtime.error = str(exc)

        return ModelsOverview(
            runtime=runtime,
            installed=installed,
            default_model_id=default_id,
            recommendations=MODEL_RECOMMENDATIONS,
        )

    async def is_model_installed(self, model_id: str) -> bool:
        """Verify whether model_id is installed in the runtime."""
        return await self._provider.has_model(model_id)

    async def delete_model(self, model_id: str) -> None:
        """Delete an installed model and clear default if it matched."""
        await self._provider.delete_model(model_id)
        if self.get_default_model_id() == model_id:
            registry = self._storage.read_json(REGISTRY_PATH, default={}) or {}
            registry["default_model_id"] = None
            registry["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._storage.write_json(REGISTRY_PATH, registry)
        logger.info("Deleted local model %s", model_id)

    def start_pull(self, model_id: str) -> ModelPullTask:
        """Start a background model pull task and return its initial status."""
        cleaned = model_id.strip()
        task_id = f"pull_{uuid.uuid4().hex[:10]}"
        task_state = ModelPullTask(
            task_id=task_id,
            model_id=cleaned,
            status="DOWNLOADING",
            progress_percent=0.0,
            status_text=f"Connecting to runtime to pull {cleaned}...",
        )
        self._pull_tasks[task_id] = task_state
        bg_task = asyncio.create_task(self._run_pull(task_id, cleaned))
        self._asyncio_tasks[task_id] = bg_task
        logger.info("Started model pull task %s for model %s", task_id, cleaned)
        return task_state

    async def _run_pull(self, task_id: str, model_id: str) -> None:
        task_state = self._pull_tasks[task_id]
        try:
            async for event in self._provider.pull_model(model_id):
                total = int(event.get("total") or 0)
                completed = int(event.get("completed") or 0)
                status_text = str(event.get("status") or "Downloading...")
                pct = round((completed / total) * 100.0, 1) if total > 0 else task_state.progress_percent

                task_state.total_bytes = total
                task_state.completed_bytes = completed
                task_state.progress_percent = min(pct, 100.0)
                task_state.status_text = status_text
                task_state.updated_at = datetime.now(timezone.utc).isoformat()

                if status_text.lower() == "success":
                    task_state.progress_percent = 100.0

            task_state.status = "COMPLETED"
            task_state.progress_percent = 100.0
            task_state.status_text = "Completed"
            task_state.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info("Completed model pull task %s for %s", task_id, model_id)
        except asyncio.CancelledError:
            task_state.status = "CANCELLED"
            task_state.status_text = "Download cancelled"
            task_state.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info("Cancelled model pull task %s for %s", task_id, model_id)
        except Exception as exc:
            task_state.status = "ERROR"
            task_state.error = str(exc)
            task_state.status_text = "Download failed"
            task_state.updated_at = datetime.now(timezone.utc).isoformat()
            logger.warning("Model pull task %s failed: %s", task_id, exc)
        finally:
            self._asyncio_tasks.pop(task_id, None)

    def get_pull_task(self, task_id: str) -> ModelPullTask | None:
        """Return current pull task status or None if unknown."""
        return self._pull_tasks.get(task_id)

    def cancel_pull(self, task_id: str) -> ModelPullTask | None:
        """Cancel an in-flight model pull task if running."""
        task_state = self._pull_tasks.get(task_id)
        if task_state is None:
            return None
        bg_task = self._asyncio_tasks.get(task_id)
        if bg_task and not bg_task.done():
            bg_task.cancel()
            task_state.status = "CANCELLED"
            task_state.status_text = "Cancelling download..."
            task_state.updated_at = datetime.now(timezone.utc).isoformat()
        return task_state
