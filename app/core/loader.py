"""Utilities for discovering and importing agents dynamically."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from app.schemas.agent import AgentManifest, AgentRecord


class AgentDiscoveryError(Exception):
    """Raised when an agent cannot be loaded from disk."""


class AgentLoader:
    """Discovers agent manifests and imports their modules."""

    def discover(self, agents_dir: Path) -> list[AgentRecord]:
        """Scan agents directory and parse each valid manifest."""

        if not agents_dir.exists() or not agents_dir.is_dir():
            raise AgentDiscoveryError(f"Agents directory not found: {agents_dir}")

        discovered: list[AgentRecord] = []
        for child in sorted(agents_dir.iterdir()):
            if not child.is_dir():
                continue

            manifest_path = child / "manifest.json"
            if not manifest_path.exists():
                continue

            manifest = AgentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
            discovered.append(AgentRecord(manifest=manifest, directory=child.resolve()))

        return discovered

    def load_module(self, record: AgentRecord) -> ModuleType:
        """Import an agent's entrypoint module from its file path."""

        module_path = record.module_path
        if not module_path.exists():
            raise AgentDiscoveryError(f"Entrypoint not found for agent '{record.manifest.id}'")

        module_name = f"agent_runtime_{record.manifest.id.replace('-', '_')}"
        spec = spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise AgentDiscoveryError(f"Cannot load module spec for agent '{record.manifest.id}'")

        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "run"):
            raise AgentDiscoveryError(f"Agent '{record.manifest.id}' has no run(input_data, context) function")

        return module
