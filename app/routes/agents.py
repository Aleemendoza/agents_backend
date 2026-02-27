"""Endpoints related to agent discovery and metadata."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.registry import AgentRegistry
from app.core.security import require_api_key
from app.dependencies import get_registry
from app.schemas.agent import AgentManifest, AgentPublic

router = APIRouter(prefix="/v1/agents", tags=["agents"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[AgentPublic])
def list_agents(registry: AgentRegistry = Depends(get_registry)) -> list[AgentPublic]:
    """List all discovered agents."""

    return registry.as_public_list()


@router.get("/{agent_id}", response_model=AgentManifest)
def get_agent(agent_id: str, registry: AgentRegistry = Depends(get_registry)) -> AgentManifest:
    """Return full metadata for one agent."""

    record = registry.get(agent_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return record.manifest
