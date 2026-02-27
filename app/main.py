"""EtherCode Agent Runtime FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.core.loader import AgentLoader
from app.core.logger import RequestLoggingMiddleware, setup_logging
from app.dependencies import get_registry
from app.routes import agents, execution
from app.services.runner import AgentRunner

settings = get_settings()
logger = setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize registry, loader and service dependencies at startup."""

    registry = get_registry()
    loader = AgentLoader()

    for record in loader.discover(settings.agents_dir.resolve()):
        registry.register(record)

    app.state.runner = AgentRunner(registry=registry, loader=loader, logger=logger)
    yield


app = FastAPI(
    title="EtherCode Agent Runtime (EAR)",
    version="1.0.0",
    description="Runtime backend to discover and execute local Python agents.",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware, logger=logger, request_log_file=settings.request_log_file)
app.include_router(agents.router)
app.include_router(execution.router)
