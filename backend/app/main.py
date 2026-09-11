from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.cases import (
    router as cases_router,
)
from app.api.evaluations import (
    router as evaluations_router,
)
from app.api.system import (
    router as system_router,
)
from app.config import get_settings
from app.observability.telemetry import (
    configure_telemetry,
    instrument_fastapi,
)
from app.state import init_db

settings = get_settings()

configure_telemetry(
    settings
)


@asynccontextmanager
async def lifespan(
    _: FastAPI,
) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "Multi-agent enterprise case "
        "resolution platform."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

instrument_fastapi(
    app
)

app.include_router(
    cases_router
)
app.include_router(
    evaluations_router
)
app.include_router(
    system_router
)

# Last add_middleware call becomes the outermost
# layer. CORS must wrap OTEL so OPTIONS preflight
# never hits the FastAPI instrumentor bug with
# mounted APIRouters (_IncludedRouter has no path).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
    )
