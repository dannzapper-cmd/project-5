"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AXON API settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    axon_env: str = "development"
    axon_phase: int = 3
    axon_version: str = "0.4.0"
    axon_service_name: str = "axon-api"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    redis_url: str = "redis://localhost:6379/0"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic_prefix: str = "axon/v1"

    # Phase 3 — LLM / Copilot
    axon_llm_mode: str = "mock"
    axon_llm_provider: str = "mock"
    axon_llm_model: str = "mock-operator-copilot-v1"
    axon_copilot_enabled: bool = True
    axon_rag_enabled: bool = True
    axon_llm_timeout_seconds: int = 15
    axon_llm_max_tokens: int = 500

    # Phase 3 — Safety thresholds
    axon_safety_high_risk_threshold: float = 0.75
    axon_safety_low_confidence_threshold: float = 0.55
    axon_stale_telemetry_seconds: int = 5

    # Phase 3 — Agent loop
    axon_agent_loop_interval_seconds: int = 5
    axon_hitl_expiry_seconds: int = 120
    axon_failure_injection_auto_reset_seconds: int = 30

    # Phase 5 — Digital Twin timing contracts
    twin_broadcast_hz: int = 5
    sensor_stale_ttl_seconds: int = 5
    sensor_dropout_ttl_seconds: int = 15

    # Optional real LLM keys (empty by default)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    @property
    def service_name(self) -> str:
        return self.axon_service_name

    @property
    def phase(self) -> int:
        return self.axon_phase

    @property
    def version(self) -> str:
        return self.axon_version


settings = Settings()
