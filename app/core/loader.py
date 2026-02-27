"""Utilities for discovering and importing agents dynamically."""

import re
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from pydantic import ValidationError

from app.schemas.agent import AgentManifest, AgentRecord

_ID_RE = re.compile(r"^[a-z0-9-]+$")


class AgentDiscoveryError(Exception):
    """Raised when an agent cannot be loaded from disk."""


class AgentLoader:
    """Discovers agent manifests and imports their modules."""

    def discover(self, agents_dir: Path) -> list[AgentRecord]:
        """Scan agents directory and parse each manifest into healthy/broken records."""

        if not agents_dir.exists() or not agents_dir.is_dir():
            raise AgentDiscoveryError(f"Agents directory not found: {agents_dir}")

        discovered: list[AgentRecord] = []
        for child in sorted(agents_dir.iterdir()):
            if not child.is_dir():
                continue

            manifest_path = child / "manifest.json"
            if not manifest_path.exists():
                continue

            try:
                manifest = AgentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
                self._validate_manifest(manifest)
                record = AgentRecord(manifest=manifest, directory=child.resolve())
                self.load_module(record)
                discovered.append(record)
            except (ValidationError, AgentDiscoveryError, ValueError) as exc:
                fallback_id = child.name.replace("_", "-").lower()
                broken_manifest = AgentManifest(
                    id=fallback_id if _ID_RE.fullmatch(fallback_id) else "broken-agent",
                    name=child.name,
                    description="Invalid or broken agent",
                    version="0.0.0",
                    entrypoint="agent.py",
                    timeout_seconds=10,
                )
                discovered.append(
                    AgentRecord(
                        manifest=broken_manifest,
                        directory=child.resolve(),
                        status="broken",
                        last_error=str(exc),
                    )
                )

        return discovered

    def _validate_manifest(self, manifest: AgentManifest) -> None:
        """Run additional robust validations beyond basic schema checks."""

        if not _ID_RE.fullmatch(manifest.id):
            raise AgentDiscoveryError("Manifest id must be a slug [a-z0-9-]")
        if manifest.timeout_seconds < 1 or manifest.timeout_seconds > 120:
            raise AgentDiscoveryError("timeout_seconds must be between 1 and 120")
        if not manifest.entrypoint.endswith(".py"):
            raise AgentDiscoveryError("entrypoint must end with .py")
        if ".." in Path(manifest.entrypoint).parts or Path(manifest.entrypoint).is_absolute():
            raise AgentDiscoveryError("entrypoint cannot contain path traversal")

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
