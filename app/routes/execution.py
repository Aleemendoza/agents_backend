"""Endpoints for agent execution."""

import json

from fastapi import APIRouter, Depends, Request, status
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
    request: Request,
    runner: AgentRunner = Depends(get_runner),
) -> AgentExecutionSuccess | JSONResponse:
    """Execute an agent by ID with request input/context."""

    result = await runner.execute(agent_id=agent_id, request=body)
    if isinstance(result, AgentExecutionError):
        request.state.execution_meta = {
            "agent_id": agent_id,
            "success": False,
            "output_size_bytes": 0,
        }
        code = status.HTTP_404_NOT_FOUND if result.error == "agent_not_found" else status.HTTP_400_BAD_REQUEST
        return JSONResponse(status_code=code, content=result.model_dump())

    request.state.execution_meta = {
        "agent_id": agent_id,
        "success": True,
        "output_size_bytes": len(json.dumps(result.output, ensure_ascii=False).encode("utf-8")),
    }
    return result
