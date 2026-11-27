"""Pydantic schemas for the End-to-End Testing Lab & AI Client Simulator."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TestExecutionMode(str, Enum):
    MOCKED = "mocked"
    LOCAL_SIMULATION = "local_simulation"
    REAL_MICROPHONE = "real_microphone"
    REAL_TELEPHONY = "real_telephony"


class TestCategory(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    VOICE = "voice"
    AI_CONVERSATION = "ai_conversation"
    TELEPHONY = "telephony"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"


class TestRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class CustomerPersonaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=4, max_length=500)
    language: str = Field(default="en", max_length=20)
    traits: list[str] = Field(default_factory=list)
    sample_utterances: list[str] = Field(default_factory=list)
    interrupt_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    silence_probability: float = Field(default=0.0, ge=0.0, le=1.0)


class CustomerPersona(CustomerPersonaCreate):
    id: str
    is_builtin: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TestScenarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    agent_id: str | None = Field(default=None, max_length=100)
    persona_id: str = Field(default="interested", min_length=1, max_length=80)
    language: str = Field(default="en", max_length=20)
    objective: str = Field(min_length=4, max_length=500)
    background: str = Field(default="", max_length=600)
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    expected_outcome: str = Field(default="INFORMATION_PROVIDED", max_length=120)
    max_duration_seconds: int = Field(default=180, ge=15, le=1800)
    max_turns: int = Field(default=6, ge=1, le=20)
    interruption_enabled: bool = False
    kb_questions: list[str] = Field(default_factory=list)
    objection_requirements: list[str] = Field(default_factory=list)


class TestScenarioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=120)
    agent_id: str | None = Field(default=None, max_length=100)
    persona_id: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, max_length=20)
    objective: str | None = Field(default=None, max_length=500)
    background: str | None = Field(default=None, max_length=600)
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    expected_outcome: str | None = Field(default=None, max_length=120)
    max_duration_seconds: int | None = Field(default=None, ge=15, le=1800)
    max_turns: int | None = Field(default=None, ge=1, le=20)
    interruption_enabled: bool | None = None
    kb_questions: list[str] | None = None
    objection_requirements: list[str] | None = None


class TestScenario(TestScenarioCreate):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    category: str
    passed: bool
    critical: bool = False
    description: str
    evidence: str = ""


class ConversationEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_score: int = Field(ge=0, le=100)
    passed: bool
    requires_review: bool = False
    critical_failures: list[str] = Field(default_factory=list)
    assertions: list[EvaluationAssertion] = Field(default_factory=list)
    criteria_scores: dict[str, int] = Field(default_factory=dict)
    explanation: str = ""
    manual_override_score: int | None = Field(default=None, ge=0, le=100)
    manual_review_notes: str | None = None


class SimulationTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_number: int
    customer_text: str
    agent_text: str
    customer_audio_generated: bool = False
    agent_audio_generated: bool = False
    stt_ms: int | None = None
    llm_ttft_ms: int | None = None
    llm_total_ms: int | None = None
    tts_ms: int | None = None
    end_to_end_ms: int | None = None
    interrupted: bool = False
    citations: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TestRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1, max_length=100)
    scenario_id: str | None = Field(default=None, max_length=100)
    persona_id: str = Field(default="interested", max_length=80)
    category: TestCategory = TestCategory.AI_CONVERSATION
    execution_mode: TestExecutionMode = TestExecutionMode.LOCAL_SIMULATION
    voice_enabled: bool = False
    max_turns: int = Field(default=4, ge=1, le=20)
    include_kb_checks: bool = True
    include_performance_checks: bool = False
    include_failure_recovery: bool = False


class TestRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    agent_id: str
    agent_name: str = ""
    scenario_id: str | None = None
    scenario_name: str = ""
    persona_id: str = "interested"
    category: TestCategory = TestCategory.AI_CONVERSATION
    execution_mode: TestExecutionMode = TestExecutionMode.LOCAL_SIMULATION
    status: TestRunStatus = TestRunStatus.PENDING
    model_id: str = ""
    stt_provider: str = ""
    tts_provider: str = ""
    turns: list[SimulationTurn] = Field(default_factory=list)
    evaluation: ConversationEvaluation | None = None
    avg_stt_ms: float | None = None
    avg_llm_ms: float | None = None
    avg_tts_ms: float | None = None
    error_logs: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None


class TestingOverviewStats(BaseModel):
    total_runs: int
    passed_runs: int
    failed_runs: int
    requires_review_runs: int
    avg_ai_response_ms: float | None = None
    avg_stt_ms: float | None = None
    avg_tts_ms: float | None = None
    completion_rate_percent: float = 0.0
    avg_quality_score: float | None = None
    voice_pipeline_errors: int = 0
    telephony_status: str = "Not connected"
    by_category: dict[str, dict[str, int]] = Field(default_factory=dict)
    by_execution_mode: dict[str, int] = Field(default_factory=dict)


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1, max_length=100)
    persona_id: str = Field(default="interested", max_length=80)
    scenario_id: str | None = Field(default=None, max_length=100)
    voice_enabled: bool = False
    max_turns: int = Field(default=4, ge=1, le=15)
    language: str | None = Field(default=None, max_length=20)
    interruption_enabled: bool = False


class EvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1, max_length=100)
    turns: list[SimulationTurn]
    require_ai_disclosure: bool = True
    persona_id: str = "interested"


class ManualReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    override_score: int = Field(ge=0, le=100)
    notes: str = Field(min_length=2, max_length=600)


class KnowledgeBaseTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1, max_length=100)
    questions: list[str] = Field(default_factory=list)
    test_prompt_injection: bool = True
    test_cross_agent_isolation: bool = True


class TelephonyTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(default="dry_run", min_length=1, max_length=100)
    mode: str = Field(default="dry_run", pattern="^(dry_run|real_test_call)$")
    test_recipient: str | None = Field(default=None, max_length=40)
    recipient_consent_confirmed: bool = False
    operator_approved: bool = False
    agent_id: str | None = Field(default=None, max_length=100)


class PerformanceTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1, max_length=100)
    concurrency: int = Field(default=2, ge=1, le=10)
    iterations: int = Field(default=4, ge=1, le=30)


class FailureRecoveryTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1, max_length=100)
    scenarios: list[str] = Field(
        default_factory=lambda: [
            "empty_response",
            "model_unavailable",
            "ws_disconnect",
            "barge_in_cancellation",
        ]
    )


class AssistantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1, max_length=100)
    instruction: str = Field(min_length=4, max_length=1000)
    execute: bool = False
    voice_enabled: bool = False
