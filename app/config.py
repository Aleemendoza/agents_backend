"""Application configuration module."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    env: str = Field(default="development", alias="ENV")
    service_name: str = Field(default="ethercode-agent-runtime", alias="SERVICE_NAME")
    service_version: str = Field(default="1.1.0", alias="SERVICE_VERSION")
    commit_sha: str = Field(default="", alias="COMMIT_SHA")

    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    agent_api_key: str = Field(default="supersecrettoken", alias="AGENT_API_KEY")
    agents_dir: Path = Field(default=Path("agents"), alias="AGENTS_DIR")
    request_log_file: Path = Field(default=Path("runtime_requests.jsonl"), alias="REQUEST_LOG_FILE")

    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    max_body_bytes: int = Field(default=262144, alias="MAX_BODY_BYTES")

    rate_limit_enabled: bool = Field(default=False, alias="RATE_LIMIT_ENABLED")
    rate_limit_per_min: int = Field(default=60, alias="RATE_LIMIT_PER_MIN")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @property
    def is_development(self) -> bool:
        return self.env.lower() == "development"

    @property
    def effective_rate_limit_enabled(self) -> bool:
        if self.env.lower() == "production":
            return True if self.rate_limit_enabled is False else self.rate_limit_enabled
        return self.rate_limit_enabled

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if self.env.lower() == "production":
            return [origin for origin in origins if origin != "*"]
        return origins or ["http://localhost:3000"]

    def sanitized(self) -> dict[str, str | int | bool]:
        """Return safe settings data for info endpoints."""

        return {
            "env": self.env,
            "port": self.port,
            "log_level": self.log_level,
            "agents_dir": str(self.agents_dir),
            "request_log_file": str(self.request_log_file),
            "cors_origins": ",".join(self.cors_origin_list),
            "max_body_bytes": self.max_body_bytes,
            "rate_limit_enabled": self.effective_rate_limit_enabled,
            "rate_limit_per_min": self.rate_limit_per_min,
        }


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
