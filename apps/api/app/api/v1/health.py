"""Health check and system status endpoints."""

import platform
import time
from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.providers.storage import JSONStorageProvider, StorageProvider
from app.schemas.health import (
    HealthData,
    PhaseInfo,
    StorageHealthInfo,
    SystemResources,
    SystemStatusData,
)
from app.schemas.response import ApiResponse, ok

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

router = APIRouter(tags=["health"])

_START_TIME = time.monotonic()


def get_storage(settings: Settings = Depends(get_settings)) -> StorageProvider:
    """Dependency providing the configured StorageProvider."""
    storage = JSONStorageProvider(settings.resolved_data_dir)
    storage.ensure_initialized()
    return storage


@router.get("/health", response_model=ApiResponse[HealthData])
async def health_check(
    settings: Settings = Depends(get_settings),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[HealthData]:
    """Liveness and storage health check."""
    writable = storage.is_writable()
    storage_state = "healthy" if writable else "degraded"
    overall_state = "healthy" if writable else "degraded"

    payload = HealthData(
        status=overall_state,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        uptime_seconds=round(time.monotonic() - _START_TIME, 2),
        storage=StorageHealthInfo(
            backend=settings.storage_backend,
            status=storage_state,
            data_dir=str(settings.resolved_data_dir),
            writable=writable,
        ),
    )
    return ok(payload, version=settings.app_version)


@router.get("/health/ready", response_model=ApiResponse[dict[str, bool]])
async def readiness_check(
    settings: Settings = Depends(get_settings),
    storage: StorageProvider = Depends(get_storage),
) -> ApiResponse[dict[str, bool]]:
    """Readiness probe for containers and orchestrators."""
    writable = storage.is_writable()
    return ok({"ready": writable, "storage_writable": writable}, version=settings.app_version)


@router.get("/system/status", response_model=ApiResponse[SystemStatusData])
async def system_status(
    settings: Settings = Depends(get_settings),
) -> ApiResponse[SystemStatusData]:
    """Return host resource snapshot and platform capabilities."""
    cpu_percent: float | None = None
    mem_total: float | None = None
    mem_used: float | None = None
    mem_percent: float | None = None

    if psutil is not None:
        cpu_percent = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        mem_total = round(vm.total / (1024 * 1024), 1)
        mem_used = round(vm.used / (1024 * 1024), 1)
        mem_percent = vm.percent

    payload = SystemStatusData(
        app_name=settings.app_name,
        tagline=settings.app_tagline,
        version=settings.app_version,
        environment=settings.app_env,
        storage_backend=settings.storage_backend,
        offline_ready=True,
        external_ai_required=False,
        resources=SystemResources(
            cpu_percent=cpu_percent,
            memory_total_mb=mem_total,
            memory_used_mb=mem_used,
            memory_percent=mem_percent,
            platform=f"{platform.system()} {platform.release()}",
            python_version=platform.python_version(),
        ),
        phases=PhaseInfo(
            current_phase=10,
            phase_name="Telephony Integration (Phases 1-5, 7-10 active; Phase 6 deferred)",
        ),
    )
    return ok(payload, version=settings.app_version)
