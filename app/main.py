"""EtherCode Agent Runtime FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.loader import AgentLoader
from app.core.logger import setup_logging
from app.core.middleware import BodySizeLimitMiddleware, InMemoryRateLimitMiddleware, RequestContextMiddleware
from app.dependencies import get_registry
from app.routes import agents, dev, execution, system
from app.services.runner import AgentRunner

settings = get_settings()
logger = setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize registry, loader and service dependencies at startup."""

    registry = get_registry()
    loader = AgentLoader()
    records = loader.discover(settings.agents_dir.resolve())
    registry.replace(records)
    for record in records:
        if record.status == "broken":
            logger.warning("agent_discovery_broken", extra={"extra": {"agent_id": record.manifest.id, "error": record.last_error}})

    app.state.runner = AgentRunner(registry=registry, loader=loader, logger=logger)
    app.state.started_at = datetime.now(UTC)
    app.state.logger = logger
    yield


app = FastAPI(
    title="EtherCode Agent Runtime (EAR)",
    version=settings.service_version,
    description="Runtime backend to discover and execute local Python agents.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Request-Id"],
)
app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=settings.max_body_bytes)
app.add_middleware(
    InMemoryRateLimitMiddleware,
    enabled=settings.effective_rate_limit_enabled,
    max_requests=settings.rate_limit_per_min,
)
app.add_middleware(RequestContextMiddleware, logger=logger, request_log_file=settings.request_log_file)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": str(exc.detail),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "validation_error",
            "details": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


app.include_router(system.router)
app.include_router(agents.router)
app.include_router(execution.router)
app.include_router(dev.router)
