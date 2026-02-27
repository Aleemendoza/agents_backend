"""Structured JSON logging configuration and request logging utilities."""

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware


class JsonFormatter(logging.Formatter):
    """Logging formatter that emits JSON records."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "extra") and isinstance(record.extra, dict):
            payload.update(record.extra)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str) -> logging.Logger:
    """Configure root logging with JSON formatter."""

    logger = logging.getLogger("ear")
    logger.setLevel(level.upper())
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs incoming requests and response latencies."""

    def __init__(self, app: FastAPI, logger: logging.Logger, request_log_file: Path) -> None:
        super().__init__(app)
        self.logger = logger
        self.request_log_file = request_log_file

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        response = None
        error_message = None

        try:
            response = await call_next(request)
            return response
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            raise
        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)
            status_code = response.status_code if response is not None else 500
            payload = {
                "path": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "client": request.client.host if request.client else "unknown",
            }
            if error_message:
                payload["error"] = error_message

            self.logger.info("request_processed", extra={"extra": payload})
            self._persist_request_log(payload)

    def _persist_request_log(self, payload: dict[str, Any]) -> None:
        """Persist request logs as JSON lines for local observability."""

        self.request_log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.request_log_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")
