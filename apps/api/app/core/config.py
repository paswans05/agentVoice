"""Application configuration loaded from environment and .env files."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve repository root (apps/api/app/core/config.py -> repo root)
REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Runtime settings for agentVoice API."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "agentVoice"
    app_tagline: str = "Your AI. Your Voice. Your Infrastructure."
    app_version: str = "0.1.0"
    app_env: Literal["development", "production", "test"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    storage_backend: Literal["json", "sqlite", "postgresql"] = "json"
    data_dir: str = str(REPO_ROOT / "agentvoice-data")

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    ollama_base_url: str = "http://localhost:11434"
    default_llm_model: str = "qwen2.5:7b-instruct"

    agentvoice_secret_key: str = Field(default="change-me-in-production", repr=False)
    require_auth: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        """Return parsed list of allowed CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def resolved_data_dir(self) -> Path:
        """Return absolute path to the data directory."""
        path = Path(self.data_dir)
        if not path.is_absolute():
            path = (REPO_ROOT / path).resolve()
        return path


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
