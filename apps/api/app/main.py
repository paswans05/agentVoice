"""FastAPI application entry point for agentVoice."""

from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.providers.llm import (
    LLMModelNotFoundError,
    LLMProviderError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.providers.storage import JSONStorageProvider, StoragePathError
from app.repositories.agent_repository import AgentRepositoryError
from app.repositories.conversation_repository import ConversationRepositoryError
from app.schemas.response import fail
from app.services.agent_service import (
    AgentConflictError,
    AgentLifecycleError,
    AgentNotFoundError,
)
from app.services.conversation_service import ConversationNotFoundError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize logging and local-first JSON storage on startup."""
    settings = get_settings()
    setup_logging(settings.log_level)
    storage = JSONStorageProvider(settings.resolved_data_dir)
    storage.ensure_initialized()
    logger.info(
        "Started %s v%s (env=%s, storage=%s, data_dir=%s)",
        settings.app_name,
        settings.app_version,
        settings.app_env,
        settings.storage_backend,
        settings.resolved_data_dir,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_tagline,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AgentNotFoundError)
    async def agent_not_found_handler(request: Request, exc: AgentNotFoundError) -> JSONResponse:
        body = fail(code="NOT_FOUND", message=str(exc), version=settings.app_version)
        return JSONResponse(status_code=404, content=body.model_dump())

    @app.exception_handler(AgentLifecycleError)
    async def agent_lifecycle_handler(request: Request, exc: AgentLifecycleError) -> JSONResponse:
        body = fail(code="VALIDATION_ERROR", message=str(exc), version=settings.app_version)
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(AgentConflictError)
    async def agent_conflict_handler(request: Request, exc: AgentConflictError) -> JSONResponse:
        body = fail(code="CONFLICT", message=str(exc), version=settings.app_version)
        return JSONResponse(status_code=409, content=body.model_dump())

    @app.exception_handler(StoragePathError)
    async def storage_path_handler(request: Request, exc: StoragePathError) -> JSONResponse:
        body = fail(code="INVALID_PATH", message=str(exc), version=settings.app_version)
        return JSONResponse(status_code=400, content=body.model_dump())

    @app.exception_handler(AgentRepositoryError)
    async def repository_error_handler(request: Request, exc: AgentRepositoryError) -> JSONResponse:
        logger.error("Storage error on %s %s: %s", request.method, request.url.path, exc)
        body = fail(
            code="STORAGE_ERROR",
            message="Failed to access agent storage.",
            version=settings.app_version,
        )
        return JSONResponse(status_code=500, content=body.model_dump())

    @app.exception_handler(ConversationNotFoundError)
    async def conversation_not_found_handler(
        request: Request, exc: ConversationNotFoundError
    ) -> JSONResponse:
        body = fail(code="NOT_FOUND", message=str(exc), version=settings.app_version)
        return JSONResponse(status_code=404, content=body.model_dump())

    @app.exception_handler(ConversationRepositoryError)
    async def conversation_repo_error_handler(
        request: Request, exc: ConversationRepositoryError
    ) -> JSONResponse:
        logger.error("Conversation storage error on %s %s: %s", request.method, request.url.path, exc)
        body = fail(
            code="STORAGE_ERROR",
            message="Failed to access conversation storage.",
            version=settings.app_version,
        )
        return JSONResponse(status_code=500, content=body.model_dump())

    @app.exception_handler(LLMUnavailableError)
    async def llm_unavailable_handler(request: Request, exc: LLMUnavailableError) -> JSONResponse:
        body = fail(code="LLM_UNAVAILABLE", message=str(exc), version=settings.app_version)
        return JSONResponse(status_code=503, content=body.model_dump())

    @app.exception_handler(LLMModelNotFoundError)
    async def llm_model_not_found_handler(
        request: Request, exc: LLMModelNotFoundError
    ) -> JSONResponse:
        body = fail(code="MODEL_NOT_INSTALLED", message=str(exc), version=settings.app_version)
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(LLMTimeoutError)
    async def llm_timeout_handler(request: Request, exc: LLMTimeoutError) -> JSONResponse:
        body = fail(code="LLM_TIMEOUT", message=str(exc), version=settings.app_version)
        return JSONResponse(status_code=504, content=body.model_dump())

    @app.exception_handler(LLMProviderError)
    async def llm_provider_handler(request: Request, exc: LLMProviderError) -> JSONResponse:
        body = fail(code="LLM_PROVIDER_ERROR", message=str(exc), version=settings.app_version)
        return JSONResponse(status_code=502, content=body.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        body = fail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
            version=settings.app_version,
        )
        return JSONResponse(status_code=500, content=body.model_dump())

    app.include_router(api_v1_router)
    return app


app = create_app()
