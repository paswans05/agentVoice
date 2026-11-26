"""Health and system status Pydantic schemas."""

from typing import Literal

from pydantic import BaseModel

ServiceHealthState = Literal["healthy", "degraded", "unavailable"]


class StorageHealthInfo(BaseModel):
    """Storage provider health status."""

    backend: Literal["json", "sqlite", "postgresql"]
    status: ServiceHealthState
    data_dir: str
    writable: bool


class HealthData(BaseModel):
    """Backend health check payload."""

    status: ServiceHealthState
    service: str
    version: str
    environment: str
    uptime_seconds: float
    storage: StorageHealthInfo


class SystemResources(BaseModel):
    """Host resource usage snapshot."""

    cpu_percent: float | None
    memory_total_mb: float | None
    memory_used_mb: float | None
    memory_percent: float | None
    platform: str
    python_version: str


class PhaseInfo(BaseModel):
    """Current platform development phase."""

    current_phase: int
    phase_name: str


class SystemStatusData(BaseModel):
    """Overall platform status for the dashboard."""

    app_name: str
    tagline: str
    version: str
    environment: str
    storage_backend: str
    offline_ready: bool
    external_ai_required: bool
    resources: SystemResources
    phases: PhaseInfo
