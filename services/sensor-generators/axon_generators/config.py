"""Generator configuration from environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class GeneratorConfig(BaseSettings):
    """Synthetic sensor generator settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    axon_scenario: str = "normal_session"
    axon_node_id: str = "rehab-node-01"
    axon_robot_id: str = "rehab-robot-01"
    axon_publish_interval: float = 1.0
    axon_seed: int | None = None
    axon_trace_id: str = "session-synthetic-001"
    axon_source: str = "sensor-generator"

    @property
    def scenario(self) -> str:
        return self.axon_scenario
