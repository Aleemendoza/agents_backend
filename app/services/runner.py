"""Service layer for executing agents with timeout and error handling."""

import asyncio
import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.core.loader import AgentLoader
from app.core.registry import AgentRegistry
from app.schemas.execution import AgentExecutionError, AgentExecutionRequest, AgentExecutionSuccess


class AgentRunner:
    """Orchestrates loading and running agents from the registry."""

    def __init__(self, registry: AgentRegistry, loader: AgentLoader, logger: logging.Logger) -> None:
        self.registry = registry
        self.loader = loader
        self.logger = logger
        self._executor = ThreadPoolExecutor(max_workers=8)

    async def execute(self, agent_id: str, request: AgentExecutionRequest) -> AgentExecutionSuccess | AgentExecutionError:
        """Execute an agent and return standardized success or error response."""

        start = time.perf_counter()
        record = self.registry.get(agent_id)
        if record is None:
            return AgentExecutionError(error="agent_not_found", latency_ms=self._latency(start), agent_id=agent_id)
        if record.status == "broken":
            return AgentExecutionError(
                error=f"agent_broken: {record.last_error or 'invalid agent'}",
                latency_ms=self._latency(start),
                agent_id=agent_id,
            )

        try:
            module = self.loader.load_module(record)
            run_callable: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = getattr(module, "run")

            output = await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(
                    self._executor,
                    run_callable,
                    request.input,
                    request.context,
                ),
                timeout=record.manifest.timeout_seconds,
            )
            if not isinstance(output, dict):
                raise TypeError("Agent run() must return dict")

            latency_ms = self._latency(start)
            self.logger.info("agent_executed", extra={"extra": {"agent_id": agent_id, "latency_ms": latency_ms}})
            return AgentExecutionSuccess(agent_id=agent_id, latency_ms=latency_ms, output=output)

        except asyncio.TimeoutError:
            latency_ms = self._latency(start)
            self.logger.warning("agent_timeout", extra={"extra": {"agent_id": agent_id, "latency_ms": latency_ms}})
            return AgentExecutionError(error="agent_execution_timed_out", latency_ms=latency_ms, agent_id=agent_id)
        except Exception as exc:  # noqa: BLE001
            latency_ms = self._latency(start)
            self.logger.exception("agent_execution_failed", extra={"extra": {"agent_id": agent_id, "latency_ms": latency_ms}})
            return AgentExecutionError(error=str(exc), latency_ms=latency_ms, agent_id=agent_id)

    @staticmethod
    def _latency(start: float) -> int:
        return int((time.perf_counter() - start) * 1000)
