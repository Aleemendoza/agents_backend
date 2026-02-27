"""Application configuration module."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    env: str = Field(default="development", alias="ENV")
    port: int = Field(default=8000, alias="PORT")
    agent_api_key: str = Field(default="supersecrettoken", alias="AGENT_API_KEY")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
    agents_dir: Path = Field(default=Path("agents"), alias="AGENTS_DIR")
    request_log_file: Path = Field(default=Path("runtime_requests.jsonl"), alias="REQUEST_LOG_FILE")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


@lru_cache

def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
