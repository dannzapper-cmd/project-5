"""Phase 6A federated learning API contracts (versioned V1 schemas).

These mirror the conventions used by ``NavSlamStateV1`` / ``DigitalTwinStateV1``:
versioned, Pydantic-validated response models consumed by the dashboard. The FL
panel reads these — it never hardcodes metrics.

Synthetic federated learning simulation. No real patient data. No medical claims.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

FederatedRunStatus = Literal["idle", "running", "completed", "failed"]

DISCLAIMER = (
    "Synthetic federated learning simulation. No real patient data. No medical claims."
)


class GlobalRoundResultV1(BaseModel):
    """Per-round centralized (global) evaluation result."""

    schema_version: Literal["v1"] = "v1"
    round: int
    global_loss: float
    global_accuracy: float


class ClientSummaryV1(BaseModel):
    """Per-client summary for one simulated edge node."""

    schema_version: Literal["v1"] = "v1"
    client_id: str
    data_size: int
    signal_type: str
    final_local_loss: float
    final_local_accuracy: float | None = None
    anomaly_ratio: float | None = None


class FederatedRunSummaryV1(BaseModel):
    """Compact summary of the latest federated run for the dashboard."""

    schema_version: Literal["v1"] = "v1"
    experiment_id: str | None = None
    timestamp_utc: str | None = None
    seed: int | None = None
    num_clients: int = 0
    num_rounds: int = 0
    local_epochs: int | None = None
    model_type: str | None = None
    model_param_count: int | None = None
    framework: str | None = None
    strategy: str | None = None
    final_global_loss: float | None = None
    final_global_accuracy: float | None = None
    completed_rounds: int = 0
    mlflow_run_id: str | None = None
    report_path: str | None = None


class FederatedStatusV1(BaseModel):
    """Status endpoint payload (valid before AND after a run)."""

    schema_version: Literal["v1"] = "v1"
    status: FederatedRunStatus = "idle"
    has_run: bool = False
    num_clients: int = 0
    num_rounds: int = 0
    completed_rounds: int = 0
    latest_global_loss: float | None = None
    latest_global_accuracy: float | None = None
    summary: FederatedRunSummaryV1 = Field(default_factory=FederatedRunSummaryV1)
    client_summaries: list[ClientSummaryV1] = Field(default_factory=list)
    convergence: list[GlobalRoundResultV1] = Field(default_factory=list)
    mlflow_run_id: str | None = None
    report_path: str | None = None
    artifact_dir: str | None = None
    synthetic_only: bool = True
    disclaimer: str = DISCLAIMER


class FederatedResultV1(BaseModel):
    """Full latest-result payload including the complete convergence curve."""

    schema_version: Literal["v1"] = "v1"
    status: FederatedRunStatus = "idle"
    has_run: bool = False
    summary: FederatedRunSummaryV1 = Field(default_factory=FederatedRunSummaryV1)
    global_results: list[GlobalRoundResultV1] = Field(default_factory=list)
    client_summaries: list[ClientSummaryV1] = Field(default_factory=list)
    client_distribution_summary: dict | None = None
    synthetic_only: bool = True
    disclaimer: str = DISCLAIMER
