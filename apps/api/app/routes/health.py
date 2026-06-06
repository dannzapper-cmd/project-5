"""Health check route."""

from fastapi import APIRouter

from apps.api.app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str | int]:
    """Return service health and Phase 0 metadata."""
    return {
        "status": "ok",
        "service": settings.service_name,
        "phase": settings.phase,
        "version": settings.version,
    }
