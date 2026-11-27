"""Pydantic schemas for Campaigns, Jobs, Calls, Events, Analytics, and Telephony."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CampaignType(str, Enum):
    SALES = "SALES"
    LEAD_QUALIFICATION = "LEAD_QUALIFICATION"
    APPOINTMENT_BOOKING = "APPOINTMENT_BOOKING"
    CUSTOMER_FOLLOW_UP = "CUSTOMER_FOLLOW_UP"
    PRODUCT_INFORMATION = "PRODUCT_INFORMATION"
    CUSTOM = "CUSTOM"


class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    READY = "READY"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CampaignLeadStatus(str, Enum):
    PENDING = "PENDING"
    ELIGIBILITY_CHECK = "ELIGIBILITY_CHECK"
    QUEUED = "QUEUED"
    INITIATING = "INITIATING"
    RINGING = "RINGING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NO_ANSWER = "NO_ANSWER"
    BUSY = "BUSY"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    EXHAUSTED = "EXHAUSTED"
    DO_NOT_CONTACT = "DO_NOT_CONTACT"


class CallOutcome(str, Enum):
    INTERESTED = "INTERESTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED"
    APPOINTMENT_BOOKED = "APPOINTMENT_BOOKED"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    INFORMATION_REQUESTED = "INFORMATION_REQUESTED"
    NO_ANSWER = "NO_ANSWER"
    BUSY = "BUSY"
    WRONG_NUMBER = "WRONG_NUMBER"
    DO_NOT_CALL = "DO_NOT_CALL"
    FAILED = "FAILED"


class RetryPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retry_on_no_answer: bool = True
    retry_on_busy: bool = True
    retry_on_provider_error: bool = True
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=5.0)
    max_retry_delay_minutes: int = Field(default=240, ge=5, le=10080)


class Campaign(BaseModel):
    """Persisted outbound voice campaign configuration."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=2000)
    campaign_type: CampaignType = CampaignType.SALES
    status: CampaignStatus = CampaignStatus.DRAFT

    agent_id: str = Field(min_length=3, max_length=64)
    knowledge_base_id: str | None = Field(default=None, max_length=64)
    calling_purpose: str = Field(default="SALES_CALLS", min_length=2, max_length=80)

    lead_group_ids: list[str] = Field(default_factory=list)
    selected_lead_ids: list[str] = Field(default_factory=list)

    timezone: str = Field(default="Asia/Kolkata", min_length=2, max_length=64)
    calling_days: list[int] = Field(
        default_factory=lambda: [0, 1, 2, 3, 4, 5],
        description="0=Monday .. 6=Sunday",
    )
    start_date: str | None = None  # YYYY-MM-DD
    end_date: str | None = None    # YYYY-MM-DD
    start_time: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(default="20:00", pattern=r"^\d{2}:\d{2}$")

    maximum_calls: int = Field(default=100, ge=1, le=100000)
    maximum_concurrent_calls: int = Field(default=2, ge=1, le=50)
    maximum_attempts_per_lead: int = Field(default=3, ge=1, le=10)
    retry_interval_minutes: int = Field(default=30, ge=1, le=1440)
    minimum_interval_between_attempts_minutes: int = Field(default=15, ge=1, le=1440)
    retry_policy: RetryPolicyConfig = Field(default_factory=RetryPolicyConfig)

    dry_run: bool = True
    telephony_provider: str = Field(default="dry_run", min_length=1, max_length=60)
    recording_enabled: bool = False  # Disabled by default for privacy/compliance

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    paused_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: str = "operator"


class CampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=2000)
    campaign_type: CampaignType = CampaignType.SALES
    agent_id: str = Field(min_length=3, max_length=64)
    knowledge_base_id: str | None = Field(default=None, max_length=64)
    calling_purpose: str = Field(default="SALES_CALLS", min_length=2, max_length=80)
    lead_group_ids: list[str] = Field(default_factory=list)
    selected_lead_ids: list[str] = Field(default_factory=list)
    timezone: str = Field(default="Asia/Kolkata", min_length=2, max_length=64)
    calling_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    start_date: str | None = None
    end_date: str | None = None
    start_time: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(default="20:00", pattern=r"^\d{2}:\d{2}$")
    maximum_calls: int = Field(default=100, ge=1, le=100000)
    maximum_concurrent_calls: int = Field(default=2, ge=1, le=50)
    maximum_attempts_per_lead: int = Field(default=3, ge=1, le=10)
    retry_interval_minutes: int = Field(default=30, ge=1, le=1440)
    minimum_interval_between_attempts_minutes: int = Field(default=15, ge=1, le=1440)
    retry_policy: RetryPolicyConfig = Field(default_factory=RetryPolicyConfig)
    dry_run: bool = True
    telephony_provider: str = Field(default="dry_run", min_length=1, max_length=60)
    recording_enabled: bool = False


class CampaignUpdate(CampaignCreate):
    pass


class CampaignJob(BaseModel):
    """Idempotent queued call attempt for a lead inside a campaign."""

    model_config = ConfigDict(extra="forbid")

    id: str
    idempotency_key: str
    campaign_id: str
    lead_id: str
    attempt_number: int = 1
    status: CampaignLeadStatus = CampaignLeadStatus.PENDING
    scheduled_for: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_retry_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CampaignCallRecord(BaseModel):
    """Completed or attempted campaign call record (real vs dry-run separated)."""

    model_config = ConfigDict(extra="forbid")

    call_id: str
    campaign_id: str
    lead_id: str
    agent_id: str
    attempt_id: str
    provider_id: str
    provider_call_id: str | None = None
    is_dry_run: bool = True
    started_at: datetime
    ended_at: datetime
    duration_seconds: int = 0
    outcome: CallOutcome = CallOutcome.FAILED
    summary: str = ""
    follow_up_required: bool = False
    error_code: str | None = None
    error_message: str | None = None


class CampaignEvent(BaseModel):
    """Audit event for campaign lifecycle and execution."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    campaign_id: str
    event_type: str
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor: str = "operator"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CampaignLeadEligibilityDetail(BaseModel):
    lead_id: str
    full_name: str
    phone: str | None
    eligible: bool
    blocked: bool
    reason: str
    consent_status: str
    suppression_status: bool


class CampaignEligibilitySummary(BaseModel):
    campaign_id: str
    total_selected: int
    eligible_count: int
    ineligible_count: int
    suppressed_count: int
    unknown_consent_count: int
    invalid_phone_count: int
    details: list[CampaignLeadEligibilityDetail] = Field(default_factory=list)


class CampaignValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    eligibility: CampaignEligibilitySummary | None = None


class CampaignProgress(BaseModel):
    campaign_id: str
    status: CampaignStatus
    dry_run: bool
    total_jobs: int
    pending_jobs: int
    completed_jobs: int
    failed_jobs: int
    skipped_jobs: int
    retry_scheduled_jobs: int


class CampaignAnalytics(BaseModel):
    campaign_id: str
    total_selected_leads: int
    eligible_leads: int
    ineligible_leads: int
    queued_leads: int
    real_calls_initiated: int
    real_calls_completed: int
    real_calls_failed: int
    dry_run_calls_simulated: int
    no_answer_count: int
    busy_count: int
    interested_count: int
    not_interested_count: int
    callback_requests: int
    appointments_booked: int
    average_real_duration_seconds: float
    completion_rate_percent: float


class CampaignAnalyticsOverview(BaseModel):
    total_campaigns: int
    draft_campaigns: int
    scheduled_campaigns: int
    running_campaigns: int
    paused_campaigns: int
    completed_campaigns: int
    failed_campaigns: int
    total_real_calls: int
    total_dry_run_calls: int


class TelephonyProviderInfo(BaseModel):
    id: str
    name: str
    supports_real_calls: bool
    configured: bool
    status: str
    message: str
