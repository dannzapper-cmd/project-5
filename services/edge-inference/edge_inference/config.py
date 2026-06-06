"""Edge inference service configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    model_dir: str = "/app/models/onnx"
    metadata_dir: str = "/app/models/metadata"
    model_score_stream: str = "axon:v1:stream:model_scores"
    inference_interval_ms: int = 500
    axon_phase: str = "Phase 2 - Edge AI Core"

    emg_stream: str = "axon:v1:stream:sensors:emg"
    imu_stream: str = "axon:v1:stream:sensors:imu"

    source: str = "edge-inference"


settings = Settings()
