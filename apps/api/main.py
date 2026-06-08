"""AXON API gateway entrypoint (Phase 8: integrated mission control layer)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.core.config import settings
from apps.api.app.core.lifespan import lifespan
from apps.api.app.reliability.middleware import TraceAndMetricsMiddleware
from apps.api.app.routes.agents import router as agents_router
from apps.api.app.routes.health import router as health_router
from apps.api.app.routes.learning import router as learning_router
from apps.api.app.routes.metrics import router as metrics_router
from apps.api.app.routes.mission import router as mission_router
from apps.api.app.routes.mlops import router as mlops_router
from apps.api.app.routes.nav_slam import router as nav_slam_router
from apps.api.app.routes.rl import router as rl_router
from apps.api.app.routes.telemetry import router as telemetry_router
from apps.api.app.routes.twin import router as twin_router
from apps.api.app.routes.ws import router as ws_router

app = FastAPI(
    title="AXON API",
    description="Bio-Robotics Edge Command System — async gateway",
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(TraceAndMetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(mission_router)
app.include_router(telemetry_router)
app.include_router(agents_router)
app.include_router(mlops_router)
app.include_router(learning_router)
app.include_router(rl_router)
app.include_router(twin_router)
app.include_router(nav_slam_router)
app.include_router(ws_router)
