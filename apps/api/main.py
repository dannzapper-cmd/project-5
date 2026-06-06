"""AXON API gateway entrypoint (Phase 0: health endpoint only)."""

from fastapi import FastAPI

from apps.api.app.core.config import settings
from apps.api.app.routes.health import router as health_router

app = FastAPI(
    title="AXON API",
    description="Bio-Robotics Edge Command System — async gateway",
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(health_router)
