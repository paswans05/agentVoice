"""Pydantic schemas and enums for agentVoice AI agents."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentStatus(str, Enum):
    """Lifecycle status of an AI voice agent."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AgentType(str, Enum):
    """Supported agent role types."""

    SALES = "SALES"
    CUSTOMER_SUPPORT = "CUSTOMER_SUPPORT"
    LEAD_QUALIFICATION = "LEAD_QUALIFICATION"
    APPOINTMENT_BOOKING = "APPOINTMENT_BOOKING"
    GENERAL_ASSISTANT = "GENERAL_ASSISTANT"
    CUSTOM = "CUSTOM"


class PersonalityTone(str, Enum):
    """Configured conversational tone."""

    FRIENDLY = "FRIENDLY"
    PROFESSIONAL = "PROFESSIONAL"
    FORMAL = "FORMAL"
    CASUAL = "CASUAL"
    CONFIDENT = "CONFIDENT"
    EMPATHETIC = "EMPATHETIC"
    CUSTOM = "CUSTOM"


class LanguageResponseMode(str, Enum):
    """How the agent selects response language."""

    AUTO = "AUTO"
    PRIMARY = "PRIMARY"
    FIXED = "FIXED"


SupportedLocale = Literal["hi-IN", "en-IN"]


class PersonalityConfig(BaseModel):
    """Agent personality configuration."""

    model_config = ConfigDict(extra="forbid")

    tone: PersonalityTone = PersonalityTone.FRIENDLY
    traits: list[str] = Field(default_factory=lambda: ["helpful", "polite"], max_length=12)
    custom_instructions: str = Field(default="", max_length=1500)

    @field_validator("traits")
    @classmethod
    def validate_traits(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            trimmed = item.strip()
            if trimmed:
                if len(trimmed) > 40:
                    raise ValueError("Each personality trait must be at most 40 characters.")
                cleaned.append(trimmed)
        return cleaned


class InstructionConfig(BaseModel):
    """Agent prompt and behavioral instructions (stored as config, never executed)."""

    model_config = ConfigDict(extra="forbid")

    system_prompt: str = Field(default="", max_length=8000)
    greeting: str = Field(default="", max_length=1000)
    additional_rules: list[str] = Field(default_factory=list, max_length=25)

    @field_validator("additional_rules")
    @classmethod
    def validate_rules(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for rule in value:
            trimmed = rule.strip()
            if trimmed:
                if len(trimmed) > 300:
                    raise ValueError("Each rule must be at most 300 characters.")
                cleaned.append(trimmed)
        return cleaned


class LanguageConfig(BaseModel):
    """Agent language and Hinglish behavior configuration."""

    model_config = ConfigDict(extra="forbid")

    primary_language: SupportedLocale = "en-IN"
    supported_languages: list[SupportedLocale] = Field(
        default_factory=lambda: ["en-IN", "hi-IN"],
        min_length=1,
    )
    hinglish_enabled: bool = False
    response_mode: LanguageResponseMode = LanguageResponseMode.AUTO

    @field_validator("supported_languages")
    @classmethod
    def deduplicate_languages(cls, value: list[SupportedLocale]) -> list[SupportedLocale]:
        seen: list[SupportedLocale] = []
        for lang in value:
            if lang not in seen:
                seen.append(lang)
        return seen


class VoiceConfig(BaseModel):
    """Saved TTS voice preferences (does not require an installed TTS engine)."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(default="piper", min_length=1, max_length=60)
    voice_id: str = Field(default="default", min_length=1, max_length=120)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)


class ModelConfig(BaseModel):
    """Local LLM model preferences for an agent."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(default="ollama", min_length=1, max_length=60)
    model_id: str = Field(default="", max_length=160)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=32, le=8192)
    context_window_messages: int = Field(default=20, ge=2, le=100)


class KnowledgeBaseAgentConfig(BaseModel):
    """Per-agent knowledge base and RAG retrieval settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    knowledge_base_id: str | None = Field(default=None, max_length=64)
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    max_context_tokens: int = Field(default=2000, ge=200, le=8000)
    require_sources_for_company_facts: bool = True
    fallback_when_not_found: bool = True


class Agent(BaseModel):
    """Complete persisted AI voice agent configuration."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)
    avatar: str = Field(default="bot", max_length=32)
    type: AgentType = AgentType.GENERAL_ASSISTANT
    status: AgentStatus = AgentStatus.DRAFT

    personality: PersonalityConfig = Field(default_factory=PersonalityConfig)
    instructions: InstructionConfig = Field(default_factory=InstructionConfig)
    language: LanguageConfig = Field(default_factory=LanguageConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    knowledge_base: KnowledgeBaseAgentConfig = Field(default_factory=KnowledgeBaseAgentConfig)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)


class AgentCreate(BaseModel):
    """Payload for creating a new agent (always starts as DRAFT)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)
    avatar: str = Field(default="bot", max_length=32)
    type: AgentType = AgentType.GENERAL_ASSISTANT
    template_id: str | None = Field(default=None, max_length=64)

    personality: PersonalityConfig = Field(default_factory=PersonalityConfig)
    instructions: InstructionConfig = Field(default_factory=InstructionConfig)
    language: LanguageConfig = Field(default_factory=LanguageConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    knowledge_base: KnowledgeBaseAgentConfig = Field(default_factory=KnowledgeBaseAgentConfig)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 2:
            raise ValueError("Agent name must be at least 2 characters.")
        return trimmed


class AgentUpdate(BaseModel):
    """Payload for updating an existing agent's configuration."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)
    avatar: str = Field(default="bot", max_length=32)
    type: AgentType = AgentType.GENERAL_ASSISTANT

    personality: PersonalityConfig
    instructions: InstructionConfig
    language: LanguageConfig
    voice: VoiceConfig
    model: ModelConfig = Field(default_factory=ModelConfig)
    knowledge_base: KnowledgeBaseAgentConfig = Field(default_factory=KnowledgeBaseAgentConfig)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 2:
            raise ValueError("Agent name must be at least 2 characters.")
        return trimmed


class AgentTemplate(BaseModel):
    """Starter configuration template for quick agent creation."""

    id: str
    name: str
    description: str
    avatar: str
    type: AgentType
    personality: PersonalityConfig
    instructions: InstructionConfig
    language: LanguageConfig
    voice: VoiceConfig
    model: ModelConfig = Field(default_factory=ModelConfig)
    knowledge_base: KnowledgeBaseAgentConfig = Field(default_factory=KnowledgeBaseAgentConfig)
