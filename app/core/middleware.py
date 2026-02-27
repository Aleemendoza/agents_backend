"""HTTP middleware for request IDs, limits, and structured request logs."""

import json
import logging
import time
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized request bodies."""

    def __init__(self, app, max_body_bytes: int) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self.max_body_bytes:
            return JSONResponse(status_code=413, content={"success": False, "error": "payload_too_large"})
        return await call_next(request)


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple IP-based fixed-window limiter."""

    def __init__(self, app, enabled: bool, max_requests: int, window_seconds: int = 60) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.enabled = enabled
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if not self.enabled:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self._store[ip]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            return JSONResponse(status_code=429, content={"success": False, "error": "rate_limited"})

        bucket.append(now)
        return await call_next(request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request_id, write structured request logs, and persist JSONL audit lines."""

    def __init__(self, app, logger: logging.Logger, request_log_file: Path) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.logger = logger
        self.request_log_file = request_log_file

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        status_code = 500
        error_message: str | None = None
        response = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            raise
        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)
            input_size = int(request.headers.get("content-length", "0")) if request.headers.get("content-length", "0").isdigit() else 0
            execution_meta = getattr(request.state, "execution_meta", {})
            payload = {
                "timestamp": datetime.now(UTC).isoformat(),
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "agent_id": execution_meta.get("agent_id"),
                "success": execution_meta.get("success", status_code < 400),
                "input_size_bytes": input_size,
                "output_size_bytes": execution_meta.get("output_size_bytes", 0),
            }
            if error_message:
                payload["error"] = error_message

            self.logger.info("request_processed", extra={"extra": payload})
            self._persist(payload)

            if response is not None:
                response.headers["X-Request-Id"] = request_id

    def _persist(self, payload: dict) -> None:
        self.request_log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.request_log_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")
