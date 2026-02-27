"""In-memory registry for discovered agents."""

from collections.abc import Iterable

from app.schemas.agent import AgentPublic, AgentRecord


class AgentRegistry:
    """Holds discovered agent records and exposes read APIs."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentRecord] = {}

    def clear(self) -> None:
        """Reset registry in-place."""

        self._agents.clear()

    def register(self, record: AgentRecord) -> None:
        """Register an agent manifest and runtime location."""

        self._agents[record.manifest.id] = record

    def replace(self, records: list[AgentRecord]) -> None:
        """Replace current records atomically."""

        self._agents = {record.manifest.id: record for record in records}

    def get(self, agent_id: str) -> AgentRecord | None:
        """Return one agent by ID if it exists."""

        return self._agents.get(agent_id)

    def all(self) -> Iterable[AgentRecord]:
        """Return all registered agent records."""

        return self._agents.values()

    def as_public_list(self) -> list[AgentPublic]:
        """Serialize all agents for list endpoint."""

        return [
            AgentPublic(
                id=record.manifest.id,
                name=record.manifest.name,
                description=record.manifest.description,
                version=record.manifest.version,
                status=record.status,
                last_error=record.last_error,
            )
            for record in self._agents.values()
        ]
