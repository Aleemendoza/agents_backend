"""Endpoints for agent execution."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.core.security import require_api_key
from app.dependencies import get_runner
from app.schemas.execution import AgentExecutionError, AgentExecutionRequest, AgentExecutionSuccess
from app.services.runner import AgentRunner

router = APIRouter(prefix="/v1/run", tags=["execution"], dependencies=[Depends(require_api_key)])


@router.post("/{agent_id}", response_model=AgentExecutionSuccess | AgentExecutionError)
async def run_agent(
    agent_id: str,
    body: AgentExecutionRequest,
    runner: AgentRunner = Depends(get_runner),
) -> AgentExecutionSuccess | JSONResponse:
    """Execute an agent by ID with request input/context."""

    result = await runner.execute(agent_id=agent_id, request=body)
    if isinstance(result, AgentExecutionError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=result.model_dump())
    return result
