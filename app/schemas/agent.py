"""Schemas related to agent metadata."""

from pathlib import Path

from pydantic import BaseModel, Field


class AgentManifest(BaseModel):
    """Manifest definition discovered from each agent directory."""

    id: str
    name: str
    description: str
    version: str
    entrypoint: str = Field(default="agent.py")
    timeout_seconds: int = Field(default=10, ge=1, le=300)


class AgentPublic(BaseModel):
    """Public agent metadata returned by listing endpoint."""

    id: str
    name: str
    description: str
    version: str


class AgentRecord(BaseModel):
    """Internal record with runtime paths used by loader and runner."""

    manifest: AgentManifest
    directory: Path

    @property
    def module_path(self) -> Path:
        """Return absolute path of the Python entrypoint for this agent."""

        return self.directory / self.manifest.entrypoint
