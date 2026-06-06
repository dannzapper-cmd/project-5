"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AXON API settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    axon_env: str = "development"
    axon_phase: int = 0
    axon_version: str = "0.1.0"
    axon_service_name: str = "axon-api"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    redis_url: str = "redis://localhost:6379/0"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic_prefix: str = "axon/v1"

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
