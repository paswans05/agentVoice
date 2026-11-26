"""Pydantic schemas for Knowledge Bases, Documents, Chunks, Retrieval, and RAG."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseStatus(str, Enum):
    """Lifecycle status of a knowledge base."""

    EMPTY = "EMPTY"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class DocumentStatus(str, Enum):
    """Processing status of an uploaded document."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"


class KnowledgeBase(BaseModel):
    """Knowledge base metadata persisted via StorageProvider."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    agent_ids: list[str] = Field(default_factory=list)
    enabled: bool = True
    status: KnowledgeBaseStatus = KnowledgeBaseStatus.EMPTY
    document_count: int = 0
    chunk_count: int = 0
    embedding_model: str = "intfloat/multilingual-e5-small"
    last_indexed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeBaseCreate(BaseModel):
    """Payload to create a knowledge base."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    agent_ids: list[str] = Field(default_factory=list)


class KnowledgeBaseUpdate(BaseModel):
    """Payload to rename or update a knowledge base."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)


class KnowledgeDocument(BaseModel):
    """Uploaded document metadata."""

    model_config = ConfigDict(extra="forbid")

    id: str
    knowledge_base_id: str
    filename: str
    file_type: str
    size_bytes: int
    status: DocumentStatus = DocumentStatus.PENDING
    chunk_count: int = 0
    error_message: str | None = None
    extraction_ms: int = 0
    chunking_ms: int = 0
    embedding_ms: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentChunk(BaseModel):
    """Chunked text unit with source metadata."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    knowledge_base_id: str
    agent_ids: list[str] = Field(default_factory=list)
    content: str
    chunk_index: int
    page_number: int | None = None
    section_title: str | None = None
    source_filename: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceCitation(BaseModel):
    """Verified source reference attached to grounded LLM replies."""

    document_id: str
    filename: str
    page_number: int | None = None
    chunk_id: str
    score: float | None = None


class RetrievalHit(BaseModel):
    """Single semantic search hit."""

    chunk_id: str
    document_id: str
    knowledge_base_id: str
    filename: str
    page_number: int | None = None
    section_title: str | None = None
    content: str
    score: float


class RetrievalTestRequest(BaseModel):
    """Request payload for retrieval search or diagnostic testing."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.25, ge=0.0, le=1.0)


class RetrievalTestResult(BaseModel):
    """Diagnostic retrieval result."""

    query: str
    hits: list[RetrievalHit]
    grounded: bool
    retrieval_ms: int = 0
    answer: str | None = None


class RAGSettings(BaseModel):
    """Configurable chunking, embedding, and retrieval defaults."""

    model_config = ConfigDict(extra="forbid")

    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "intfloat/multilingual-e5-small"
    chunk_size_tokens: int = Field(default=800, ge=100, le=4000)
    chunk_overlap_tokens: int = Field(default=120, ge=0, le=1000)
    default_top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    max_context_tokens: int = Field(default=2000, ge=200, le=8000)
    max_file_size_mb: int = Field(default=10, ge=1, le=100)
