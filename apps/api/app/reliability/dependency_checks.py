"""TCP and disk checks for Phase 7 reliability (max 1s TCP timeout, no retries)."""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from apps.api.app.core.config import settings

ALLOWED_STATUSES = frozenset({"ok", "degraded", "unavailable", "inactive", "error"})


@dataclass(frozen=True)
class ComponentCheck:
    status: str
    required: bool
    message: str
    error_type: str | None = None

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_STATUSES:
            raise ValueError(f"invalid status vocabulary: {self.status}")


def tcp_reachable(host: str, port: int, timeout: float = 1.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"TCP reachable at {host}:{port}"
    except OSError as exc:
        return False, f"TCP check failed: {exc}"


def parse_redis_target(redis_url: str) -> tuple[str, int]:
    parsed = urlparse(redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    return host, port


def check_redis() -> ComponentCheck:
    host, port = parse_redis_target(settings.redis_url)
    ok, msg = tcp_reachable(host, port)
    if ok:
        return ComponentCheck(status="ok", required=True, message=msg)
    return ComponentCheck(
        status="error",
        required=True,
        message=msg,
        error_type="redis_unreachable",
    )


def check_mqtt() -> ComponentCheck:
    ok, msg = tcp_reachable(settings.mqtt_host, settings.mqtt_port)
    if ok:
        return ComponentCheck(status="ok", required=True, message=msg)
    return ComponentCheck(
        status="error",
        required=True,
        message=msg,
        error_type="mqtt_unreachable",
    )


def artifact_exists(path: Path, label: str) -> ComponentCheck:
    if path.is_file():
        return ComponentCheck(
            status="ok",
            required=False,
            message=f"{label} artifact present at {path.name}",
        )
    return ComponentCheck(
        status="unavailable",
        required=False,
        message=f"{label} artifact missing at {path}",
    )


def check_mlflow() -> ComponentCheck:
    host = os.getenv("MLFLOW_HOST", "").strip()
    if not host:
        return ComponentCheck(
            status="inactive",
            required=False,
            message="MLflow learning profile not configured (set MLFLOW_HOST to probe)",
        )
    port = int(os.getenv("MLFLOW_PORT", "5000"))
    ok, msg = tcp_reachable(host, port)
    if ok:
        return ComponentCheck(status="ok", required=False, message=msg)
    return ComponentCheck(
        status="unavailable",
        required=False,
        message=f"MLflow server not reachable at {host}:{port} (learning profile optional)",
        error_type="mlflow_unreachable",
    )
