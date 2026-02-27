"""Development-only endpoints."""

import json
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.config import Settings
from app.core.loader import AgentLoader
from app.core.security import require_api_key
from app.dependencies import get_app_settings, get_registry
from app.services.runner import AgentRunner

router = APIRouter(prefix="/v1/dev", tags=["dev"], dependencies=[Depends(require_api_key)])


@router.post("/reload-agents")
def reload_agents(request: Request, settings: Settings = Depends(get_app_settings)) -> dict[str, bool | int]:
    """Reload all agent manifests in development mode."""

    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_available")

    registry = get_registry()
    loader = AgentLoader()
    records = loader.discover(settings.agents_dir.resolve())
    registry.replace(records)
    request.app.state.runner = AgentRunner(registry=registry, loader=loader, logger=request.app.state.logger)

    return {
        "success": True,
        "agents_total": len(records),
    }


@router.get("/requests/recent")
def recent_requests(
    settings: Settings = Depends(get_app_settings),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, list[dict]]:
    """Read recent request logs from JSONL in development mode."""

    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_available")

    log_file = settings.request_log_file
    if not log_file.exists():
        return {"items": []}

    buffer: deque[str] = deque(maxlen=limit)
    with log_file.open("r", encoding="utf-8") as file:
        for line in file:
            buffer.append(line)

    return {"items": [json.loads(item) for item in buffer]}
