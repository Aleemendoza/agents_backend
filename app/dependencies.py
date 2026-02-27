"""Dependency providers used by FastAPI routes."""

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.core.registry import AgentRegistry
from app.services.runner import AgentRunner

_registry = AgentRegistry()


def get_registry() -> AgentRegistry:
    """Return application-wide registry instance."""

    return _registry


def get_app_settings(settings: Settings = Depends(get_settings)) -> Settings:
    """Expose settings through FastAPI dependency injection."""

    return settings


def get_runner(request: Request) -> AgentRunner:
    """Retrieve runner service attached to the FastAPI application state."""

    return request.app.state.runner
