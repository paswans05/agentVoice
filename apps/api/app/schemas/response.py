"""Shared API response envelope schemas."""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiMeta(BaseModel):
    """Metadata attached to every API response."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: str | None = None
    version: str = "0.1.0"


class ApiError(BaseModel):
    """Structured error payload."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ApiResponse(BaseModel, Generic[T]):
    """Standard response envelope used across all agentVoice API endpoints."""

    success: bool
    data: T | None = None
    error: ApiError | None = None
    meta: ApiMeta = Field(default_factory=ApiMeta)


def ok(
    data: T,
    *,
    request_id: str | None = None,
    version: str = "0.1.0",
) -> ApiResponse[T]:
    """Build a successful API response."""
    return ApiResponse[T](
        success=True,
        data=data,
        error=None,
        meta=ApiMeta(request_id=request_id, version=version),
    )


def fail(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
    version: str = "0.1.0",
) -> ApiResponse[None]:
    """Build an error API response."""
    return ApiResponse[None](
        success=False,
        data=None,
        error=ApiError(code=code, message=message, details=details),
        meta=ApiMeta(request_id=request_id, version=version),
    )
