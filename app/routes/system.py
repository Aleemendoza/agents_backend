"""System and observability endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from app.config import Settings
from app.dependencies import get_app_settings, get_registry

router = APIRouter(prefix="/v1", tags=["system"])


@router.get("/version")
def get_version(settings: Settings = Depends(get_app_settings)) -> dict[str, str]:
    """Expose service version metadata for smoke tests."""

    response = {
        "service": settings.service_name,
        "version": settings.service_version,
        "env": settings.env,
    }
    if settings.commit_sha:
        response["commit"] = settings.commit_sha
    return response


@router.get("/info")
def get_info(request: Request, settings: Settings = Depends(get_app_settings)) -> dict:
    """Expose runtime info and sanitized settings for smoke tests."""

    started_at: datetime = request.app.state.started_at
    uptime_seconds = int((datetime.now(UTC) - started_at).total_seconds())
    registry = get_registry()
    records = list(registry.all())
    return {
        "service": settings.service_name,
        "env": settings.env,
        "uptime_seconds": uptime_seconds,
        "agents_total": len(records),
        "agents_healthy": len([r for r in records if r.status == "healthy"]),
        "agents_broken": len([r for r in records if r.status == "broken"]),
        "settings": settings.sanitized(),
    }
