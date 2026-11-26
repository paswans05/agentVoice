"""Pydantic schemas for local LLM runtime, models, and conversations."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.knowledge import SourceCitation


class ModelStatus(str, Enum):
    """Lifecycle status of a local LLM model."""

    AVAILABLE = "AVAILABLE"
    DOWNLOADING = "DOWNLOADING"
    INSTALLED = "INSTALLED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class LLMRuntimeHealth(BaseModel):
    """Health and version status of the local LLM runtime."""

    provider: str = "ollama"
    available: bool
    endpoint: str
    version: str | None = None
    error: str | None = None
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LLMProviderInfo(BaseModel):
    """Metadata describing a supported LLM provider."""

    id: str
    name: str
    description: str
    is_local: bool = True
    configured_endpoint: str


class LLMModelInfo(BaseModel):
    """Discovered or recommended local LLM model metadata."""

    id: str
    name: str
    provider: str = "ollama"
    status: ModelStatus = ModelStatus.INSTALLED
    size_bytes: int | None = None
    family: str | None = None
    parameter_size: str | None = None
    quantization: str | None = None
    modified_at: str | None = None
    is_default: bool = False


class ModelRecommendation(BaseModel):
    """Curated hardware guidance for local models (does not claim unverified capabilities)."""

    id: str
    name: str
    approximate_size: str
    min_ram_gb: int
    quantization: str
    language_notes: str
    performance_notes: str


class ModelPullTask(BaseModel):
    """Status of an asynchronous model pull/download task."""

    task_id: str
    model_id: str
    status: Literal["DOWNLOADING", "COMPLETED", "CANCELLED", "ERROR"]
    progress_percent: float = 0.0
    completed_bytes: int = 0
    total_bytes: int = 0
    status_text: str = "Starting download..."
    error: str | None = None
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ModelPullRequest(BaseModel):
    """Request payload to pull a model from Ollama."""

    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(min_length=1, max_length=160)


class DefaultModelRequest(BaseModel):
    """Request payload to set the default local model."""

    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(min_length=1, max_length=160)


class ModelsOverview(BaseModel):
    """Combined model manager payload."""

    runtime: LLMRuntimeHealth
    installed: list[LLMModelInfo]
    default_model_id: str | None = None
    recommendations: list[ModelRecommendation]


class ChatMessage(BaseModel):
    """Single message in a conversation."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=32000)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_id: str | None = None
    duration_ms: int | None = None
    sources: list[SourceCitation] = Field(default_factory=list)
    grounded: bool | None = None


class Conversation(BaseModel):
    """Persisted conversation history for an agent."""

    model_config = ConfigDict(extra="forbid")

    id: str
    agent_id: str
    model_id: str
    title: str = "New Conversation"
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationCreate(BaseModel):
    """Payload to start a new conversation for an agent."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="New Conversation", max_length=120)
    model_id: str | None = Field(default=None, max_length=160)


class SendMessageRequest(BaseModel):
    """Payload to send a user message in a conversation."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=16000)
    allow_draft_preview: bool = True


class SendMessageResult(BaseModel):
    """Response from a non-streaming message turn."""

    conversation: Conversation
    reply: ChatMessage
