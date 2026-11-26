"""Pydantic schemas for Leads Management, Consent, Suppression, Groups, and CSV Import/Export."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class LeadStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    UNQUALIFIED = "UNQUALIFIED"
    INTERESTED = "INTERESTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    FOLLOW_UP = "FOLLOW_UP"
    CONVERTED = "CONVERTED"
    LOST = "LOST"
    DO_NOT_CONTACT = "DO_NOT_CONTACT"


class LeadPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class ConsentStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class ConsentChannel(str, Enum):
    PHONE = "PHONE"
    SMS = "SMS"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    WEB = "WEB"
    IN_PERSON = "IN_PERSON"
    OTHER = "OTHER"


class ActivityType(str, Enum):
    LEAD_CREATED = "LEAD_CREATED"
    LEAD_UPDATED = "LEAD_UPDATED"
    CSV_IMPORTED = "CSV_IMPORTED"
    AGENT_ASSIGNED = "AGENT_ASSIGNED"
    AGENT_UNASSIGNED = "AGENT_UNASSIGNED"
    STATUS_CHANGED = "STATUS_CHANGED"
    GROUP_ADDED = "GROUP_ADDED"
    GROUP_REMOVED = "GROUP_REMOVED"
    NOTE_ADDED = "NOTE_ADDED"
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    SUPPRESSION_ADDED = "SUPPRESSION_ADDED"
    SUPPRESSION_REMOVED = "SUPPRESSION_REMOVED"
    DATA_EXPORTED = "DATA_EXPORTED"


class ConsentRecord(BaseModel):
    """Auditable consent record scoped by channel and purpose."""

    model_config = ConfigDict(extra="forbid")

    id: str
    lead_id: str
    consent_status: ConsentStatus = ConsentStatus.UNKNOWN
    consent_type: str = Field(default="EXPLICIT", max_length=60)
    purpose: str = Field(default="PRODUCT_INFORMATION", min_length=2, max_length=80)
    channel: ConsentChannel = ConsentChannel.PHONE
    source: str = Field(default="manual", max_length=120)
    captured_at: datetime | None = None
    expires_at: datetime | None = None
    evidence_reference: str = Field(default="", max_length=300)
    privacy_notice_version: str = Field(default="", max_length=40)
    revoked_at: datetime | None = None
    revocation_reason: str = Field(default="", max_length=300)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsentGrantRequest(BaseModel):
    """Payload to record consent for a specific channel and purpose."""

    model_config = ConfigDict(extra="forbid")

    consent_status: ConsentStatus = ConsentStatus.GRANTED
    consent_type: str = Field(default="EXPLICIT", max_length=60)
    purpose: str = Field(default="PRODUCT_INFORMATION", min_length=2, max_length=80)
    channel: ConsentChannel = ConsentChannel.PHONE
    source: str = Field(default="manual_entry", min_length=1, max_length=120)
    evidence_reference: str = Field(default="", max_length=300)
    privacy_notice_version: str = Field(default="", max_length=40)


class ConsentRevokeRequest(BaseModel):
    """Payload to revoke consent for a channel and purpose."""

    model_config = ConfigDict(extra="forbid")

    channel: ConsentChannel = ConsentChannel.PHONE
    purpose: str = Field(default="PRODUCT_INFORMATION", min_length=2, max_length=80)
    reason: str = Field(default="User requested opt-out", max_length=300)


class SuppressionRecord(BaseModel):
    """Centralized do-not-contact suppression entry."""

    model_config = ConfigDict(extra="forbid")

    id: str
    lead_id: str | None = None
    phone: str | None = None
    normalized_phone: str | None = None
    email: str | None = None
    channel: str = Field(default="ALL", max_length=40)
    reason: str = Field(default="Opt-out requested", max_length=300)
    source: str = Field(default="manual", max_length=120)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = Field(default="operator", max_length=80)
    revoked_at: datetime | None = None
    revocation_reason: str | None = None


class SuppressionCreateRequest(BaseModel):
    """Payload to add a contact to the suppression list."""

    model_config = ConfigDict(extra="forbid")

    lead_id: str | None = None
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=160)
    channel: str = Field(default="ALL", max_length=40)
    reason: str = Field(default="Opt-out requested", min_length=2, max_length=300)
    source: str = Field(default="manual", max_length=120)


class EligibilityResult(BaseModel):
    """Reusable contact eligibility check result for future campaigns/telephony."""

    lead_id: str
    channel: ConsentChannel
    purpose: str
    eligible: bool
    blocked: bool
    reason: str
    applicable_consent_status: ConsentStatus
    suppression_status: bool


class LeadGroup(BaseModel):
    """Organizational group for segmenting leads."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=300)
    color: str = Field(default="#6366f1", max_length=24)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LeadGroupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=300)
    color: str = Field(default="#6366f1", max_length=24)


