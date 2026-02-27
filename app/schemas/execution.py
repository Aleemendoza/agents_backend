"""Schemas for execution API contracts."""

from typing import Any

from pydantic import BaseModel, Field


class AgentExecutionRequest(BaseModel):
    """Incoming payload for agent execution."""

    input: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentExecutionSuccess(BaseModel):
    """Successful execution response payload."""

    success: bool = True
    agent_id: str
    latency_ms: int
    output: dict[str, Any]


class AgentExecutionError(BaseModel):
    """Failed execution response payload."""

    success: bool = False
    error: str
    latency_ms: int
    agent_id: str | None = None