class LeadActivity(BaseModel):
    """Chronological audit/activity item for a lead."""

    model_config = ConfigDict(extra="forbid")

    activity_id: str
    lead_id: str
    activity_type: ActivityType
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor: str = "operator"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Lead(BaseModel):
    """Core Lead record."""

    model_config = ConfigDict(extra="forbid")

    id: str
    first_name: str = Field(default="", max_length=80)
    last_name: str = Field(default="", max_length=80)
    full_name: str = Field(default="", max_length=160)
    email: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    normalized_phone: str | None = Field(default=None, max_length=40)
    alternate_phone: str | None = Field(default=None, max_length=40)
    company: str = Field(default="", max_length=120)
    job_title: str = Field(default="", max_length=120)
    website: str = Field(default="", max_length=200)
    country: str = Field(default="", max_length=80)
    state: str = Field(default="", max_length=80)
    city: str = Field(default="", max_length=80)
    address: str = Field(default="", max_length=300)
    source: str = Field(default="manual", max_length=80)
    status: LeadStatus = LeadStatus.NEW
    priority: LeadPriority = LeadPriority.MEDIUM
    assigned_agent_id: str | None = None
    group_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=4000)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    consent_status: ConsentStatus = ConsentStatus.UNKNOWN
    suppressed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_contacted_at: datetime | None = None
    next_follow_up_at: datetime | None = None


class LeadCreate(BaseModel):
    """Payload to create a lead."""

    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(default="", max_length=80)
    last_name: str = Field(default="", max_length=80)
    full_name: str = Field(default="", max_length=160)
    email: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    alternate_phone: str | None = Field(default=None, max_length=40)
    company: str = Field(default="", max_length=120)
    job_title: str = Field(default="", max_length=120)
    website: str = Field(default="", max_length=200)
    country: str = Field(default="", max_length=80)
    state: str = Field(default="", max_length=80)
    city: str = Field(default="", max_length=80)
    address: str = Field(default="", max_length=300)
    source: str = Field(default="manual", max_length=80)
    status: LeadStatus = LeadStatus.NEW
    priority: LeadPriority = LeadPriority.MEDIUM
    assigned_agent_id: str | None = None
    group_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=4000)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class LeadUpdate(LeadCreate):
    """Payload to update an existing lead."""


class LeadListResponse(BaseModel):
    """Paginated leads list."""

    items: list[Lead]
    total: int
    page: int
    page_size: int
    total_pages: int


class LeadDashboardStats(BaseModel):
    """Live lead statistics for the Leads Dashboard."""

    total_leads: int
    new_leads: int
    qualified_leads: int
    interested_leads: int
    follow_up_leads: int
    converted_leads: int
    suppressed_contacts: int


class BulkUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_ids: list[str] = Field(min_length=1)
    status: LeadStatus | None = None
    priority: LeadPriority | None = None
    assigned_agent_id: str | None = None


class BulkDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_ids: list[str] = Field(min_length=1)


DuplicateStrategy = Literal["SKIP", "UPDATE_EXISTING", "IMPORT_AS_NEW"]
MatchStrategy = Literal["EMAIL", "PHONE", "EMAIL_OR_PHONE"]


class CSVImportPreviewResponse(BaseModel):
    job_id: str
    filename: str
    headers: list[str]
    total_rows: int
    sample_rows: list[dict[str, str]]
    suggested_mapping: dict[str, str]


class CSVImportValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    column_mapping: dict[str, str]
    duplicate_strategy: DuplicateStrategy = "SKIP"
    match_strategy: MatchStrategy = "EMAIL_OR_PHONE"


class CSVImportRowError(BaseModel):
    row_number: int
    message: str


class CSVImportResult(BaseModel):
    job_id: str
    total_rows: int
    imported_count: int
    skipped_count: int
    duplicate_count: int
    invalid_count: int
    updated_count: int
    errors: list[CSVImportRowError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CSVExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_ids: list[str] | None = None
    status: LeadStatus | None = None
    assigned_agent_id: str | None = None
    group_id: str | None = None
    include_consent: bool = False
